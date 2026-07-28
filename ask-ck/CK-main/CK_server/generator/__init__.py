"""Pure helpers lifted out of `routers/wizard.py` (PLAN-backend-module-split.md, Part B).

This package holds the Generator's *logic* — text shaping, gates, backfill — with no
FastAPI surface of its own. `routers/wizard.py` keeps the endpoints and imports from
here, so the route layer stays about HTTP and these stay unit-testable without a
TestClient.

Two layers, two names:
  * `generator.*`       — this package, at CK_server root: pure, importable by anyone.
  * `routers.wizard`    — the HTTP router (later a `routers/wizard/` package itself).

It was called `wizard` in commits 7 and 9, which made `wizard` mean two different things
once commit 10 turns the router into `routers/wizard/`. Python resolves that fine — absolute
imports, and `routers.wizard` is only reachable under that path — but a reader cannot, so it
was renamed before the move rather than after.

"Generator" is the user-facing name for this tool (the Objective / Test Case Generator in the
sidebar); "wizard" is the internal name for its HTTP router only.

Nothing here may import `routers.*`; the dependency runs one way only.
"""
