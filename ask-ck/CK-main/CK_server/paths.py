"""
Filesystem anchors for the Ask CK server.

Single source of truth for repo-layout paths after the ask-ck/ restructure:
    Test-cases/
    └── ask-ck/
        ├── CK-main/CK_server/       <- this package
        ├── objective-drafting/      <- Generator data, refined-cases, process docs
        ├── pytest-create/
        ├── test-composer/
        └── zephyr-tool/
"""

from pathlib import Path

CK_SERVER_DIR = Path(__file__).resolve().parent            # .../ask-ck/CK-main/CK_server
ASKCK_ROOT = CK_SERVER_DIR.parent.parent                   # .../ask-ck

OBJECTIVE_DRAFTING_ROOT = ASKCK_ROOT / "objective-drafting"
REFINED_DIR = OBJECTIVE_DRAFTING_ROOT / "refined-cases"
PROCESS_MD = OBJECTIVE_DRAFTING_ROOT / "OBJECTIVE_DRAFTING_PROCESS.md"
# NOTE: the old corpus dir OBJECTIVE_DRAFTING_ROOT/"data" (and pytest-create/"data")
# is retired — all corpora live in ck.db now. No DATA_DIR / PT_DATA_DIR anchor
# exists on purpose: nothing at runtime may read corpus JSON off disk.

# PyTest Creator (see ask-ck/pytest-create/PLAN-pytest-creator.md)
PYTEST_CREATE_ROOT = ASKCK_ROOT / "pytest-create"
PT_GENERATED_DIR = PYTEST_CREATE_ROOT / "generated"

# LLM observability (see ask-ck/ck-facelift/PLAN-llm-observability.md)
DEBUG_LOG_DIR = CK_SERVER_DIR / "debug-log"                 # per-session LLM request JSONL (gitignored)
LOCAL_LLM_SECRETS = CK_SERVER_DIR / "secrets.local.json"    # app-owned Local LLM key (gitignored via secrets.*)

# SQLite data layer (see ask-ck/ck-facelift/PLAN-db-only-search.md)
# ck.db is the PERMANENT single source of truth — built once, shipped via Git LFS,
# NOT rebuildable and NOT a cache. The intermediate corpus JSON it was built from has
# been retired/deleted; the running server reads corpora ONLY from ck.db (db.py).
VAR_DIR = ASKCK_ROOT / "var"                                # .../ask-ck/var
DB_PATH = VAR_DIR / "ck.db"                                 # SQLite (FTS5 + sqlite-vec) single file
EMBED_MODEL_DIR = VAR_DIR / "models"                        # local sentence-transformers cache
