<#
Ask CK seat setup — Windows (PowerShell 5.1+).

Served by the Ask CK server at <server>/setup/setup.ps1 and run with ONE line copied from
the Ask CK home page:

    irm http://10.33.22.17:8000/setup/setup.ps1 | iex

What it does, every time it runs (re-running is how you update or repair):
  Install ✔  find the Claude Code CLI, install it if absent, fix the user PATH, `claude update`
  Login   ✔  `claude auth status`; if not logged in, `claude auth login` (opens the browser)
  Agent   ✔  download/refresh ck-agent from the server, start it hidden (replace a stale one),
             optionally register it to start at logon, and confirm it is up + logged in
then it opens Ask CK, which runs the final, authoritative check itself.

Contract + design: ask-ck/ck-facelift/PLAN-seat-setup-and-per-seat-llm.md §3.3.

Knobs (environment variables, because `irm | iex` cannot take parameters):
  $env:CK_SERVER = 'http://host:port'    the Ask CK server (the served copy has it filled in)
  $env:CK_SETUP_AUTOSTART = 'yes'|'no'|'ask'   register the agent at logon (default: ask once, remember)
  $env:CK_SETUP_NO_OPEN = '1'            do not open the browser at the end
  $env:CK_SETUP_NO_UPDATE = '1'          skip `claude update`
#>
$ErrorActionPreference = 'Stop'

$CK_SERVER = if ($env:CK_SERVER) { $env:CK_SERVER } else { '__CK_SERVER__' }
if ($CK_SERVER -like '__CK_*') { $CK_SERVER = 'http://10.33.22.17:8000' }
$CK_SERVER = $CK_SERVER.TrimEnd('/')
$AgentPort = if ($env:CK_AGENT_PORT) { [int]$env:CK_AGENT_PORT } else { 8765 }
$AgentUrl = "http://127.0.0.1:$AgentPort"
$AgentDir = Join-Path $env:LOCALAPPDATA 'ck-agent'
$AgentFile = Join-Path $AgentDir 'ck-agent.ps1'
$Conf = Join-Path $AgentDir 'ck-agent.conf'
$InstallDir = Join-Path $env:USERPROFILE '.local\bin'
$TaskName = 'Ask CK agent (ck-agent)'

function Ok($msg)   { Write-Host "[OK]  $msg" -ForegroundColor Green }
function Bad($msg)  { Write-Host "[X]   $msg" -ForegroundColor Red }
function Note($msg) { Write-Host "      $msg" -ForegroundColor DarkGray }
function Die($msg)  { Bad $msg; if ($Host.Name -eq 'ConsoleHost') { Write-Host 'Press Enter to close.'; [void](Read-Host) }; exit 1 }

Write-Host "Ask CK seat setup - server $CK_SERVER"
Write-Host ''

# ------------------------------------------------------------------------------------------
# Install
# ------------------------------------------------------------------------------------------
function Find-Claude {
  $exe = Join-Path $InstallDir 'claude.exe'
  if (Test-Path -LiteralPath $exe) { return $exe }
  $cmd = Get-Command claude -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($cmd) { return $cmd.Source }
  return $null
}

