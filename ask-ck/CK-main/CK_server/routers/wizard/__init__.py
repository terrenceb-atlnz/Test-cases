"""The Generator (Objective / Test Case Generator) HTTP router.

Was a single 1971-line `routers/wizard.py`; split into this package
(PLAN-backend-module-split.md commit 10). The endpoints live in four route modules —
`reviews` (step 1/2/3 gates + case listing), `config` (session / LLM config),
`synthesis` (objectives + steps) and `export` (the drop-in bundle + push_to_zephyr) —
with the shared request dependency and export template env in `_shared`.

The names re-exported below are the router's public surface: `router` for `main.py` to
mount, plus the symbols the test suite imports directly (`from routers.wizard import …`)
or reaches through `import routers.wizard as wizard`.

`sessions` is re-exported as the SAME dict object `session_store` holds —
`routers.wizard.sessions is session_store.sessions` is asserted by a test and is what
keeps the in-memory cache and persistence pointed at one store; do not rebind it.
"""
from fastapi import APIRouter

from session_store import sessions

from ._shared import BASE_DIR, OUTPUTS_ENV, get_data
from . import config, export, reviews, synthesis
from .reviews import _parse_selections, confirm_step
from .synthesis import _authoritative_session
from .export import (
    _build_payload,
    _build_test_script,
    _render_traceability,
    _write_bundle,
    push_to_zephyr,
)

router = APIRouter()
router.include_router(reviews.router)
router.include_router(config.router)
router.include_router(synthesis.router)
router.include_router(export.router)
