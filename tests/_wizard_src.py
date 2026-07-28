"""Locate the Generator's HTTP router source — one file, or (commit 10) a package.

WHY THIS MODULE EXISTS
----------------------
`PLAN-backend-module-split.md` commit 10 split the 1971-line `routers/wizard.py` into a
`routers/wizard/` package (reviews / config / synthesis / export / _shared / __init__).
Several suites grep or AST-parse the router source by a hardcoded `routers/wizard.py`
path. After the move that path is gone, and the danger is not a red test — it is a
GREEN one: a read that silently finds nothing keeps passing while it stops covering the
handlers it was written for. The plan calls this out explicitly ("a glob that quietly
stops matching is not [loud]").

So every test resolves the router source through here. `wizard_router_paths()` raises if
it finds nothing, and `wizard_router_source()` concatenates the whole package — so the
NEXT structural move re-routes every caller at once, and an empty result fails loudly.
"""
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[1] / "ask-ck" / "CK-main" / "CK_server"


def wizard_router_paths():
    """Every .py file backing the wizard router, sorted. Package, or a legacy single file."""
    pkg = _SERVER / "routers" / "wizard"
    if pkg.is_dir():
        paths = sorted(pkg.rglob("*.py"))
    else:
        single = _SERVER / "routers" / "wizard.py"
        paths = [single] if single.exists() else []
    if not paths:
        raise FileNotFoundError(
            "wizard router source not found — looked for routers/wizard/ and routers/wizard.py")
    return paths


def wizard_router_source():
    """The whole wizard router as one text blob (all package files concatenated)."""
    return "\n".join(p.read_text(encoding="utf-8") for p in wizard_router_paths())