function Ensure-UserPath {
  # The native installer writes %USERPROFILE%\.local\bin\claude.exe and does NOT put it on
  # PATH (demo-day issue #1). Fix the USER PATH (registry, no admin) and this session's.
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  $parts = @()
  if ($userPath) { $parts = $userPath -split ';' | Where-Object { $_ } }
  if (-not ($parts | Where-Object { $_.TrimEnd('\') -ieq $InstallDir.TrimEnd('\') })) {
    [Environment]::SetEnvironmentVariable('Path', (($parts + $InstallDir) -join ';'), 'User')
    Note "PATH fixed for your account - new terminals will see 'claude'; existing ones need reopening."
  }
  if (-not (($env:Path -split ';') | Where-Object { $_.TrimEnd('\') -ieq $InstallDir.TrimEnd('\') })) {
    $env:Path = "$InstallDir;$env:Path"
  }
}

$Claude = Find-Claude
$freshInstall = $false
if (-not $Claude) {
  Note 'Claude Code CLI not found - installing (official installer, needs HTTPS to claude.ai)...'
  try { Invoke-Expression (Invoke-RestMethod -Uri 'https://claude.ai/install.ps1' -UseBasicParsing) | Out-Null }
  catch { Die "Install: the Claude Code installer failed ($_). Check network access to claude.ai and re-run." }
  $freshInstall = $true
  Ensure-UserPath
  $Claude = Find-Claude
  if (-not $Claude) { Die "Install: installer ran but claude.exe was not found in $InstallDir." }
} else {
  Ensure-UserPath
}

if (-not $freshInstall -and $env:CK_SETUP_NO_UPDATE -ne '1') {
  Note 'claude update...'
  try { & $Claude update 2>&1 | Out-Null } catch { Note 'claude update reported a problem (continuing with the installed version).' }
}
$claudeVersion = ''
try { $v = (& $Claude --version 2>&1 | Out-String); if ($v -match '\d+\.\d+\.\d+') { $claudeVersion = $Matches[0] } } catch { }
Ok "Install - Claude Code $claudeVersion at $Claude"

# ------------------------------------------------------------------------------------------
# Login
# ------------------------------------------------------------------------------------------
function Get-Auth {
  try {
    $out = (& $Claude auth status 2>$null | Out-String).Trim()
    if ($out) { return ($out | ConvertFrom-Json) }
  } catch { }
  return $null
}
$auth = Get-Auth
if (-not ($auth -and $auth.loggedIn)) {
  Note "Not logged in - starting 'claude auth login' (it opens your browser)..."
  try { & $Claude auth login } catch { }
  $auth = Get-Auth
  if (-not ($auth -and $auth.loggedIn)) { Die "Login: still not logged in after 'claude auth login'. Run it again and re-run this." }
}
$org = ''
try { if ($auth.orgName) { $org = " as $($auth.orgName)" } } catch { }
Ok "Login - logged in$org"

# ------------------------------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------------------------------
New-Item -ItemType Directory -Path $AgentDir -Force | Out-Null

function Get-Health {
  try { return Invoke-RestMethod -Uri "$AgentUrl/health" -TimeoutSec 5 -UseBasicParsing } catch { return $null }
}
function Read-Conf {
  $h = @{}
  if (Test-Path -LiteralPath $Conf) {
    foreach ($line in Get-Content -LiteralPath $Conf) {
      if ($line -match '^\s*([A-Za-z_]+)\s*=\s*(.*?)\s*$') { $h[$Matches[1]] = $Matches[2] }
    }
  }
  return $h
}
function Write-Conf($h) {
  $lines = foreach ($k in ($h.Keys | Sort-Object)) { "$k=$($h[$k])" }
  Set-Content -LiteralPath $Conf -Value $lines -Encoding ASCII
}

try { $manifest = Invoke-RestMethod -Uri "$CK_SERVER/setup/manifest.json" -TimeoutSec 15 -UseBasicParsing }
catch { Die "Agent: cannot reach $CK_SERVER/setup/manifest.json - is the Ask CK server up?" }
$wantVersion = [string]$manifest.agent_version
$wantSha = [string]$manifest.files.'ck-agent.ps1'

$haveSha = ''
$downloaded = $false
if (Test-Path -LiteralPath $AgentFile) { $haveSha = (Get-FileHash -LiteralPath $AgentFile -Algorithm SHA256).Hash.ToLower() }
if ($haveSha -ne $wantSha.ToLower()) {
  $downloaded = $true
  $tmp = "$AgentFile.new"
  try { Invoke-WebRequest -Uri "$CK_SERVER/setup/ck-agent.ps1" -OutFile $tmp -TimeoutSec 30 -UseBasicParsing }
  catch { Die "Agent: download of ck-agent.ps1 failed ($_)." }
  $got = (Get-FileHash -LiteralPath $tmp -Algorithm SHA256).Hash.ToLower()
  if ($got -ne $wantSha.ToLower()) { Remove-Item -LiteralPath $tmp -Force; Die "Agent: downloaded ck-agent.ps1 does not match the server's manifest." }
  Move-Item -LiteralPath $tmp -Destination $AgentFile -Force
  Note "ck-agent $wantVersion downloaded."
}

$conf = Read-Conf
$conf['origin'] = $CK_SERVER
$conf['port'] = "$AgentPort"

# Autostart is the user's choice (plan D6): ask once, remember, honour the knob.
$choice = if ($conf.ContainsKey('autostart')) { $conf['autostart'] } else { '' }
switch ($env:CK_SETUP_AUTOSTART) {
  'yes' { $choice = 'yes' }
  'no'  { $choice = 'no' }
  default {
    if (-not $choice) {
      $answer = ''
      try { $answer = Read-Host 'Start the Ask CK agent automatically when you log in? [Y/n]' } catch { $answer = 'n' }
      $choice = if ($answer -match '^(n|no)$') { 'no' } else { 'yes' }
    }
  }
}
$conf['autostart'] = $choice
Write-Conf $conf

$agentArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$AgentFile`""
function Start-Agent {
  $env:CK_AGENT_ORIGIN = $CK_SERVER
  $env:CK_AGENT_PORT = "$AgentPort"
  # stderr to agent.err: a script that fails to PARSE never reaches its own agent.log.
  Start-Process -FilePath 'powershell.exe' -ArgumentList $agentArgs -WindowStyle Hidden -WorkingDirectory $AgentDir -RedirectStandardError (Join-Path $AgentDir 'agent.err') | Out-Null
}
function Register-Autostart {
  # Per-user task at logon, no admin. The agent reads origin/port from ck-agent.conf when
  # the environment does not carry them, so the task needs no environment of its own.
  & schtasks.exe /Create /F /SC ONLOGON /TN "$TaskName" /TR "powershell.exe $agentArgs" 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { Note 'Agent registered to start at logon (Task Scheduler).' } else { Note 'Could not register the logon task (schtasks failed); the agent is running for this session.' }
}
function Unregister-Autostart {
  & schtasks.exe /Query /TN "$TaskName" 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { & schtasks.exe /Delete /F /TN "$TaskName" 2>&1 | Out-Null }
}
function Stop-RunningAgent {
  try { Invoke-RestMethod -Uri "$AgentUrl/shutdown" -Method Post -ContentType 'application/json' -Body '{}' -TimeoutSec 5 -UseBasicParsing | Out-Null } catch { }
  for ($i = 0; $i -lt 6; $i++) { if (-not (Get-Health)) { return $true }; Start-Sleep -Milliseconds 500 }
  # No /shutdown (or it ignored us): find the listener on our port and, only if it is a
  # PowerShell running ck-agent, stop it the hard way.
  try {
    $owners = Get-NetTCPConnection -LocalPort $AgentPort -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $owners) {
      $p = Get-CimInstance Win32_Process -Filter "ProcessId = $procId" -ErrorAction SilentlyContinue
      if ($p -and $p.CommandLine -match 'ck-agent') { Note "Stopping old agent (pid $procId)..."; Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue }
    }
  } catch { }
  for ($i = 0; $i -lt 10; $i++) { if (-not (Get-Health)) { return $true }; Start-Sleep -Milliseconds 500 }
  return $false
}

$running = Get-Health
$runningVersion = if ($running) { [string]$running.agent_version } else { '' }
if ($running -and $runningVersion -eq $wantVersion -and -not $downloaded) {
  # up to date and running; nothing to restart
} elseif ($running) {
  # A different version, OR the same version with new bytes: the running process is stale.
  Note "Replacing agent $(if ($runningVersion) { $runningVersion } else { '<unknown>' }) with $wantVersion..."
  if (-not (Stop-RunningAgent)) { Die "Agent: the old agent on port $AgentPort did not stop. Stop it and re-run." }
  Start-Agent
} else {
  Start-Agent
}
if ($choice -eq 'yes') { Register-Autostart } else { Unregister-Autostart }

# Wait for health - the agent runs `claude update` at startup, which can take a while.
$final = $null
for ($i = 0; $i -lt 90; $i++) { $final = Get-Health; if ($final) { break }; Start-Sleep -Seconds 1 }
if (-not $final) { Die "Agent: not answering on $AgentUrl after start. Read $AgentDir\agent.log (and agent.err if the script itself failed)." }
if (-not $final.claude_cli) { Die "Agent: up ($($final.agent_version)) but it cannot find the Claude CLI. $($final.hint)" }
if ($final.logged_in -ne $true) { Die "Agent: up ($($final.agent_version)) but the CLI is not logged in as seen by the agent. $($final.hint)" }
Ok "Agent - ck-agent $($final.agent_version) up on $AgentUrl, CLI $($final.cli_version), logged in$(if ($choice -eq 'yes') { ', autostart on' })"
Note "Agent log: $AgentDir\agent.log"

Write-Host ''
Write-Host 'All good. Opening Ask CK - the page will run the final check itself.'
if ($env:CK_SETUP_NO_OPEN -ne '1') { Start-Process "$CK_SERVER/?seat-check=1" | Out-Null } else { Write-Host "Open: $CK_SERVER/?seat-check=1" }
exit 0
