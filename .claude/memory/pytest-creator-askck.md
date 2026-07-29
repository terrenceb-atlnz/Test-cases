---
name: pytest-creator-askck
description: "PyTest Creator tool in Ask CK — current flow shape, tracker location, and what remains (tb470 execution, .setup parsing)"
metadata:
  node_type: memory
  type: project
  originSessionId: 3813cc75-639d-4e62-abb8-fd384442d015
  modified: 2026-07-28T02:34:43.796Z
---

The **PyTest Creator** (a tool inside the Ask CK FastAPI workbench at
`copilot/Test-cases/ask-ck/CK-main/CK_server/`) turns refined AWPTCM cases into runnable
Allied Telesis `framework` (ATTestSet/ATTestCase) scripts, then runs them on real hardware
over SSH and iterates via an LLM fix loop.

The living plan/progress tracker is `copilot/Test-cases/ask-ck/pytest-create/PLAN-pytest-creator.md`
— **update it as milestones land** (user explicitly wants progress tracked there). Testing
status lives in the companion `PLAN-pytest-testing.md`.

Facts that have CHANGED since this memory was first written (2026-07-14) — do not trust the
older phrasing found in historical doc entries:

- The flow is **7 steps, not 8** — Fit Decision was removed 2026-07-23. Internal `stepN`
  session keys are unchanged (fragments are still `step5`, generate `step6`).
- Generation **fills a fixed skeleton** (`templates/pt_script_template.py.jinja`); it is not
  a free compose.
- All script source comes from **`ck.db`** — the old script mount (`testsuites_art/` etc.)
  is retired and guarded against. The testbox framework dir is read-only, also guarded.

Remaining as of 2026-07-28: **Part 3b** (execution judging on tb470) needs `configs/tb470.setup`
— the schema is no longer the blocker (captured in `SETUP-FILE-REFERENCE.md`), only tb470's
device list and physical wiring are. Parsing `.setup` inside `CK_server` is the outstanding
design follow-up ([[setup-file-declares-topology]]). T33234 TestCase_8 is still graded bad.

Conventions: `framework` is a whole library (not just the two base classes); generated
scripts go to `generated/<Group>/<Name>.py` with names the user can edit at creation;
testbox profiles need `tb_number` + IP minimum, stored in gitignored `secrets.testboxes.json`;
server runs via `ask-ck/CK-main/run.sh` on port 8000. Reaching a device by hand:
[[testbox-console-access]].
