# Autopilot batch — resumption note

**Task:** for the 10 AWPTCM cases in `batch-10.txt`, create objectives + refined test cases +
pytest scripts with **Opus**, judge them, and attempt to run them on tb470. Started 2026-07-30.

If a session ends mid-batch, everything needed to continue is on disk. Nothing here needs
re-deriving from conversation.

## The one setup step a new session must redo

The workspace LLM default is the thing that decides which model the pipeline uses. Check it,
and set it if it drifted back:

```bash
curl -s localhost:8000/api/wizard/llm_config          # expect claude / claude_code / claude-opus-5
curl -s -X POST localhost:8000/api/wizard/set_llm_config -H 'Content-Type: application/json' \
  -d '{"provider":"claude","auth_method":"claude_code","model":"claude-opus-5"}'
```

`claude_code` is the headless server-side CLI mode: no browser session, no API key, runs on this
host's own `claude` login. `claude_agent` (the UI's Claude mode) CANNOT be driven headlessly — it
502s "needs a browser session id". See memory `workspace-llm-default-gotcha`.

**Restore when the batch is finished** — this is a workspace-wide default the UI also reads:

```bash
curl -s -X POST localhost:8000/api/wizard/set_llm_config -H 'Content-Type: application/json' \
  -d '{"provider":"openai","auth_method":"local_llm","model":"vllm-fast"}'
```

## Resuming the batch

```bash
python3 tool/pt_autopilot.py --cases-file ask-ck/pytest-create/autopilot/batch-10.txt \
        --phase all --run-dir ask-ck/pytest-create/autopilot/<STAMP>
```

Re-running is always safe and never re-pays for finished work: autopilot skips a case whose
phase is already `ok` in `state.json`, and within a case it re-reads the live server session and
skips any step already confirmed. `--status` prints the batch at a glance.

## What is expected to be slow

Sequence extraction and generation are minutes-per-case on Opus, because these refined cases are
large (the Generator expands a title + a few hundred characters of source into 30–45 Zephyr
steps, and sequence extraction emits a row per step). Budget on the order of 10–20 min per case
for the PyTest phase. A `claude -p` child of the uvicorn process is the sign it is working:

```bash
pgrep -af 'claude -p'
```

## Phase order and where each phase's output lands

| Phase | Command | Output |
|---|---|---|
| Generator | `--phase generator` | `ask-ck/objective-drafting/refined-cases/<Group>/<KEY>/` |
| PyTest Creator | `--phase pytest` | `ask-ck/pytest-create/generated/<Group>/<name>.py` |
| Mechanical judge | `tool/pt_grade.py --out <dir>` | `<dir>/<KEY>/mechanical.json` |
| LLM judge | `tool/pt_judge.py --judges opus,vllm-fast --out <dir>` | `<dir>/<KEY>/criterion4.json` |
| Preflight | `tool/pt_preflight.py --setup ~/claude/IE520-testing/bench-setup/tb470.setup.current` | stdout verdicts |
| Run | see below | `ask-ck/pytest-create/generated/.meta/<Group>/<name>/runs/<RUN_ID>/` |

## The tb470 run phase — the one thing that needs an environment change

`pt_exec` connects with paramiko. Key auth would use `~/.ssh/id_rsa`, which is
**passphrase-encrypted and therefore useless non-interactively**; the working key lives only in
the Linux gnome-keyring agent. The running dev server inherited VS Code's forwarded (empty) Mac
agent socket, so it cannot authenticate to a testbox as started.

Restart the server so it inherits the keyring agent, then create the profile:

```bash
export SSH_AUTH_SOCK="${XDG_RUNTIME_DIR:-/run/user/1971}/keyring/ssh"
ssh-add -l                        # must list the RSA key
./ask-ck/CK-main/run.sh --restart # inherits the env; also drops --reload, which is what you want
                                  # mid-batch anyway (an editor save must not bounce the server)
```

Verified facts about the bench account (2026-07-30): `terrenceb@tb470` authenticates with that
agent key, has **passwordless sudo**, python3 **3.13.5**, and `/home/st-art/framework` present.
`st-art@tb470` does **not** authenticate with it — so the profile must set `user: terrenceb`,
not the `st-art` default.

```bash
curl -s -X POST localhost:8000/api/pytest-create/profiles -H 'Content-Type: application/json' -d '{
  "name": "tb470", "tb_number": "470", "host": "tb470", "user": "terrenceb", "auth": "key",
  "setups": {"tb470": "/home/st-art/st-art/configs/tb470.setup"}}'
curl -s -X POST localhost:8000/api/pytest-create/profiles/tb470/check
```

## Bench state to respect (do not rediscover the hard way)

- Roles: **IE520s = `swi_a`/`swi_b`, AR4050S = `swi_c`, x230 = `swi_d`**. `swi_a` is the DUT per
  the setup's own `[misc] ck_role_dut`.
- Declared links: copper `port1.0.1`, fibre `port1.0.7` (both `swi_a`↔`swi_b`), and
  `tb-swi_a = eth3-port1.0.23`. **No `swi_a`↔`swi_c` data link exists.**
- The bench implements profiles `base, fibre, tblink`; **not `stack`**.
- ⚠️ **Never cable `port1.0.27/1.0.28` between the two IE520s** — both are stack ID 1 sharing
  chassis-id 3039, so a stackport link recreates the duplicate-master / all-ports-err-disabled
  state that took a session to escape.
- Neither IE520 is on the PDU, so **the DUT cannot be power-cycled** — a reboot must go over the
  CLI.

## Fix made during this batch (already applied)

`routers/pytest_create.py` `extract_sequence` passed no `timeout` to `run_prompt`, so it
inherited the 180s default while every sibling LLM step asked for 300–600s. A 42-step case timed
out at exactly 180s every attempt, and the 502 text blames the LLM rather than the missing
kwarg. Now `timeout=600`; pinned by `tests/test_llm_call_timeouts.py`.
