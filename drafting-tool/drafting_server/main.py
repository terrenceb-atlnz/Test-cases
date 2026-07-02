#!/usr/bin/env python3
"""
Server-backed Objective Drafting Tool.

FastAPI backend for:
- Serving the interactive OBJECTIVE_DRAFTING_PROCESS as a web page
- Enforcing repeatable step-by-step process with user review gates
- LLM-driven synthesis of Objectives and Steps (using templated prompts)
- Producing repeatable standardized outputs (traceability.md + zephyr_payload.json)

Run with (from project root):
  python -m uvicorn drafting_tool.drafting_server.main:app --host 0.0.0.0 --port 8000

Or cd into drafting-tool/drafting_server and adjust.
Behind nginx (copy nginx.conf.example to appropriate location).

This replaces the old single-file static approach.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
import sys

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

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main wizard UI (migrated from v1)."""
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    with open(index_path) as f:
        return HTMLResponse(f.read())

@app.get("/process", response_class=HTMLResponse)
async def process_page():
    """The OBJECTIVE_DRAFTING_PROCESS as a web-based page."""
    # For now serve a simple page; in full render the md with sections + wizard links
    return HTMLResponse("""
    <h1>OBJECTIVE_DRAFTING_PROCESS</h1>
    <p>This is the live web-based reference for the repeatable process.</p>
    <ul>
      <li>Step 1: Review TestLink + Decisions (user confirm pause)</li>
      <li>Step 2: Zephyr Cross-Reference</li>
      <li>Step 3: ATPyLib + Gaps</li>
      <li><strong>Synthesis of Objectives & Steps happens LAST using LLM + templates</strong></li>
    </ul>
    <p><a href="/">Back to Wizard</a></p>
    <pre>Full content of OBJECTIVE_DRAFTING_PROCESS.md would be rendered here with interactive links.</pre>
    """)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("drafting_tool.drafting_server.main:app", host="0.0.0.0", port=8000, reload=True)