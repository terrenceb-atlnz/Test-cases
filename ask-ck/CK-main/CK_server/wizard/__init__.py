"""Pure helpers lifted out of `routers/wizard.py` (PLAN-backend-module-split.md, Part B).

This package holds the Generator's *logic* — text shaping, gates, backfill — with no
FastAPI surface of its own. `routers/wizard.py` keeps the endpoints and imports from
here, so the route layer stays about HTTP and these stay unit-testable without a
TestClient.

Note the two similar names, which are deliberately different layers:
  * `wizard.*`          — this package, at CK_server root: pure, importable by anyone.
  * `routers.wizard`    — the HTTP router (later a `routers/wizard/` package itself).

Nothing here may import `routers.*`; the dependency runs one way only.
"""
