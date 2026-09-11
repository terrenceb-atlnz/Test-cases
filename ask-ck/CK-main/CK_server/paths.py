"""
Filesystem anchors for the Ask CK server.

Single source of truth for repo-layout paths after the ask-ck/ restructure:
    Test-cases/
    └── ask-ck/
        ├── CK-main/CK_server/       <- this package (the backend)
        ├── frontend/ck-main/current <- the served front-end (FRONTEND_DIR); svelte/ beside it
        ├── functions/               <- one directory per page (2026-09-11 restructure)
        │   ├── generator/           <- Generator data, refined-cases, process docs, PROGRESS.md
        │   ├── pytest-creator/      <- PyTest Creator specs + generated/
        │   ├── test-composer/
        │   └── zephyr-tool/
        ├── tools/                   <- scripts not called by a page button (gate, guards, loaders)
        ├── plans/
        └── db/                      <- ck.db + models/ (DB_DIR)
"""

from pathlib import Path

CK_SERVER_DIR = Path(__file__).resolve().parent            # .../ask-ck/CK-main/CK_server
ASKCK_ROOT = CK_SERVER_DIR.parent.parent                   # .../ask-ck

OBJECTIVE_DRAFTING_ROOT = ASKCK_ROOT / "functions" / "generator"
REFINED_DIR = OBJECTIVE_DRAFTING_ROOT / "refined-cases"
PROCESS_MD = OBJECTIVE_DRAFTING_ROOT / "OBJECTIVE_DRAFTING_PROCESS.md"
# NOTE: the old corpus dir OBJECTIVE_DRAFTING_ROOT/"data" (and pytest-create/"data")
# is retired — all corpora live in ck.db now. No DATA_DIR / PT_DATA_DIR anchor
# exists on purpose: nothing at runtime may read corpus JSON off disk.

# PyTest Creator (see ask-ck/plans/PLAN-pytest-creator.md)
PYTEST_CREATE_ROOT = ASKCK_ROOT / "functions" / "pytest-creator"
PT_GENERATED_DIR = PYTEST_CREATE_ROOT / "generated"

# LLM observability (see archive/plans/PLAN-llm-observability.md)
DEBUG_LOG_DIR = CK_SERVER_DIR / "debug-log"                 # per-session LLM request JSONL (gitignored)
LOCAL_LLM_SECRETS = CK_SERVER_DIR / "secrets.local.json"    # app-owned Local LLM key (gitignored via secrets.*)

# SQLite data layer (see archive/plans/PLAN-db-only-search.md)
# ck.db is the PERMANENT single source of truth — built once, shipped via Git LFS,
# NOT rebuildable and NOT a cache. The intermediate corpus JSON it was built from has
# been retired/deleted; the running server reads corpora ONLY from ck.db (db.py).
DB_DIR = ASKCK_ROOT / "db"                                  # .../ask-ck/db  (was var/ until 2026-09-11)
DB_PATH = DB_DIR / "ck.db"                                  # SQLite (FTS5 + sqlite-vec) single file
EMBED_MODEL_DIR = DB_DIR / "models"                         # local sentence-transformers cache

# The current (pre-Svelte) front-end: index.html, styles.css, assets and the ES modules sorted
# into page directories (generator/, pytest-creator/, llm-config/, admin/, shared/). Served at
# /static by main.py. Moved out of CK_server/static on 2026-09-11 (PLAN-restructure batch 7);
# the Svelte rewrite will live beside it at frontend/ck-main/svelte/.
FRONTEND_DIR = ASKCK_ROOT / "frontend" / "ck-main" / "current"
