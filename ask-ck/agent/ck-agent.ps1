<#
.SYNOPSIS
  ck-agent for Windows — Ask CK per-user local LLM agent (PowerShell 5.1+).

.DESCRIPTION
  Runs on the USER's OWN Windows machine so their Ask CK LLM requests execute against THEIR
  OWN locally-logged-in Claude Code CLI seat, never a shared one. The shared Ask CK server
  never runs `claude`; the user's browser tab brokers prompts from the server to this agent
  and posts completions back. This is the Windows implementation of the SAME contract as
  ck_agent.py (Ubuntu): same endpoints, same payloads, same `claude -p` flags, same
  stream-json parsing, same failure reporting. Design: ask-ck/CK-main/PLAN-per-user-agent.md
  and ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md (§4).

  No dependencies beyond Windows PowerShell 5.1 (present on every Windows 10/11 machine).

    powershell -ExecutionPolicy Bypass -File ck-agent.ps1
    $env:CK_AGENT_ORIGIN = 'http://10.33.22.17:8000'; .\ck-agent.ps1   # lock CORS to your server

  Security model (per signed-off plan): binds 127.0.0.1 ONLY (never 0.0.0.0), CORS is
  restricted to the Ask CK server origin, no token. Any process on THIS machine could call
  it, but it can only ever spend THIS user's own Claude seat.

  Self-test modes (used by the repo's gate through pwsh, so the two agents cannot drift):
    -ParseStream <file>                  print {content, cli_error_text, is_error, result} for a stream capture
    -FailureDetail <file> -Stderr <s> -ExitCode <n>   print the failure reason the agent would report
    -Health                              print the /health payload and exit
#>
[CmdletBinding()]
param(
  [string]$ParseStream,
  [string]$FailureDetail,
  [string]$Stderr = "",
  [int]$ExitCode = 1,
  [switch]$Health
)

Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------------------
# Everything the request workers need is in $Lib so it can be dot-sourced into worker
# runspaces (a /run can take ten minutes; /health and /cancel must keep answering).
# ---------------------------------------------------------------------------------------
$Lib = {
  # Bump when the contract changes; the setup script compares this against the served
  # manifest to decide whether a running agent is stale and must be replaced.
  $script:AGENT_VERSION = '1.2.0'
  # Thinking shares one message's output budget with the answer; cap it on LONG calls only
  # (passing the flag turns extended thinking on, and the 30s health ping must stay fast).
  # Mirrors ck_agent.py; "long" is decided by the job's timeout, which the server floors.
  $script:CLI_MAX_THINKING_TOKENS = 2048
  $script:LONG_CALL_SECONDS = 120

  # MIRRORS THE SERVER'S TRANSPORT (and ck_agent.py), measured 2026-09-04:
  #   --tools ""                 one completion, never an agent session
  #   --system-prompt <steer>    REPLACE the CLI's harness prompt
  #   --no-session-persistence   a completion is not a session
  #   cwd = a neutral directory  nothing to auto-discover (no CLAUDE.md, no memory)
  #   stream-json                concatenate every assistant text block; `result` alone
  #                              drops the head of a long answer
  $script:DEFAULT_SYSTEM_PROMPT = 'You are a precise generator. Follow the user''s instructions exactly and return only what they ask for.'
  $script:DEFAULT_TIMEOUT = [int]($(if ($env:CK_AGENT_TIMEOUT) { $env:CK_AGENT_TIMEOUT } else { 600 }))
  $script:STATUS_TTL_SEC = 60

  function Write-AgentLog([string]$msg, $state) {
    # One timestamped line appended to agent.log beside the script ($state.logPath, set by the
    # listener at startup; unset in the self-test modes, where this is a no-op). The agent runs
    # HIDDEN, so this file is the only record of what happened on the seat — the Ubuntu agent
    # has had agent.log since the served setup shipped; the Windows one had nothing until
    # 2026-09-11. Worker runspaces share the file: a named mutex serialises the appends.
    try {
      if ($null -eq $state -or -not $state.ContainsKey('logPath') -or -not $state['logPath']) { return }
      $line = ('{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg) + [Environment]::NewLine
      $m = New-Object System.Threading.Mutex($false, 'Local\ck-agent-log')
      try {
        [void]$m.WaitOne(2000)
        [IO.File]::AppendAllText($state['logPath'], $line, (New-Object System.Text.UTF8Encoding($false)))
      } finally { try { $m.ReleaseMutex() } catch { }; $m.Dispose() }
    } catch { }
  }

  function Get-NeutralCwd {
    $p = Join-Path ([IO.Path]::GetTempPath()) 'askck-cli-cwd'
    if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    return $p
  }

  function Find-Claude {
    # CK_AGENT_CLAUDE pins a binary (tests); then PATH; then the native installer's location,
    # which it does NOT add to PATH (demo-day issue #1). Prefer the .exe over a .cmd shim.
    if ($env:CK_AGENT_CLAUDE -and (Test-Path -LiteralPath $env:CK_AGENT_CLAUDE)) { return $env:CK_AGENT_CLAUDE }
    if ($env:USERPROFILE) {
      $local = Join-Path $env:USERPROFILE '.local\bin\claude.exe'
      if (Test-Path -LiteralPath $local) { return $local }
    }
    $cmd = Get-Command claude -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { return $cmd.Source }
    return $null
  }

  function Get-TextBlocks($message) {
    $out = @()
    if ($null -eq $message) { return $out }
    $content = $null
    try { $content = $message.content } catch { }
    if ($null -eq $content) { return $out }
    foreach ($b in @($content)) {
      if ($null -eq $b) { continue }
      $t = $null; $tx = $null
      try { $t = $b.type; $tx = $b.text } catch { }
      if ($t -eq 'text' -and $tx) { $out += [string]$tx }
    }
    return $out
  }

  function Parse-Stream([string]$raw) {
    # (content, envelope) — every `assistant` text block with a real (msg_*) id, in order.
    # Synthesized CLI error messages (non-msg_ id) are kept OUT of the content but ON the
    # envelope as cli_error_text: on a failed run that is the message the user needs.
    $texts = New-Object System.Collections.Generic.List[string]
    $synth = New-Object System.Collections.Generic.List[string]
    $envelope = $null
    foreach ($line in ($raw -split "`r?`n")) {
      $line = $line.Trim()
      if (-not $line) { continue }
      $evt = $null
      try { $evt = $line | ConvertFrom-Json } catch { continue }
      if ($null -eq $evt) { continue }
      $kind = $null
      try { $kind = $evt.type } catch { }
      if ($kind -eq 'assistant') {
        $message = $null
        try { $message = $evt.message } catch { }
        # @(...) because PowerShell unrolls a returned array: one chunk would arrive as a
        # string and none as $null, and `.Count` on $null fails under strict mode.
        $chunks = @(Get-TextBlocks $message)
        if ($chunks.Count -eq 0) { continue }
        $id = ''
        try { if ($message.id) { $id = [string]$message.id } } catch { }
        if ($id -and -not $id.StartsWith('msg_')) { foreach ($c in $chunks) { $synth.Add($c) }; continue }
        foreach ($c in $chunks) { $texts.Add($c) }
      } elseif ($kind -eq 'result') {
        $envelope = $evt
      } elseif ($null -eq $kind) {
        $hasResult = $false
        try { $hasResult = ($null -ne $evt.result) } catch { }
        if ($hasResult) { $envelope = $evt }
      }
    }
    $env2 = @{}
    if ($null -ne $envelope) {
      foreach ($p in $envelope.PSObject.Properties) { $env2[$p.Name] = $p.Value }
    }
    if ($synth.Count -gt 0) {
      $joined = ($synth -join '')
      $env2['cli_error_text'] = $joined.Substring(0, [Math]::Min(2000, $joined.Length))
    }
    if ($texts.Count -gt 0) { $content = ($texts -join '') }
    elseif ($env2.ContainsKey('result') -and $null -ne $env2['result']) { $content = [string]$env2['result'] }
    else { $content = $raw }
    return @{ content = $content; envelope = $env2 }
  }

  function Get-FailureDetail([string]$out, [string]$err, [int]$code) {
    # The reason a non-zero `claude -p` exit failed: result event text, then the synthesized
    # message, then stderr, then the exit code. NEVER a slice of raw stdout — that is the
    # `init` event, and reporting it hid the reason for eight demo-day failures (2026-09-10).
    $parsed = Parse-Stream $out
    $env2 = $parsed.envelope
    $candidates = @()
    if ($env2.ContainsKey('result')) { $candidates += [string]$env2['result'] }
    if ($env2.ContainsKey('cli_error_text')) { $candidates += [string]$env2['cli_error_text'] }
    $candidates += [string]$err
    foreach ($c in $candidates) {
      $t = ([string]$c).Trim()
      if ($t -and -not $t.StartsWith('{')) { return $t.Substring(0, [Math]::Min(500, $t.Length)) }
    }
    return "exit code $code"
  }

  function ConvertTo-ArgString([string[]]$argList) {
    # Windows has ONE command line, not argv. Quote per the MS C runtime rules so an
    # argument with spaces, quotes or newlines (the system prompt) arrives intact, and an
    # EMPTY argument (`--tools ""`) is preserved. (Named $argList, never $args: that is
    # PowerShell's automatic unbound-arguments variable, and a parameter of that name is
    # silently empty — the first smoke test ran `claude` with no arguments at all.)
    $parts = foreach ($a in $argList) {
      if ($a -eq '') { '""'; continue }
      if ($a -notmatch '[\s"]') { $a; continue }
      $sb = New-Object System.Text.StringBuilder
      [void]$sb.Append('"')
      $bs = 0
      foreach ($ch in $a.ToCharArray()) {
        if ($ch -eq '\') { $bs++; continue }
        if ($ch -eq '"') { [void]$sb.Append('\' * ($bs * 2 + 1)); [void]$sb.Append('"'); $bs = 0; continue }
        if ($bs) { [void]$sb.Append('\' * $bs); $bs = 0 }
        [void]$sb.Append($ch)
      }
      if ($bs) { [void]$sb.Append('\' * ($bs * 2)) }
      [void]$sb.Append('"')
      $sb.ToString()
    }
    return ($parts -join ' ')
  }

  function Start-Cli([string]$cli, [string[]]$argList, [string]$stdin, [int]$timeoutSec, [string]$jobId, $running) {
    # Redirected stdio with async stdout/stderr readers (a synchronous ReadToEnd on both
    # deadlocks once a pipe fills). Stdin is written as UTF-8 bytes on the base stream so
    # the prompt is not re-encoded by the console code page.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cli
    $psi.Arguments = ConvertTo-ArgString $argList
    $psi.WorkingDirectory = Get-NeutralCwd
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    [void]$proc.Start()
    if ($jobId -and $null -ne $running) { $running[$jobId] = $proc }
    $outTask = $proc.StandardOutput.ReadToEndAsync()
    $errTask = $proc.StandardError.ReadToEndAsync()
    try {
      if ($null -ne $stdin) {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($stdin)
        $proc.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
        $proc.StandardInput.BaseStream.Flush()
      }
    } catch { }
    try { $proc.StandardInput.Close() } catch { }
    $finished = $proc.WaitForExit([int]($timeoutSec * 1000))
    if (-not $finished) {
      Stop-ProcessTree $proc.Id
      try { $proc.WaitForExit(5000) | Out-Null } catch { }
      if ($jobId -and $null -ne $running) { $running.Remove($jobId) }
      return @{ timeout = $true; code = -1; out = ''; err = '' }
    }
    $proc.WaitForExit()   # flush the async readers
    if ($jobId -and $null -ne $running) { $running.Remove($jobId) }
    return @{ timeout = $false; code = $proc.ExitCode; out = $outTask.Result; err = $errTask.Result }
  }

  function Stop-ProcessTree([int]$processId) {
    # The Windows equivalent of killing the POSIX process group: `claude` spawns children,
    # and killing only the parent leaves them holding the seat.
    $tk = Get-Command taskkill.exe -ErrorAction SilentlyContinue
    if ($tk) { try { & $tk.Source /T /F /PID $processId 2>$null | Out-Null; return } catch { } }
    # No taskkill (pwsh on Linux/macOS, used by the repo's gate): parent only.
    try { Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue } catch { }
  }

  function Invoke-Quick([string]$cli, [string[]]$argList, [int]$timeoutSec = 20) {
    try { return Start-Cli $cli $argList $null $timeoutSec '' $null } catch { return @{ timeout = $false; code = 999; out = ''; err = "$_" } }
  }

  function Get-CliVersion([string]$cli) {
    $r = Invoke-Quick $cli @('--version') 20
    $text = ("$($r.out)$($r.err)").Trim()
    if ($text -match '\d+\.\d+\.\d+') { return $Matches[0] }
    if ($text.Length -gt 40) { return $text.Substring(0, 40) } else { return $text }
  }

  function Get-AuthStatus([string]$cli) {
    # `claude auth status`: JSON, exit 0 when logged in, 1 when not.
    $r = Invoke-Quick $cli @('auth', 'status') 20
    $data = $null
    try { $data = ($r.out.Trim() | ConvertFrom-Json) } catch { $data = $null }
    $loggedIn = ($r.code -eq 0)
    $org = $null; $email = $null
    if ($null -ne $data) {
      try { if ($null -ne $data.loggedIn) { $loggedIn = [bool]$data.loggedIn } } catch { }
      try { $org = $data.orgName } catch { }
      try { $email = $data.email } catch { }
    }
    return @{ logged_in = $loggedIn; org = $org; email = $email; error = $null }
  }

  function Get-CliStatus([string]$cli, $cache) {
    $now = [DateTime]::UtcNow
    if ($cache.ContainsKey('value') -and $cache['cli'] -eq $cli -and ($now - $cache['at']).TotalSeconds -lt $script:STATUS_TTL_SEC) { return $cache['value'] }
    $v = @{ cli_version = (Get-CliVersion $cli) }
    $auth = Get-AuthStatus $cli
    foreach ($k in $auth.Keys) { $v[$k] = $auth[$k] }
    $cache['value'] = $v; $cache['cli'] = $cli; $cache['at'] = $now
    return $v
  }

  function Invoke-ClaudeUpdate([string]$cli, $state) {
    # `claude update` — unless a job is in flight: on Windows the executable in use cannot be
    # replaced, so say so and let the caller retry. Invalidates the status cache.
    if (-not $cli) { return @{ ok = $false; updated = $false; error = 'claude CLI not found' } }
    $busy = @($state.running.Keys | Where-Object { -not $_.StartsWith('__') }).Count
    if ($busy -gt 0) { return @{ ok = $true; updated = $false; skipped = $true; reason = "job in flight ($busy); retry when the run finishes" } }
    $before = Get-CliVersion $cli
    $r = Invoke-Quick $cli @('update') 240
    $state.status.Remove('value')
    $after = Get-CliVersion $cli
    $output = ("$($r.out)`n$($r.err)").Trim()
    if ($output.Length -gt 600) { $output = $output.Substring($output.Length - 600) }
    $res = @{ ok = ($r.code -eq 0); updated = ([bool]$before -and [bool]$after -and $before -ne $after); from = $before; to = $after; output = $output }
    if ($r.code -ne 0) { $res['error'] = "claude update exited $($r.code): $output" }
    $state.lastUpdate.Clear()
    foreach ($k in $res.Keys) { $state.lastUpdate[$k] = $res[$k] }
    Write-AgentLog "claude update: $(if ($res.ContainsKey('error')) { 'FAILED - ' + $res['error'] } elseif ($res['updated']) { "$before -> $after" } else { "up to date ($after)" })" $state
    return $res
  }

  function Get-HealthPayload($state) {
    $cli = Find-Claude
    $busy = 0
    try { $busy = @($state.running.Keys | Where-Object { -not $_.StartsWith('__') }).Count } catch { }
    $p = [ordered]@{
      ok = $true; agent = 'ck-agent'; agent_version = $script:AGENT_VERSION
      claude_cli = [bool]$cli; claude_path = $cli; cli_version = $null; logged_in = $null; org = $null
      jobs_in_flight = $busy; update_error = $(if ($state.lastUpdate.ContainsKey('error')) { $state.lastUpdate['error'] } else { $null }); hint = $null
    }
    if (-not $cli) { $p['hint'] = "Install Claude Code and run 'claude auth login'."; return $p }
    $s = Get-CliStatus $cli $state.status
    $p['cli_version'] = $(if ($s.cli_version) { $s.cli_version } else { $null })
    $p['logged_in'] = $s.logged_in
    $p['org'] = $s.org
    if ($s.error) { $p['hint'] = $s.error }
    elseif (-not $s.logged_in) { $p['hint'] = "Claude CLI is installed but not logged in: run 'claude auth login'." }
    return $p
  }

  function Invoke-Claude([string]$prompt, [string]$model, [int]$timeoutSec, [string]$jobId, [string]$system, $state) {
    $cli = Find-Claude
    $sw = [Diagnostics.Stopwatch]::StartNew()
    Write-AgentLog "job $jobId start: model=$model timeout=${timeoutSec}s prompt=$($prompt.Length) chars system=$($system.Length) chars cli=$(if ($cli) { $cli } else { 'NOT FOUND' })" $state
    if (-not $cli) { return @{ content = "ERROR: Claude Code CLI not found on this machine. Install it and run 'claude auth login' with your Claude account before using the agent."; error = $true } }
    $argList = @('-p', '--output-format', 'stream-json', '--verbose', '--tools', '', '--no-session-persistence', '--system-prompt', $(if ($system) { $system } else { $script:DEFAULT_SYSTEM_PROMPT }))
    if ($model -and $model -ne 'default') { $argList += @('--model', $model) }
    if ($timeoutSec -ge $script:LONG_CALL_SECONDS) { $argList += @('--max-thinking-tokens', "$($script:CLI_MAX_THINKING_TOKENS)") }
    try {
      $r = Start-Cli $cli $argList $prompt $timeoutSec $jobId $state.running
      $secs = [int]$sw.Elapsed.TotalSeconds
      if ($r.timeout) {
        Write-AgentLog "job $jobId TIMEOUT after ${timeoutSec}s" $state
        return @{ content = "ERROR: claude CLI timed out after ${timeoutSec}s"; error = $true }
      }
      if ($state.running.ContainsKey("__killed__$jobId")) {
        $state.running.Remove("__killed__$jobId")
        Write-AgentLog "job $jobId CANCELLED after ${secs}s" $state
        return @{ content = 'ERROR: claude CLI was cancelled on this machine; nothing was kept.'; error = $true; cancelled = $true }
      }
      if ($r.code -ne 0) {
        $detail = Get-FailureDetail $r.out $r.err $r.code
        Write-AgentLog "job $jobId FAILED after ${secs}s: exit $($r.code): $detail" $state
        return @{ content = "ERROR: claude CLI failed: $detail"; error = $true }
      }
      $parsed = Parse-Stream ($r.out.Trim())
      $env2 = $parsed.envelope
      if ($env2.ContainsKey('is_error') -and $env2['is_error']) {
        $msg = $(if ($env2['result']) { [string]$env2['result'] } else { [string]$parsed.content })
        Write-AgentLog "job $jobId CLI ERROR after ${secs}s: $($msg.Substring(0, [Math]::Min(300, $msg.Length)))" $state
        return @{ content = "ERROR: $($msg.Substring(0, [Math]::Min(500, $msg.Length)))"; error = $true }
      }
      $res = @{ content = $parsed.content; error = $false }
      if ($env2.ContainsKey('usage') -and $null -ne $env2['usage']) { $res['usage'] = $env2['usage'] }
      if ($env2.ContainsKey('total_cost_usd') -and $null -ne $env2['total_cost_usd']) { $res['total_cost_usd'] = $env2['total_cost_usd'] }
      Write-AgentLog "job $jobId ok after ${secs}s: $($parsed.content.Length) chars$(if ($res.ContainsKey('total_cost_usd')) { ', $' + $res['total_cost_usd'] })" $state
      return $res
    } catch {
      Write-AgentLog "job $jobId ERROR after $([int]$sw.Elapsed.TotalSeconds)s: $_" $state
      return @{ content = "ERROR: $_"; error = $true }
    }
  }

  function Stop-AgentJob([string]$jobId, $state) {
    if (-not $jobId -or -not $state.running.ContainsKey($jobId)) { return $false }
    $proc = $state.running[$jobId]
    $state.running["__killed__$jobId"] = $true
    try { Stop-ProcessTree $proc.Id } catch { return $false }
    return $true
  }
}
. $Lib
$LibText = $Lib.ToString()

# ---------------------------------------------------------------------------------------
# Self-test modes (the gate runs these through pwsh against tests/fixtures/cli_stream_*.jsonl)
# ---------------------------------------------------------------------------------------
if ($ParseStream) {
  $raw = [IO.File]::ReadAllText($ParseStream)
  $p = Parse-Stream $raw
  $e = $p.envelope
  $out = [ordered]@{
    content = $p.content
    cli_error_text = $(if ($e.ContainsKey('cli_error_text')) { $e['cli_error_text'] } else { $null })
    is_error = $(if ($e.ContainsKey('is_error')) { [bool]$e['is_error'] } else { $false })
    result = $(if ($e.ContainsKey('result')) { $e['result'] } else { $null })
  }
  $out | ConvertTo-Json -Compress -Depth 5
  exit 0
}
if ($FailureDetail) {
  $raw = [IO.File]::ReadAllText($FailureDetail)
  Write-Output (Get-FailureDetail $raw $Stderr $ExitCode)
  exit 0
}

# Shared, thread-safe state for the listener and its workers.
$State = [hashtable]::Synchronized(@{
  running    = [hashtable]::Synchronized(@{})   # job_id -> Process (and __killed__<id> markers)
  status     = [hashtable]::Synchronized(@{})   # cli status cache
  lastUpdate = [hashtable]::Synchronized(@{})
})

if ($Health) { Get-HealthPayload $State | ConvertTo-Json -Compress; exit 0 }

# ck-agent.conf beside this file (written by the seat setup script): origin=, port=. The
# environment wins when set; the conf carries the settings into a Windows logon task,
# which has no environment of its own.
$Conf = @{}
$confPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'ck-agent.conf'
if (Test-Path -LiteralPath $confPath) {
  foreach ($line in Get-Content -LiteralPath $confPath) {
    if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.*?)\s*$') { $Conf[$Matches[1]] = $Matches[2] }
  }
}
# agent.log beside this file: the agent runs hidden, so this is what a person (or Claude,
# over a redirected RDP drive) reads when a seat misbehaves. Rotated once at 5 MB.
$LogPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'agent.log'
try {
  if ((Test-Path -LiteralPath $LogPath) -and (Get-Item -LiteralPath $LogPath).Length -gt 5MB) {
    Move-Item -LiteralPath $LogPath -Destination "$LogPath.1" -Force
  }
} catch { }
$State['logPath'] = $LogPath
function Say([string]$msg) { Write-Host $msg; Write-AgentLog $msg $State }

$Port = [int]($(if ($env:CK_AGENT_PORT) { $env:CK_AGENT_PORT } elseif ($Conf.ContainsKey('port') -and $Conf['port']) { $Conf['port'] } else { 8765 }))
$AllowedOrigin = $(if ($env:CK_AGENT_ORIGIN) { $env:CK_AGENT_ORIGIN } elseif ($Conf.ContainsKey('origin') -and $Conf['origin']) { $Conf['origin'] } else { '*' })

function Send-Json($ctx, [int]$code, $payload) {
  $res = $ctx.Response
  $origin = $ctx.Request.Headers['Origin']
  $allow = $(if ($AllowedOrigin -eq '*' -and $origin) { $origin } else { $AllowedOrigin })
  $res.Headers['Access-Control-Allow-Origin'] = $(if ($allow) { $allow } else { '*' })
  $res.Headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
  $res.Headers['Access-Control-Allow-Headers'] = 'Content-Type'
  $res.StatusCode = $code
  $res.ContentType = 'application/json'
  $bytes = [System.Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json -Compress -Depth 8))
  $res.ContentLength64 = $bytes.Length
  $res.OutputStream.Write($bytes, 0, $bytes.Length)
  $res.OutputStream.Close()
}

# Worker: runs a POST body handler in its own runspace so the listener keeps answering.
$WorkerScript = @"
param(`$ctx, `$State, `$route, `$body, `$AllowedOrigin, `$Port)
. ([scriptblock]::Create(@'
$LibText
'@))
function Send-Json(`$ctx, [int]`$code, `$payload) {
  `$res = `$ctx.Response
  `$origin = `$ctx.Request.Headers['Origin']
  `$allow = `$(if (`$AllowedOrigin -eq '*' -and `$origin) { `$origin } else { `$AllowedOrigin })
  `$res.Headers['Access-Control-Allow-Origin'] = `$(if (`$allow) { `$allow } else { '*' })
  `$res.Headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
  `$res.Headers['Access-Control-Allow-Headers'] = 'Content-Type'
  `$res.StatusCode = `$code
  `$res.ContentType = 'application/json'
  `$bytes = [System.Text.Encoding]::UTF8.GetBytes((`$payload | ConvertTo-Json -Compress -Depth 8))
  `$res.ContentLength64 = `$bytes.Length
  `$res.OutputStream.Write(`$bytes, 0, `$bytes.Length)
  `$res.OutputStream.Close()
}
try {
  if (`$route -eq '/update') {
    `$r = Invoke-ClaudeUpdate (Find-Claude) `$State
    `$r['health'] = Get-HealthPayload `$State
    Send-Json `$ctx 200 `$r
  } else {
    `$prompt = [string]`$body.prompt
    `$model = `$(if (`$body.PSObject.Properties['model']) { [string]`$body.model } else { 'default' })
    `$timeout = `$(if (`$body.PSObject.Properties['timeout'] -and `$body.timeout) { [int]`$body.timeout } else { `$script:DEFAULT_TIMEOUT })
    `$jobId = `$(if (`$body.PSObject.Properties['job_id']) { [string]`$body.job_id } else { '' })
    `$system = `$(if (`$body.PSObject.Properties['system']) { [string]`$body.system } else { '' })
    `$r = Invoke-Claude `$prompt `$model `$timeout `$jobId `$system `$State
    Send-Json `$ctx 200 `$r
  }
} catch {
  Write-AgentLog "ERROR worker `$route : `$_" `$State
  try { Send-Json `$ctx 200 @{ content = "ERROR: `$_"; error = `$true } } catch { }
}
"@

$Pool = [runspacefactory]::CreateRunspacePool(1, 8)
$Pool.Open()
$Workers = New-Object System.Collections.ArrayList

function Start-Worker($ctx, $route, $body) {
  $ps = [powershell]::Create()
  $ps.RunspacePool = $Pool
  [void]$ps.AddScript($WorkerScript).AddArgument($ctx).AddArgument($State).AddArgument($route).AddArgument($body).AddArgument($AllowedOrigin).AddArgument($Port)
  $handle = $ps.BeginInvoke()
  [void]$Workers.Add(@{ ps = $ps; handle = $handle })
  # Reap finished workers.
  foreach ($w in @($Workers)) { if ($w.handle.IsCompleted) { try { $w.ps.EndInvoke($w.handle) | Out-Null } catch { }; $w.ps.Dispose(); $Workers.Remove($w) } }
}

$cliNow = Find-Claude
Say "ck-agent $($script:AGENT_VERSION) (Windows/PowerShell) starting on http://127.0.0.1:$Port (pid $PID, log $LogPath)"
Say "  claude CLI: $(if ($cliNow) { "found at $cliNow" } else { 'NOT FOUND - install + log in first' })"
if ($cliNow) {
  if ($env:CK_AGENT_UPDATE_ON_START -eq '0') { Say '  claude update: skipped (CK_AGENT_UPDATE_ON_START=0)' }
  else {
    Say '  claude update: checking...'
    $u = Invoke-ClaudeUpdate $cliNow $State
    if ($u.ContainsKey('error')) { Say "  claude update: FAILED - $($u.error) (continuing with $($u.from))" }
    elseif ($u.updated) { Say "  claude update: $($u.from) -> $($u.to)" }
    else { Say "  claude update: up to date ($($u.to))" }
  }
  $st = Get-CliStatus $cliNow $State.status
  Say "  claude login: $(if ($st.logged_in) { "yes ($($st.org))" } else { 'NO - run: claude auth login' })"
}
Say "  CORS origin: $AllowedOrigin"
Say "  Leave this running; select 'Claude Code CLI (my local machine)' in Ask CK."

$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://127.0.0.1:$Port/")
try { $Listener.Start() } catch {
  # A hidden process that dies here leaves no trace anywhere else (port taken, URL ACL...).
  Say "FATAL: cannot listen on http://127.0.0.1:$Port/ - $_"
  exit 1
}
Say "  listening."
$Stopping = $false
try {
  while (-not $Stopping -and $Listener.IsListening) {
    $ctx = $Listener.GetContext()
    $req = $ctx.Request
    $route = $req.Url.AbsolutePath
    try {
      if ($req.HttpMethod -eq 'OPTIONS') {
        $origin = $req.Headers['Origin']
        $allow = $(if ($AllowedOrigin -eq '*' -and $origin) { $origin } else { $AllowedOrigin })
        $ctx.Response.Headers['Access-Control-Allow-Origin'] = $(if ($allow) { $allow } else { '*' })
        $ctx.Response.Headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        $ctx.Response.Headers['Access-Control-Allow-Headers'] = 'Content-Type'
        $ctx.Response.StatusCode = 204
        $ctx.Response.OutputStream.Close()
        continue
      }
      if ($req.HttpMethod -eq 'GET') {
        if ($route -eq '/health') { Send-Json $ctx 200 (Get-HealthPayload $State) } else { Send-Json $ctx 404 @{ error = 'not found' } }
        continue
      }
      if ($req.HttpMethod -ne 'POST' -or $route -notin @('/run', '/cancel', '/update', '/shutdown')) {
        Send-Json $ctx 404 @{ error = 'not found' }; continue
      }
      if ($route -in @('/update', '/shutdown')) {
        # State-changing routes insist on JSON so a cross-site "simple" POST (text/plain, no
        # preflight) cannot reach them; the preflight is answered for the Ask CK origin only.
        $ctype = ([string]$req.ContentType).Split(';')[0].Trim().ToLower()
        if ($ctype -ne 'application/json') { Send-Json $ctx 415 @{ ok = $false; error = 'Content-Type must be application/json' }; continue }
      }
      $reader = New-Object IO.StreamReader($req.InputStream, [System.Text.Encoding]::UTF8)
      $bodyText = $reader.ReadToEnd(); $reader.Close()
      $body = $null
      try { $body = $(if ($bodyText.Trim()) { $bodyText | ConvertFrom-Json } else { [pscustomobject]@{} }) } catch { $body = $null }
      if ($null -eq $body) { Send-Json $ctx 400 @{ content = 'ERROR: bad JSON body'; error = $true }; continue }
      switch ($route) {
        '/cancel' {
          $jid = $(if ($body.PSObject.Properties['job_id']) { [string]$body.job_id } else { '' })
          $killed = Stop-AgentJob $jid $State
          Write-AgentLog "cancel $jid -> killed=$killed" $State
          Send-Json $ctx 200 @{ ok = $true; killed = $killed }
        }
        '/shutdown' {
          Write-AgentLog "shutdown requested by $($req.RemoteEndPoint)" $State
          Send-Json $ctx 200 @{ ok = $true; agent_version = $script:AGENT_VERSION; stopping = $true }
          $Stopping = $true
        }
        '/run' {
          $hasPrompt = $false
          try { $hasPrompt = [bool]$body.prompt } catch { }
          if (-not $hasPrompt) { Send-Json $ctx 400 @{ content = 'ERROR: no prompt'; error = $true } }
          else { Start-Worker $ctx '/run' $body }
        }
        '/update' { Start-Worker $ctx '/update' $body }
      }
    } catch {
      Write-AgentLog "ERROR handling $route : $_" $State
      try { Send-Json $ctx 500 @{ content = "ERROR: $_"; error = $true } } catch { }
    }
  }
} finally {
  try { $Listener.Stop() } catch { }
  try { $Pool.Close(); $Pool.Dispose() } catch { }
  Say 'ck-agent stopped.'
}
