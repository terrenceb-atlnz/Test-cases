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
DATA_DIR = OBJECTIVE_DRAFTING_ROOT / "data"
REFINED_DIR = OBJECTIVE_DRAFTING_ROOT / "refined-cases"
PROCESS_MD = OBJECTIVE_DRAFTING_ROOT / "OBJECTIVE_DRAFTING_PROCESS.md"

# PyTest Creator (see ask-ck/pytest-create/PLAN-pytest-creator.md)
PYTEST_CREATE_ROOT = ASKCK_ROOT / "pytest-create"
PT_DATA_DIR = PYTEST_CREATE_ROOT / "data"
PT_GENERATED_DIR = PYTEST_CREATE_ROOT / "generated"
