---
name: run-pt-lint-offline
description: How to run the PyTest Creator's own lint (_lint_generated) over ANY script file offline — a PtSession built from the case's stored pt- session with the code swapped in, against a scratch ck.db copy; used 2026-10-20 to lint a hand-written script on equal terms with the tool's
metadata:
  type: project
  verified: 2026-10-20
---

**The tool's lint is callable on a file that the tool did not generate.** `_lint_generated(sess)`
in `routers/pytest_create.py` reads only `sess.step6.files.test.code` (plus the session's
sequence for the verdict-echo and coverage checks), so a hand-written or edited script can be
judged by exactly the checks the Creator applies — the logging contract, the frame structure,
the house-rule bans, pycodestyle at 120 — with no server call and no write to the real db.

```bash
SCRATCH="$(.venv/bin/python ask-ck/tools/ckdb_scratch.py | tail -1)"   # WAL-consistent copy
CK_DB_PATH="$SCRATCH" .venv/bin/python - <<'EOF'
import os, sys, json, sqlite3, pathlib
CK = pathlib.Path('ask-ck/CK-main/CK_server').resolve(); sys.path[:0] = [str(CK), str(CK.parent)]
from routers import pytest_create as pc
from models import PtSession
con = sqlite3.connect('file:' + os.environ['CK_DB_PATH'] + '?mode=ro', uri=True)
p = json.loads(con.execute("select payload from sessions where id='pt-AWPTCM-T33241'").fetchone()[0])
p['step6'] = dict(p.get('step6') or {})
p['step6']['files'] = {'test': {'name': 'x.py', 'code': open('<the script>').read()}, 'library': None}
res = pc._lint_generated(PtSession(**{k: v for k, v in p.items() if k in PtSession.model_fields}))
print(res['ok'], res['errors'], res['warnings'], res['coverage'])
EOF
rm -f "$SCRATCH"     # 465 MB under /tmp/ck-scratch-db/
```

**Why the scratch copy:** importing `routers.pytest_create` imports the db layer; `CK_DB_PATH`
pointed at a copy means an accidental write can never reach the permanent `ck.db`
([[db-is-permanent-source]], [[ckdb-wal-and-test-isolation]]). The copy is 465 MB — delete it
after (Terrence, 2026-10-20: "delete").

**How to apply:** before comparing a script written outside the tool with the tool's own, run
both through this so neither has an unfair lint advantage; `library: None` tells the lint there
is no family library to resolve names against. Any `*.py` dropped into `generated/<family>/`
(except `library_*`) also appears in the Validation and Run Scripts pickers, without provenance.
