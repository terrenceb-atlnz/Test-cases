---
name: editing-backend-restarts-production
description: ask-ck.service runs uvicorn --reload against the working tree, so ANY save to CK_server/*.py bounces the live server — and a reload can wedge on the agent long-polls
metadata:
  type: project
  verified: 2026-09-22
---

The hosted server (`systemd --user` unit `ask-ck.service`, LAN on :8000) runs:

```
python -m uvicorn CK_server.main:app --host 0.0.0.0 --port 8000 --reload
```

`--reload` watches **this working tree**, and the working tree **is** production
([[askck-lan-hosting]]). So **every save to a `CK_server/*.py` file restarts the live server
other people are using.** Editing the backend is not a local-only act here.

**The reload can wedge rather than complete.** Observed 2026-09-17 09:24: an edit to `llm.py`
tripped `StatReload`, uvicorn began a graceful shutdown ("Waiting for connections to close"),
but the agent bridge holds **25-second long-polls** (`/api/agent/next?...&wait=25`) from every
open browser tab, so fresh connections kept arriving faster than it could drain. The old
worker never exited and **no replacement worker ever started** — both LAN and localhost timed
out while `systemctl status` still showed the unit "active (running)". It does not recover on
its own; `systemctl --user restart ask-ck.service` is the fix (never `run.sh --stop/--bg`,
see [[ask-ck-admin-restart]]).

A mutation-testing loop makes this far worse: rewriting the same module 6 times in seconds
fires 6 reloads. Run mutation checks on a **copy**, or accept that the server will bounce.

**How to apply:** before editing anything under `CK_server/`, know that you are restarting
production. Say so if others may be on it — check the journal for active sessions
(`journalctl --user -u ask-ck.service --since -2m | grep -oE 'session=sess-[a-z0-9]+' | sort -u`);
on 2026-09-17 a second seat (10.33.12.16) and an in-flight LLM call were killed by my edit.
Batch backend edits rather than saving repeatedly, and verify `/health` afterwards.

**Settled 2026-09-17 — `--reload` STAYS.** Terrence's call after the outage above: *"its fine
for now. if it happens often we will fix it."* So do not propose removing it again; work with
it (batch the edits, mutate on a copy, restart when it wedges). Revisit only if wedging
becomes a recurring cost — and then it is a change to the systemd unit, which lives outside
this repo at `~/.config/systemd/user/ask-ck.service`.

**2026-09-22 — the converse confirmed, and it is the useful half in practice.** A session that
edited only `ask-ck/frontend/**` and `tests/**` did NOT bounce the server: it kept answering
`/health` and serving `/static/**` throughout, and the edited modules were served immediately
with `cache-control: no-cache` + an etag, so open tabs pick them up on reload with no version
bump needed. **How to apply:** front-end-only work needs no idle window and no restart planning —
that constraint belongs to `CK-main/**/*.py` alone. (Not re-checked today: that a `.py` save
under `CK-main` still bounces it, or the long-poll wedge. Those remain as verified 2026-09-21.)
