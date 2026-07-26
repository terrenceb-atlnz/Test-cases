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
  LLM_API_KEY=sk-... ./drafting-tool/run.sh
  PORT=9000 ./drafting-tool/run.sh

Or manually from the project root:
  LLM_API_KEY=sk-... PYTHONPATH=drafting-tool python3 -m uvicorn drafting_server.main:app --host 0.0.0.0 --port 8000 --reload

Or cd into the server directory:
  cd drafting-tool/drafting_server
  LLM_API_KEY=sk-... PYTHONPATH=. python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Behind nginx (copy nginx.conf.example to appropriate location).

Note: MOCK/demo removed. Use real credentials or local CLI logins (grok login --oauth / claude /login).

This replaces the old single-file static approach.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
import uvicorn
import os
import sys
import re

# Ensure we can import sibling modules when run from project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from data import load_all_data
from paths import PROCESS_MD
from routers.wizard import router as wizard_router
from routers.zephyr_tool import router as zephyr_tool_router
from routers.test_composer import router as test_composer_router
from routers.pytest_create import router as pytest_create_router
from routers.agent_bridge import router as agent_bridge_router
from routers.llm_debug import router as llm_debug_router
from routers.admin import router as admin_router
import llm as _llm

app = FastAPI(title="Ask CK (Server-Backed)")


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
    try:
        response = await call_next(request)
    finally:
        _llm.current_session_id.reset(token)
        _llm.current_panel_id.reset(panel_token)
        _llm.current_request_path.reset(path_token)
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

app.include_router(wizard_router, prefix="/api/wizard")
app.include_router(zephyr_tool_router, prefix="/api/zephyr-tool")
app.include_router(test_composer_router, prefix="/api/test-composer")
app.include_router(pytest_create_router, prefix="/api/pytest-create")
app.include_router(agent_bridge_router, prefix="/api/agent")
app.include_router(llm_debug_router, prefix="/api/llm")
app.include_router(admin_router, prefix="/api/admin")


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

@app.get("/health")
async def health():
    import db
    chk = db.startup_check()
    return {
        "status": "ok",
        "db": {
            "ready": chk.get("ok", False),
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
    uvicorn.run("drafting_tool.drafting_server.main:app", host="0.0.0.0", port=8000, reload=True)