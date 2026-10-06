---
verified: 2026-10-05
---
# Zephyr Templating Tool — function home

Page: **Zephyr Templating Tool → Organize Templates** (`current/zephyr-tool/zephyr-tool.js`). Backend:
`CK_server/routers/zephyr_tool.py` + `CK_server/zt_analysis.py` + prompts `zt_analyse_plan.jinja` /
`zt_gaps.jinja`. Tools: `ask-ck/tools/zt_snapshot.py` (templates → ck.db `zt_template_*`),
`zt_wiki.py` (the project's wiki pages), `zt_upload.py` (API Upload: `--dry-run` lists the calls, `--apply` makes them — PLAN §5b).
Plan: `ask-ck/plans/PLAN-zephyr-templating.md`; Terrence's design: `docs/zephyr.txt`. This directory holds the function's data, results and
docs when they exist, mirroring `../generator/` and `../pytest-creator/` (PLAN-restructure-2026-09-11).
