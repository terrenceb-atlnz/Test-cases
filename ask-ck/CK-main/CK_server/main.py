#!/usr/bin/env python3
"""
Server-backed Objective Drafting Tool.

FastAPI backend for:
- Serving the interactive OBJECTIVE_DRAFTING_PROCESS as a web page
- Enforcing repeatable step-by-step process with user review gates
- LLM-driven synthesis of Objectives and Steps (using templated prompts)
- Producing repeatable standardized outputs (traceability.md + zephyr_payload.json)

Run with the helper script (recommended):

  ./drafting-tool/run.sh

  # Examples
  PORT=9000 ./ask-ck/CK-main/run.sh

Or manually from ask-ck/CK-main:
  python3 -m uvicorn CK_server.main:app --host 127.0.0.1 --port 8000 --reload

The LLM backend is chosen on the Configure page and is limited to an approved set
(models.SUPPORTED_AUTH_METHODS). There is no environment-key fallback.

The server binds LOOPBACK by default: it has no authentication, and push_to_zephyr can
spend the server's own JIRA_KEY against live cases. Exposing it on the network is a
deliberate opt-in (HOST=0.0.0.0 ./ask-ck/CK-main/run.sh) — see the note in run.sh.
Behind nginx (copy nginx.conf.example to appropriate location).

Note: MOCK/demo removed. Use real credentials or local CLI logins (grok login --oauth / claude /login).

This replaces the old single-file static approach.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import os
import sys
import re
import threading
import time
import hashlib

# Ensure we can import sibling modules when run from project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Logging setup. The routers use `logging.getLogger(__name__)`; without this call the
# root logger sits at WARNING, so every log.info() would be silently DROPPED — including
# the "[export] Saved drop-in bundle to …" line an operator relies on. These messages
# went to stdout as bare print() before, so configuring INFO here is what preserves
# today's visibility rather than adding noise. Level is overridable for quiet runs.
#
# force=True because uvicorn installs its own handlers on the root logger when it starts;
# without it, whichever ran first wins and the format silently depends on launch order.
logging.basicConfig(
    level=os.environ.get("CK_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    force=True,
)

log = logging.getLogger(__name__)

from data import load_all_data
from paths import DB_PATH as PERMANENT_DB_PATH, PROCESS_MD
from session_store import SessionWriteError
from locks import LockError
from routers.wizard import router as wizard_router
from routers.zephyr_tool import router as zephyr_tool_router
from routers.test_composer import router as test_composer_router
from routers.pytest_create import router as pytest_create_router
from routers.agent_bridge import router as agent_bridge_router
from routers.llm_debug import router as llm_debug_router
from routers.admin import router as admin_router
from routers.locks import router as locks_router
import llm as _llm

app = FastAPI(title="Ask CK (Server-Backed)")

# CORS lockdown (adversarial-review finding: no CORS meant any origin could drive the
# /api/agent/* broker + other endpoints from a victim's browser on a shared deployment).
# The app serves its own frontend SAME-ORIGIN, so cross-origin browser access is not needed
# by design. Default to a restrictive localhost allowlist; a named deployment can widen it
# via CK_ALLOWED_ORIGINS (comma-separated), mirroring the ck-agent's CK_AGENT_ORIGIN pattern.
_default_origins = [
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost", "http://127.0.0.1",
]
_env_origins = [o.strip() for o in os.environ.get("CK_ALLOWED_ORIGINS", "").split(",") if o.strip()]
_allowed_origins = _env_origins or _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,            # no cookies/credentials are used cross-origin
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(SessionWriteError)
async def _session_write_failed(request: Request, exc: SessionWriteError):
    """A session write that never reached ck.db must fail the request, not return 200.

    session_store.persist_session used to log the failure and carry on, so a handler
    answered 200 while the user's confirmed selections or synthesized objective were
    gone — and nothing in the response said so. pytest_create._pt_persist had the same
    shape and was already changed to raise, because silently losing work is what made
    "never trust the 200" a documented workaround.

    Handled here rather than in session_store so that module stays framework-free (see
    its SessionWriteError docstring), and here rather than at each call site so none of
    them can forget. The exception's own message is the body — it already names the case
    and says the work was not saved.
    """
    log.error("session write failed on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(LockError)
async def _lock_conflict(request: Request, exc: LockError):
    """A per-case lock conflict (another editor holds the case) or a stale optimistic
    write (rev CAS mismatch) is a 409, not a 500: the request was well-formed and the
    server is fine — the write was deliberately refused to protect another editor's
    work. The exception's own message names the case and says what to do, so it is the
    body. Handled app-wide (like SessionWriteError) so no persist call site can forget.
    See PLAN-auth-and-case-locking.md Phase 1 and locks.py.
    """
    log.info("lock conflict on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.middleware("http")
async def _bind_session_id(request: Request, call_next):
    """Expose per-request browser context to the LLM layer via ContextVars:
    X-CK-Session (claude_agent routing + debug-log keying), X-CK-Panel and the
    request path (LLM debug-log attribution — see llm_debug.record).

    Set per request; never persisted. Empty for non-browser callers.
    ContextVars propagate into run_in_threadpool — the same mechanism
    current_session_id already relies on.
    """
    token = _llm.current_session_id.set(request.headers.get("X-CK-Session", ""))
    panel_token = _llm.current_panel_id.set(request.headers.get("X-CK-Panel", ""))
    path_token = _llm.current_request_path.set(request.url.path)
    # X-CK-LLM-Call: per-call id for live progress + true cancel (llm_inflight).
    call_token = _llm.current_llm_call_id.set(request.headers.get("X-CK-LLM-Call", ""))
    try:
        response = await call_next(request)
    finally:
        _llm.current_session_id.reset(token)
        _llm.current_panel_id.reset(panel_token)
        _llm.current_request_path.reset(path_token)
        _llm.current_llm_call_id.reset(call_token)
    # Force revalidation of ES modules. The entry main.js is cache-busted with
    # ?v=N, but its imports (llm.js, nav.js, …) are bare specifiers with no
    # query, so a stale cached child module can shadow a freshly-shipped one
    # (symptom: new UI logic silently absent after a code change). StaticFiles
    # sends an ETag but no Cache-Control, so browsers may skip revalidation;
    # no-cache makes them revalidate every load (ETag => 304 when unchanged, so
    # this is cheap). See static/js/README.md convention #4.
    if request.url.path.startswith("/static/js/"):
        response.headers["Cache-Control"] = "no-cache"
    return response

# Serve the migrated frontend using absolute path relative to this file
static_dir = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.state.app_data = None

@app.on_event("startup")
async def startup_event():
    print("Loading data for server-backed drafting tool...")
    # Strict DB-only: ck.db is the single runtime source of truth — there is no
    # JSON fallback to silently diverge to. If it is missing/empty, fail fast with
    # a clear, actionable message instead of booting into a broken half-state.
    import db
    chk = db.startup_check()
    if not chk.get("ok"):
        raise RuntimeError(
            f"ck.db is not ready ({chk.get('error') or 'empty / no corpora'}) at "
            f"{chk.get('db_path')}. The server reads all corpora from this database "
            f"and has no JSON fallback. Build it first:\n"
            f"    python3 tool/build_db.py --fresh --verify\n"
            f"then (for semantic search)  python3 tool/build_db.py --embed")
    app.state.app_data = load_all_data()
    print("Data ready.")

    # Warm the sentence-transformer in the BACKGROUND so the first hybrid search does
    # not pay the cold load (measured 16.2s from disk; ~20ms per encode once warm).
    # The searches themselves now run via run_in_threadpool, so a cold load no longer
    # blocks the event loop — but it still stalls whoever typed first. Warming on a
    # daemon thread keeps boot fast (important for --reload and the E2E webServer) and
    # costs nothing if the user never searches. Opt out with CK_NO_EMBED_WARMUP=1.
    if db.HAS_VEC and os.getenv("CK_NO_EMBED_WARMUP") != "1":
        def _warm():
            try:
                t0 = time.perf_counter()
                db._get_model()
                print(f"Embedding model warm ({time.perf_counter() - t0:.1f}s).")
            except Exception as e:
                # Never fatal: hybrid search degrades to keyword, and the lazy load
                # still runs on first use if this failed for a transient reason.
                print(f"Warning: embedding-model warmup failed ({e}); "
                      f"first semantic search will load it inline.")
        # context-free: runs at app startup, so there is no request context to inherit and
        # nothing it touches is lock-guarded. Every OTHER background thread must carry the
        # caller's contextvars.Context — see pt_exec.RunManager.start and Phase 11.0.
        threading.Thread(target=_warm, name="embed-warmup", daemon=True).start()

app.include_router(wizard_router, prefix="/api/wizard")
app.include_router(zephyr_tool_router, prefix="/api/zephyr-tool")
app.include_router(test_composer_router, prefix="/api/test-composer")
app.include_router(pytest_create_router, prefix="/api/pytest-create")
app.include_router(agent_bridge_router, prefix="/api/agent")
app.include_router(llm_debug_router, prefix="/api/llm")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(locks_router, prefix="/api/locks")


@app.get("/favicon.ico")
@app.get("/favicon.svg")
async def favicon():
    """Browsers always request /favicon.ico; serve a small SVG to avoid 404 noise."""
    path = os.path.join(static_dir, "favicon.svg")
    if os.path.exists(path):
        return FileResponse(path, media_type="image/svg+xml")
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main wizard UI (migrated from v1)."""
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    with open(index_path) as f:
        return HTMLResponse(f.read())

