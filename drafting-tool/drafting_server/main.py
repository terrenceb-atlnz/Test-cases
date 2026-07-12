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
from routers.wizard import router as wizard_router

app = FastAPI(title="Objective Drafting Tool (Server-Backed)")

# Serve the migrated frontend using absolute path relative to this file
static_dir = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.state.app_data = None

@app.on_event("startup")
async def startup_event():
    print("Loading data for server-backed drafting tool...")
    app.state.app_data = load_all_data()
    print("Data ready.")

app.include_router(wizard_router, prefix="/api/wizard")


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
    process_path = os.path.join(BASE_DIR, "..", "..", "OBJECTIVE_DRAFTING_PROCESS.md")
    content = "# OBJECTIVE_DRAFTING_PROCESS\n\nFull markdown content could not be loaded."
    if os.path.exists(process_path):
        try:
            with open(process_path, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            pass

    # Simple markdown-to-HTML for headings, lists, links (no extra deps)
    html = content
    html = re.sub(r'^# (.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2 id="\1">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: '<ul>' + m.group(0) + '</ul>', html)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
    html = html.replace('\n\n', '<p></p>').replace('\n', '<br />')

    # Add wizard deep link anchors and note
    html = html.replace('Step 1', '<a href="/#step-1">Step 1</a>')
    html = html.replace('Step 2', '<a href="/#step-2">Step 2</a>')
    html = html.replace('Step 3', '<a href="/#step-3">Step 3</a>')
    html = html.replace('Step 4', '<a href="/#step-4">Step 4 (Synthesis)</a>')

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
        <a href="#Step 1">Step 1</a> |
        <a href="#Step 2">Step 2</a> |
        <a href="#Step 3">Step 3</a> |
        <a href="#Step 4">Step 4 (Synthesis)</a>
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
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("drafting_tool.drafting_server.main:app", host="0.0.0.0", port=8000, reload=True)