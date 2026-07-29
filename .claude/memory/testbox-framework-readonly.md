---
name: testbox-framework-readonly
description: The testbox framework dir (/home/st-art/framework) is READ-ONLY for this project — never write/edit/mutate it
metadata: 
  node_type: memory
  type: project
  originSessionId: 6c4c3b5d-20a2-4e93-8a92-519e908e14e6
  modified: 2026-07-20T20:59:22.176Z
---

**Terrence's standing rule (2026-07-21):** the testbox framework directory —
`/home/st-art/framework` on tb470, i.e. the profile `framework_path` — is **READ-ONLY
for this project.** PyTest Creator (and anything else) may READ files there and COPY
them locally for editing (an explicit exception), but must NEVER write into it, edit a
file under it, or run a mutating command against it. Copy-to-workdir-and-edit-there is
the only sanctioned way to change a framework file, and it's out of scope as a general
rule.

**Why:** it's a shared/authoritative framework install on real hardware; mutating it
would corrupt the test environment for everyone and isn't this project's job.

**How to apply / enforced in code:**
- `CK_server/pt_exec.py::_assert_write_allowed()` guards every SFTP write target (run
  workdir + uploaded files) — a target at/under `framework_path` raises
  `FrameworkReadOnlyError` before writing.
- `CK_server/pt_exec.py::_assert_command_allowed()` scans the remote run command per
  sub-command (`&&`/`||`/`;`) and refuses a mutating verb (rm/mv/cp/touch/mkdir/chmod/
  ln/dd/truncate/tee/`sed -i`/patch…) whose WRITE TARGET is under the framework dir.
  Read-only refs pass: `test -d <fw>`, `PYTHONPATH=<fw>`, copy/symlink FROM fw, and
  `ln -s <fw> framework` (the current run path points a workdir symlink AT the fw).
- `tool/guard_framework_readonly.py` — runnable 15-case check; run it with
  `tool/guard_db_only.py` before committing execution-path changes.

Don't remove or weaken these guards. If asked to modify framework code, push back with
the copy-locally exception. Testbox reachable this seat: `ssh tb470` (device on u5,
passwordless sudo, framework at /home/st-art/framework). See the DB-only single-source
invariant [[db-only-single-source]] and the testing plan at
ask-ck/pytest-create/PLAN-pytest-testing.md §6.