@app.get("/process", response_class=HTMLResponse)
async def process_page():
    """The OBJECTIVE_DRAFTING_PROCESS as a web-based page.
    Basic server-rendered version with headings and step anchors for deep links.
    Cross-references PLAN-server-backed.md (function 1) and PROGRESS.md (process reference priority).
    """
    process_path = str(PROCESS_MD)
    content = "# OBJECTIVE_DRAFTING_PROCESS\n\nFull markdown content could not be loaded."
    if os.path.exists(process_path):
        try:
            with open(process_path, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            pass

    def _base_slug(text: str) -> str:
        """URL-safe heading base (lowercase, spaces→-, drop punctuation)."""
        s = text.strip().lower()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'\s+', '-', s)
        return s.strip('-')

    # GitHub-style *unique* heading ids: a slug repeated in the doc gets -1, -2, … so no two
    # <h2> share an id (the source doc repeats "## Zephyr Cross-References (Step 3)" verbatim).
    # A single shared counter is walked in document order and consumed by BOTH the h2-id pass
    # and the nav-slug discovery, so the nav always links to the id its heading actually gets.
    _slug_counts: dict = {}
    def _unique_slug(text: str) -> str:
        base = _base_slug(text)
        n = _slug_counts.get(base, 0)
        _slug_counts[base] = n + 1
        return base if n == 0 else f"{base}-{n}"

    # Discover the doc's own process-step headings ("## Step N: …") BEFORE HTML-escaping/replacing,
    # so the in-page nav links to real heading anchors that exist on THIS page — not to wizard
    # panels (which have no hash routing) and not by fragile full-heading-text ids. These are the
    # *process* steps (Objective / testScript / Zephyr / ATPyLib), a different numbering from the
    # UI's display-only Generator step labels — so we never conflate the two.
    #
    # Walk ALL h2 headings in document order through the SAME _unique_slug counter used by the
    # h2-id pass below (also document order), capturing the slug assigned to each "Step N:" head.
    # This guarantees nav slug == heading id even after de-duplication.
    step_headings = []  # [(label, slug)]
    _nav_counts: dict = {}
    def _nav_slug(text: str) -> str:
        base = _base_slug(text)
        n = _nav_counts.get(base, 0)
        _nav_counts[base] = n + 1
        return base if n == 0 else f"{base}-{n}"
    for m in re.finditer(r'^##\s+(.*)$', content, flags=re.MULTILINE):
        heading = m.group(1).strip()
        slug = _nav_slug(heading)
        if re.match(r'^Step\s+\d+:', heading):
            step_headings.append((heading, slug))

    # Simple markdown-to-HTML for headings, lists, links (no extra deps)
    html = content
    html = re.sub(r'^# (.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', lambda m: f'<h2 id="{_unique_slug(m.group(1))}">{m.group(1)}</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', html)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
    html = html.replace('\n\n', '<p></p>').replace('\n', '<br />')

    # Build the top nav from the headings actually present in the doc (label + real in-page anchor).
    if step_headings:
        nav_step_links = ' |\n        '.join(
            f'<a href="#{slug}">{label.split(":")[0].strip()}</a>' for label, slug in step_headings
        )
    else:
        nav_step_links = ''

    page = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>OBJECTIVE_DRAFTING_PROCESS - Drafting Tool</title>
      <style>
        body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 1rem; line-height: 1.5; }}
        h1, h2, h3 {{ color: #1f2937; }}
        ul {{ margin-left: 1.5rem; }}
        pre, code {{ background: #f3f4f6; padding: 0.2rem 0.4rem; }}
        .nav {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #e5e7eb; }}
      </style>
    </head>
    <body>
      <div class="nav">
        <a href="/">← Back to Wizard</a> |
        {nav_step_links}
      </div>
      <div>{html}</div>
      <p style="margin-top:2rem; font-size:0.9em; color:#6b7280;">
        This is a server-rendered reference. Use the wizard for the repeatable gated workflow with LLM synthesis.
        See <a href="https://wiki.atlnz.lc/awpwiki/index.php">wiki</a> for full context.
      </p>
    </body>
    </html>
    """
    return HTMLResponse(page)

# --- Frontend build identity (stale-tab guard) -------------------------------
# Hashed from the static tree ON DISK — deliberately not a startup constant and
# not the git SHA, because neither would move in the cases that actually strand
# a tab. Static assets are served straight off disk, so an edit is live with NO
# restart (md5 of the file equals md5 of the served bytes while the process
# keeps running), and an UNCOMMITTED edit leaves the SHA untouched. mtime+size
# over the ~24 static files notices a changed asset without reading any of them.
#
# Cached for a few seconds: every open tab polls this, so an unguarded version
# would turn a room full of browsers into a stat storm on every tick.
_BUILD_TTL_S = 5.0
_build_cache = {"stamp": "", "at": 0.0}
_build_lock = threading.Lock()


def _static_build_id() -> str:
    """sha256 (truncated) over each static file's path, mtime_ns and size."""
    now = time.monotonic()
    with _build_lock:
        if _build_cache["stamp"] and (now - _build_cache["at"]) < _BUILD_TTL_S:
            return _build_cache["stamp"]
    parts = []
    for root, _dirs, files in os.walk(static_dir):
        for name in files:
            fp = os.path.join(root, name)
            try:
                st = os.stat(fp)
            except OSError:
                continue  # vanished mid-walk; a later tick will see the tree settle
            parts.append(f"{os.path.relpath(fp, static_dir)}:{st.st_mtime_ns}:{st.st_size}")
    stamp = hashlib.sha256("\n".join(sorted(parts)).encode()).hexdigest()[:16]
    with _build_lock:
        _build_cache["stamp"] = stamp
        _build_cache["at"] = now
    return stamp


@app.get("/api/version")
async def api_version():
    """Identity of the frontend this server is serving right now.

    The browser records it at load and re-checks periodically; a change means
    that tab is running superseded modules and should reload. Touches neither
    the DB nor the LLM — every open tab polls it.
    """
    return {"build": _static_build_id()}


@app.get("/health")
async def health():
    import db
    chk = db.startup_check()
    return {
        "status": "ok",
        "db": {
            "ready": chk.get("ok", False),
            # WHICH database this server is on, and whether it is the permanent one.
            # ask-ck/var/ck.db is meant to be written when a person operates the app (a
            # case load persists a session); a server being DRIVEN BY TESTS must not touch
            # it, and runs against a throwaway copy via CK_DB_PATH (see
            # tool/run_scratch_server.sh). Until this was reported, the only way to tell
            # the two apart was to read the process environment.
            "db_path": chk.get("db_path"),
            "is_permanent_db": chk.get("db_path") == str(PERMANENT_DB_PATH),
            "counts": chk.get("counts", {}),
            "vector_search": chk.get("vector_search", False),   # live: extension loaded AND vectors exist
            "sqlite_vec_loaded": chk.get("has_vec", False),
            "embeddings": chk.get("embeddings", 0),
            "embed_model": chk.get("embed_model"),
            "schema_version": chk.get("schema_version"),
            "built_at": chk.get("built_at"),
            "error": chk.get("error"),
        },
    }

if __name__ == "__main__":
    # Loopback by default — Ask-CK has no auth and push_to_zephyr can spend the server's
    # JIRA_KEY against live cases; see the note in run.sh. Override deliberately with
    # CK_HOST=0.0.0.0 (run.sh's HOST does the same for the normal launch path).
    # NOTE: the module path here was stale ("drafting_tool.drafting_server.main:app" has
    # not existed since the 2026-07-13 restructure), so this block could only ever have
    # raised on import. Corrected to the real app path.
    uvicorn.run("CK_server.main:app",
                host=os.getenv("CK_HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "8000")),
                reload=True)