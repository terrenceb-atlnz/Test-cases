---
verified: 2026-10-07
---
# PLAN — Zephyr Templating Tool

> ## Status (read first)
>
> **ACTIVE — built through Phase 4 and applied to production 2026-10-06 06:07 (`fc308f8`); Phase 5's real
> upload is the open work.** Terrence's design is [`docs/zephyr.txt`](../../docs/zephyr.txt) — this plan
> carries it out and records the decisions made since; where the two differ, the decision log (§3)
> is newer. **Built: Phases 0a, 0b, 1 (by hand), 2, 3, 4 and the Upload dry run (2026-10-05).** `ask-ck/tools/zt_snapshot.py` reads the template
> set from Zephyr (GET only); `POST /api/zephyr-tool/templates/refresh` runs it and imports the result
> into ck.db's `zt_template_*` tables; `GET /api/zephyr-tool/templates` returns the tree. Applied to
> production and refreshed there on Terrence's "apply now and refresh" (14 plans / 15 cycles / 396
> cases / 416 links, captured 2026-10-05T01:14:27Z). Phase 2: `ask-ck/tools/zt_wiki.py` reads a
> project page and its TPS / Test Strategy / Feature Page (GET only; §4a) — a standalone tool, wired
> to the server with Phase 3. Phases 3–4 (§5a): `POST /api/zephyr-tool/analyse` + the one-page
> **Organize Templates** panel; API Upload is a dry-run call list (D9). The tool itself writes
> nothing to Zephyr or the wiki; the only Zephyr writes so far are the IE570 Port pair (§6) and the
> IE570 Factory Tests pair (§6a). **2026-10-07: every upload request is captured** (clone, move,
> remove-case — §6a) and the dry run now lists each with its real method, URL and body, all known.
> Next: the real upload's writes (not started — needs Terrence's go-ahead). Open questions: §8.

## 1. What the tool does (from `docs/zephyr.txt`)

A user pastes a project's wiki page URL (e.g. `Project:3296_IE520_Software`). The tool:

1. reads the three templated pages that page links to — the **Test Strategy**, the **Feature
   Page** (sometimes undeveloped) and the **TPS** — and fills **What Version** (AW+ version) and
   **What Product** (the DUT);
2. starts from **every** template plan, cycle and case selected, and has the LLM trim them,
   erring on the side of keeping a test, by answering:
   1. which test plans can be cut (Test Strategy);
   2. within kept plans, which cycles are not relevant (unsupported feature, incapable device);
   3. within kept cycles, which cases are not relevant (feature absent from the TPS or device);
   4. which remaining cases are not **Mandatory (M)** or **Supported "YES"** on first release per
      the TPS (§11.3 / §11.4);
   5. what any document names as a requirement that has **no** template (a gap report);
   6. **AI Notes** backing each deselection (features absent, stack member count, …);
3. shows one page: URL + **Organize with LLM**; Version + Product; then two scrollable columns —
   a read-only **Results Analysis**, and the Plan → Cycle → Case tree with checkboxes the user can
   override (unticking a parent unticks its children); **Confirm** un-greys **API Upload**;
4. **API Upload** clones the selected templates into the project's AW+ version location in Zephyr;
5. *later ("more to follow")*: links the result into the wiki page's Test Results section (the
   red-circled area of the project page template).

It replaces the four placeholder pages the 2026-07 facelift scaffolded
(`nav.js` `panel-zt-info|plan|link|tbd`) with **one** page.

## 2. What exists today

| piece | state |
|---|---|
| UI | four "under construction" panels; `routers/zephyr_tool.py` is a `/status` stub; `ask-ck/functions/zephyr-tool/` holds a README only |
| Zephyr access | `upload_refined.py` (the Generator's push): Bearer PAT from `JIRA_KEY` (env, else `secrets.md`), the public `/rest/atm/1.0` API and the UI's internal `/rest/tests/1.0` (trace links); shelled out to by `push_to_zephyr`, audited to `ask-ck/db/zephyr-push-audit.jsonl`, the server never holds the token |
| `ck.db` | all 45,427 Zephyr **cases** (`zephyr_cases`, with folder) — **no plans, no cycles** |
| wiki | `https://wiki.atlnz.lc/awpwiki/api.php` answers **without login** from this host (checked 2026-10-05: `action=parse&prop=links` on the IE520 project page lists `IE520 Software TPS`, `Test:3296 Test Strategy - IE520 Software`, `IE520 Software - Feature Page`) |

## 3. Decisions (Terrence, 2026-10-05)

- **D1 — the templates are authored in Zephyr by Terrence**: blank template plans and cycles, linked
  to the cases refined in Ask-CK. Plans in `/Platform Testing/Test Plan TEMPLATES`, cycles in
  `/Platform Testing/Test Cycle TEMPLATES`. Populated for now; *"they will likely be updated later."*
- **D2 — plans and cycles are CLONED; cases are SHARED** (corrected 2026-10-05, Terrence: *"D2 yes
  you can"*). A clone of a plan or cycle gets its own key and its Traceability tab links the original;
  a cloned cycle holds the **same case keys** as its template (measured, §6), so each case gathers
  executions from every project — that is what *"so the test cases retain their previous
  executions"* means. (Recorded first as "cases included", which the measurement contradicted.)
- **D3 — the template set is snapshotted through the API** (the UI exports cases only, not plans or
  cycles) **into a `ck.db` table** (*"ck.db table is a better idea"*). ck.db is written only by the
  server, so the snapshot tool prints JSON and a server-side import writes the table.
- **Deferred:** template item assignees (178 items carry one; a clone would inherit it) — *"we can
  worry about assignments later."*
- **D4 — a `-` in the TPS feature tables means "not supported or N/A"** (Terrence, 2026-10-05). §11.3's
  ranking is `M` or `-`, so only `M` counts as supported. *Correction found while building Phase 2:* in
  §11.4 the `-` is in the **Priority** column, not Supported, which is only `YES`/`NO`; there, the
  Supported column decides. One row has Priority `-` but Supported `YES` (Switching / Port Security /
  Dynamic Port Security): **the Supported column decides** (Terrence, 2026-10-05).
- **D5 — the target folder is created by the USER before an upload**; the tool finds it, never
  creates it. It is looked up from the version on the project page and the middle level the Test
  Strategy names (§6.2 "Test Cases": *"stored in Jira under 5.5.6-2 ---> Tomahawk ---> IE570"*).
  IE520 itself sits in an old location (the project slipped several releases) — not a case the tool
  has to handle.
- **D6 — an unwritten Feature Page is reported as "not written"**, not fed to the model (Terrence:
  *"i like your solution"*).
- **D7 — the wiki write-back is one edit** (confirmed by Terrence): the project page's red-circled
  Test Results box is `{{Test Status v2|<version>|<project>}}`, which transcludes
  `Test:<version>/<project>/Status`; that page ends in `{{ATMSummary|<plan keys>|both|detailed}}`,
  and the wiki draws the results from that list of Zephyr plan keys. Writing back = putting the
  cloned plan keys into that list.
- **D9 — API Upload is a DRY-RUN list in the first page build** (Terrence, 2026-10-05): after Confirm it
  shows the exact calls it would make — clone, move, unlink, rename, verify — per plan and cycle, and
  writes nothing. The clone and move call bodies were never captured (only unlink and rename, §6);
  real writes follow once Terrence captures one plan clone and one cycle clone in the Network tab.
  *Captured 2026-10-07* — clone, move and remove-case (§6a); the dry run lists them all as known.
- **D10 — Q4 UNTICKS with an AI Note** citing the TPS row (e.g. "TPS §11.4 Continuous POE (HANP):
  NO"); the user can re-tick. "Maybe" stays ticked (D8).
- **D11 — Q5, the gap report, is in the first build, report-only** — a read-only "Gaps" list that
  changes no ticks.
- **D12 — the live wiki read is an accepted exception** to "the server reads corpora only from ck.db"
  (§8.5): the wiki is per-project INPUT, not a corpus; the server runs `zt_wiki.py` as a read-only
  subprocess, as the template refresh runs `zt_snapshot.py`.

## 4. The template set (snapshot 2026-10-05, `zt_snapshot.py`)

**14 plans → 15 cycles → 396 cases**, each plan linking one cycle except Bootloader (two):

| plan | cycle(s) | cases |
|---|---|---|
| P3248 Port | C8451 | 7 |
| P3249 Sanity Checks | C8452 | 25 |
| P3250 Switching | C8453 | 75 |
| P3251 QoS | C8454 | 22 |
| P3252 Management | C8455 | 71 |
| P3253 IPv4 | C8456 | 44 |
| P3254 IPv6 | C8457 | 35 |
| P3255 Factory Tests | C8458 | 10 |
| P3256 Bootloader Tests | C8459 (Manual) / C8465 (Automated) | 17 / **0** |
| P3257 Authentication and Security | C8460 | 42 |
| P3258 Advanced Management | C8464 | 19 |
| P3259 Stack Tests | C8461 | 14 |
| P3260 Industrial Features | C8463 | 12 |
| P3261 Data Center Features | C8462 | 8 |

Observations: 5 cases sit in more than one cycle (harmless now cases are shared — D2); the cases come from several folders, not only `New Platform Template` (e.g.
`/Environmental Monitoring` 18, `/Modbus/Proj 2166 Modbus Support` 6, 3 with no folder — Terrence:
several cases outside the template folder still need creating or updating; *"for now, it'll do"*); 357 cases
are at version 1.0 and 39 at 2.0 (the refined ones); 178 items have an assignee (deferred); 17 case
names contain a double space (cosmetic — the whitespace check may be narrowed to plans and cycles).
Plans and cycles are re-snapshotted whenever the templates change; discovery is by folder, so new
families need no code change.

## 4a. The wiki pages (read 2026-10-05, IE520, `api.php` without login)

| page | found by | what the tool takes |
|---|---|---|
| project page (`Project:3296 IE520 Software`) | the URL the user pastes | **version** from `[[5.5.6-2 Release\|…]]` / `{{Test Status v2\|5.5.6-2\|3296}}` / `[[Category:5.5.6-2]]`; **product** from the remaining category (`IE520`); project number; the three links below |
| **TPS** `IE520 Software TPS` (73 sections, ~122 k chars) | the project page's rendered links (`prop=links`) — the `{{#switch: hw\|gui\|…}}` picks TPS or TFS, so the rendered link, not the wikitext, is read | §11.3 *Supported features (Ref. SID)*: 738 rows, ranking `M` 605 / `-` 133 · §11.4 *Supported features (Ref. PRD)*: 260 rows, Supported `YES` 232 / `NO` 28, Priority `1`/`2`/`3`/`-` (D4) · §6.1.4 features not implemented · §11.6 items in PRD not supported |
| **Test Strategy** `Test:3296 Test Strategy - IE520 Software` | rendered link, `Test:` namespace | §3.3 Feature Coverage, §4 Not Tested (IE520's just points at TPS §11.4), §6.2 Test Cases (the target path, D5) |
| **Feature Page** `IE520 Software - Feature Page` | rendered link | written / not written per section — a section still equal to `Template:FeatureDocumentation/Preload` (all `{{TODO\|…}}`) is not written (D6); IE520's is wholly unwritten |

**Two TPS layouts (found 2026-10-05 on IE570).** The older one (IE570, `Project:3001 IE570 Platform
Support`) has no SID section: under §11.3 *Supported features (Ref. PRD …)* sit "PRD Software
Requirements - Part 1/2" (SID-shaped, 26 + 504 rows, ranking `M`/`D`/`O` **plus a "1st Release"
column** Yes/No/Maybe) and "Part 3" (PRD-shaped, 296 rows, Yes/No/Maybe/N/A), then a licence table;
and §11.4.4 *Features Supported and Tested* is filled (524 rows, all `Y` — IE520's is the empty
stub). So the reader recognises each table by its **columns** — SID-style (Ranking + Feature Group),
PRD-style (Item + Specification + Supported), tested (Feature Group + "Features Supported") — under
every "Supported features…" / "Features Supported and Tested" section and its subsections, and tags
each row with its section. Reading rules: Yes/Y supported; No/N/N-A/`-` not (D4); where a row has a
Supported or "1st Release" column, that column decides (§8.11's ruling, extended to "1st Release");
anything else — "Maybe" (6 IE570 rows), a bare `D`/`O` ranking — is **left undecided** (`None`) and
counted in `problems`, never guessed.

- **D8 — an undecided ("Maybe") feature keeps its tests selected, with an AI Note citing the TPS
  comment** (Terrence, 2026-10-05 — the design's "err on the side of keeping a test"). The TPS does
  not define "Maybe"; its comments show it means *not committed, depends on something outside the
  project*: IE570's 6 rows are 3 features — PROFInet IO ("Dependent on IE360, IE560 support"),
  MACsec VLAN tag in clear ("Dependent on {{MRSt|1513}}"), gNMI ("Not in AW+, But is possible
  gNXI"). A Phase 3 rule; the reader already passes them on as `supported: None`.
- The same feature can appear in more than one PRD part (MACsec is in all three) — Phase 3 treats
  repeats as one feature.

Sections are found by **title**, not number (a TPS revision can renumber them). IE520's Strategy
shows why the reader reports, never decides: its §6.2 says `5.5.6-2 ---> Tomahawk ---> IE570` (a
typo for IE520) and its Schedule says 5.5.6-1.

## 5. Phases

| phase | what | touches | state |
|---|---|---|---|
| **0a** | read-only snapshot tool: plans, cycles, cases by folder, plus `problems` | Zephyr GETs | **DONE** 2026-10-05 |
| **0b** | `ck.db` tables + server import (runs the tool, imports its JSON in one transaction) + a read endpoint for the tree | server code, `ck.db` schema → **production restart** | **DONE** 2026-10-05 (applied; the reload wedged and the unit was restarted — ~4½ min down) |
| **1** | map the CLONE API and its side effects, in a sandbox: clone one plan, one cycle, one case; record exactly which links appear on the clone and on the original; design the cheapest **clone → prune → verify** sequence (or a clone that never creates the stray link) | Zephyr **writes** — each one asked first | needs a sandbox (§8) |
| **2** | wiki reader: project page → its three links by the templated names → page text (wikitext via `api.php`), TPS §11.3/11.4 tables, version + product, the Strategy's target path, Feature Page written / not written (§4a) | wiki GETs | **DONE** 2026-10-05 — `ask-ck/tools/zt_wiki.py`, not yet wired to the server |
| **1** *(done by hand)* | the clone side effects measured on IE570 (§6) — Terrence cloned, Claude unlinked and renamed | Zephyr writes, each asked | **DONE** 2026-10-05 |
| **3** | analysis: Q1–Q5 + AI Notes over the snapshot tree (§5a) | the per-seat LLM | **BUILT** 2026-10-05 (`zt_analysis.py`, 2 prompts, `/analyse`) |
| **4** | the single page (§5a) | front end | **BUILT** 2026-10-05 (`current/zephyr-tool/`, both index pages) |
| **5** | API Upload: **dry-run list first (D9)**; then an audit record written before the first write (the `push_to_zephyr` pattern), clone → move → unlink → rename → verify | Zephyr writes | dry run **BUILT** (`zt_upload.py`, `/upload/preview`); every request **CAPTURED** 2026-10-07 (§6a) and in the dry run; the writes are not built |
| later | wiki write-back: put the cloned plan keys into `{{ATMSummary|…}}` on `Test:<version>/<project>/Status` (D7) | one wiki write | not built |

**The analysis guardrail (Phase 3):** the model may only PROPOSE deselections, each with a reason
that cites a source document; every template item it does not mention stays selected. So a model
that drops items from its answer cannot silently remove tests — it can only fail to remove them,
which is the cautious direction the design asks for.

**Scale of an upload (sized by Phase 1):** up to 14 plan + 15 cycle clones per project (cases are
shared, D2), and per family the two unlinks of §6 plus a re-read of both ends. Phase 1 looks for bulk endpoints (the internal API has `…/bulk/…` routes, e.g. the
trace-link create `upload_refined.py` already uses). *Found 2026-10-07 (§6a):* both clones take a
`sourceIdList` and both moves take a list, so one request can clone or move many; only one-item
lists have been seen working.

## 5a. Phases 3–4 design (2026-10-05)

**One request, then polling** (the browser connection ceiling): `POST /api/zephyr-tool/analyse {url}`
starts a job and returns its id; `GET /analyse/{id}` reports it; `POST /analyse/{id}/cancel` stops
work not yet started. The job:

1. **reads the wiki** — runs `zt_wiki.py <url>` (D12) → version, product, pages, TPS feature rows,
   Strategy, Feature Page, `problems`;
2. **one model call per template plan (Q1–Q4)**, a few at a time — the plan's cycles and cases, the
   Strategy text, the TPS device sections, and only the TPS rows that are **not supported** (No /
   `-` / N/A) or **undecided** ("Maybe"); the model PROPOSES deselections, each with a question
   (Q1 plan, Q2 cycle, Q3/Q4 case), a reason and a cited source, plus AI Notes;
3. **one model call for Q5 + project AI Notes** — the supported TPS rows against the template
   names → `gaps` (report-only, D11) and notes such as stack size and absent hardware.

**The guardrail, enforced by the server:** a proposal must name a key in that plan's tree and carry
a reason and a source, or it is dropped (and counted); everything not proposed stays ticked; a
"Maybe" feature is never a deselection (D8); a failed plan call leaves that plan fully ticked and
says so.

**The page** (`docs/zephyr.txt` UI): one panel replacing the four placeholders — URL + **Organize with
LLM**; **What Version** / **What Product** (filled from the read, editable; the version comes from
the Strategy's target path when it has one, since that is where the tests go — the project page's
own version is shown beside it when they differ); two scrolling columns — **Results Analysis**
(read-only: Q1–Q5 and 6. AI Notes, plus the read's problems) and the **Plan → Cycle → Case tree**
(checkboxes; unticking a parent unticks its children; ticking a child re-ticks its parents; each
AI-unticked row shows its reason); **Confirm** un-greys **API Upload**, which shows the dry-run list
(D9) from `POST /upload/preview` — `zt_upload.py --dry-run` (GET only: finds the target folders under
`/<version>/<middle>/` by the project number or product, reads the template ids).

**First real runs (2026-10-05, IE570, org vLLM `vllm-fast`, scratch server).** Run 1: 149 s, 12 of
14 plans answered, 9 untick proposals, 7 gaps; two plan replies (Switching 75 cases, Authentication
42) held no usable JSON; the model cut the whole Advanced Management plan (Q1) from four TPS rows;
and it cited Strategy sections as "TPS §3.3". Three fixes: every digest heading names its document
(`### Test Strategy §3.3 …`); a Q1 survives only with a Test Strategy source (docs/zephyr.txt: "refer
to test strategy for details"); a reply with no usable JSON is asked once more. Run 2: 152 s, **14 of
14 answered**, 20 untick proposals (Q2 ×1, Q3 ×4, Q4 ×15), each citing a real TPS row or section, 10
gaps, no mis-cited section. Open (§8.12): with Q1 barred, the model unticked Advanced Management's
ONLY cycle (Q2) on the same TPS rows — the plan is emptied anyway.

## 6. The clone side effect (from `docs/zephyr.txt`, to be measured in Phase 1)

After a clone, the NEW object keeps the original's associations, and the ORIGINAL gains an
association to the new one. The originals here are the templates, so each project clone would add a
link on the template; over many projects the templates collect links to every project cloned from
them. The new objects need their inherited associations pruned and the prune re-verified. Preferred:
a clone that never creates the association; acceptable: clone → cull → check. Phase 1 records the
exact before/after on both sides before anything is designed around it.

**Measured 2026-10-05** — Terrence cloned the Port pair by hand into IE570's folders
(`/5.5.6-2/Tomahawk/Project 3001: IE570`, plans and cycles) and the before/after was read through the
public API:

| step | new object | its links | side effect on the template |
|---|---|---|---|
| clone plan P3248 | **P3263** "Port (cloned)" | the **template** cycle C8451 (a plan clone does NOT clone its cycles) | none visible on P3248 |
| clone cycle C8451 | **C8466** "Port (cloned)" | joins **every plan the original was in**: P3263 *and the template plan P3248* | **P3248 now links C8466** — an IE570 cycle inside the template |

- The cycle clone holds the **same 7 case keys** as C8451 — cases are shared, not copied, and the
  assignees came with it (`nings`, `JIRAUSER17403`). IE570's own 25 cycles are clones of earlier
  cycles the same way (Terrence), which is how a case keeps its executions across projects.
- Names get ` (cloned)`; owner/creator = the cloner; status Draft / Not Executed.
- A link CREATED by a clone does not bump the template's `updatedOn`; a link DELETED does (below). The
  Traceability "cloned from" link is not in the public API's plan or cycle record.
- **A plan↔cycle link is ONE trace-link record**, seen from both ends under the same id:
  `GET /rest/tests/1.0/{testplan|testrun}/{numericId}?fields=id,key,traceLinks` (numeric id from
  `GET /rest/tests/1.0/{testplan|testrun}/{KEY}?fields=id,key`). The UI bundle also exposes
  `/testplan/bulk/clone` and `/testrun/bulk/clone` (Phase 5).
- **The prune for one family** is two unlinks: P3263 drops C8451, P3248 drops C8466. **Done
  2026-10-05** on Terrence's go-ahead: `DELETE /rest/tests/1.0/tracelink/169716` (P3248↔C8466) and
  `…/169714` (P3263↔C8451), each re-verified just before and both ends read after — 200, exactly those
  links gone; P3248↔C8451 (169684) and P3263↔C8466 (169718) kept. The templates' name, folder,
  status, cases and assignees are unchanged, **but their `updatedOn`/`updatedBy` moved** (P3248
  02:19:51Z, C8451 02:21:34Z, the token's account) — an upload will touch every template it clones
  from this way. `zt_snapshot`'s "cycle linked by a template plan but lives outside the template
  folder" check is what catches a missed prune on the template side.
- **Rename = a partial PUT:** `PUT /rest/tests/1.0/testrun|testplan/{numericId}` with
  `{"id": …, "name": "…", "projectId": 15310}` (+ header `jira-project-id: 15310`) changes the name and
  `updatedOn` only — fields not sent are kept, links untouched. Captured from Terrence's UI rename of
  C8466 (the body inferred from its 60-byte length, then verified by the before/after) and used for
  P3263. **Naming (Terrence):** `IE570: Port (Ask-CK)` — `<product>: <template name> (Ask-CK)`.
- **IE570 result, 2026-10-05:** P3263 "IE570: Port (Ask-CK)" → C8466 "IE570: Port (Ask-CK)" (7 shared
  cases) in `/5.5.6-2/Tomahawk/Project 3001: IE570`; templates P3248 → C8451 as before. Writes logged
  in the session: 2 trace-link DELETEs, 1 plan rename (Claude); the clones and the cycle rename
  (Terrence, in the UI).

## 6a. The upload requests (captured 2026-10-07, Factory Tests → IE570)

Terrence did each step in the UI with the Firefox Network tab open; Claude read both ends back
through the API after each (GET only). Pair: template P3255 (id 11608) → C8458 (id 54224, 10 cases);
targets `/5.5.6-2/Tomahawk/Project 3001: IE570` — plan folder **26670**, cycle folder **26674**
(the TEMPLATES folders are 27278 / 27280). Every request carries `jira-project-id: 15310` and
`Content-Type: application/json`, as the rename does (§6).

| step (UI) | request | body | reply |
|---|---|---|---|
| clone plan (Clone) | `POST /rest/tests/1.0/testplan/bulk/clone` | `{"projectId":15310,"sourceIdList":[11608]}` | 200 `[11632]` — the new plan's id |
| clone cycle (Clone → "Clone all test cases that match the criteria", all filters "All") | `POST /rest/tests/1.0/testrun/bulk/clone` | `{"projectId":15310,"sourceIdList":[54224],"tql":"testRun.projectId IN (15310)"}` | 200 `[54276]` |
| move plan (drag into the folder) | `PUT /rest/tests/1.0/testplan` | `[{"folderId":26670,"id":11632}]` | 200, no body |
| move cycle (drag into the folder) | `PUT /rest/tests/1.0/testrun/bulk/update` | `[{"folderId":26674,"id":54276}]` | 200, no body (`text/html`) |
| take a case out (cycle page: tick → Delete → **Save**; Delete alone sends nothing) | `PUT /rest/tests/1.0/testrunitem/bulk/save` | `{"testRunId":54276,"addedTestRunItems":[],"updatedTestRunItems":[],"updatedTestRunItemsIndexes":[{"id":997176,"index":0},…{"id":997192,"index":8}],"deletedTestRunItems":[{"id":997174}],"autoReorder":false}` | 200, no body |

Body lengths matched each request's Content-Length, so nothing was left out. The Save also sends
`PUT …/testrun/{id}` `{"id":…,"projectId":15310}` (no field changed) and a `POST
…/testcase/bulk/get` (a READ of the remaining cases); neither is part of the removal.

**What the captures showed.**
- *New objects land in the template's folder*, named `<name> (cloned)`; the move is a separate
  request, and plans and cycles move through different URLs. A folder is addressed by its numeric
  id, read from `GET …/project/15310/foldertree/{testplan|testrun}`.
- *A cycle holds its own ITEMS; each item points at a shared case.* The clone's items are new
  (997174…; the template's are 996076…), so removing one never touches the template. A removal
  names the ITEM id — read from `GET /rest/tests/1.0/testrun/{id}/testrunitems` (item id, index,
  case key). The UI also re-sends the order of the kept items; whether that part is required is
  untested, so the dry run sends it as the UI does.
- *A cycle clone joins EVERY plan its template cycle is in — archived ones too.* An earlier,
  deleted clone, **P3264** (created 20:59:37Z by Terrence, `archived: true`, still in the template
  folder), was linked to C8458 — and the new C8468 joined it as well. The UI's Delete only archives
  a plan, and an archived plan keeps its links. The public API answers 404 for an archived plan and
  the plan-side reads of P3255 / P3265 never show it: **only the cycle side
  (`GET …/testrun/{id}?fields=id,traceLinks`) does.** Those reads are slow — 26–32 s, and once over
  60 s (C8458) — so the upload's verify reads the cycle side with a long timeout.
- The clone leaves `updatedOn`/`updatedBy` empty; the first move stamps them.

**Writes this session.** Terrence (UI): the two clones, the two moves, T48185 out of C8468.
Claude (API, each on Terrence's go-ahead, each link re-read just before): `DELETE …/tracelink/169908`
(P3265↔C8458), `…/169910` (P3255↔C8468), `…/169912` (P3264↔C8468), `…/169906` (P3264↔C8458); the
renames of P3265 and C8468 (`PUT …/{id}`, §6). All 200.

**Result, read from both ends:** P3265 "IE570: Factory Tests (Ask-CK)" → C8468 "IE570: Factory
Tests (Ask-CK)" (9 cases, T48185 out) in the IE570 folders, link 169914 only; template P3255 →
C8458 (10 cases), link 169696 only, `updatedOn` 21:28Z (the unlinks); P3264 archived with no links.

## 7. Invariants this tool touches

- `ck.db` stays the server's only data source: the template tree is read from the `ck.db` table,
  never from a file at runtime; the table is written only by the server's import.
- **New live external dependencies:** the wiki (read) and Zephyr (read, and write on upload). The
  Generator's `push_to_zephyr` already writes to Zephyr as a deliberate, audited exception; whether
  this tool is treated the same way is Q6.
- The server never holds the Jira token: like `push_to_zephyr`, it runs a command-line tool that
  reads `JIRA_KEY` itself.

## 8. Open questions

1. ~~Go-ahead for Phase 0b~~ — given 2026-10-05.
2. ~~Target location~~ — answered: the user creates it; the tool finds it from the version and the
   Strategy's §6.2 path (D5). *Still to settle in Phase 5:* the exact Zephyr folder match (does the
   last level name the project, e.g. `Project 3296: IE520`?) and what the page shows when it is absent.
3. **Sandbox for Phase 1:** which Zephyr folder may test clones be written to, and who removes them?
4. **Credentials:** the shared `JIRA_KEY` in `secrets.md` (every clone attributed to its owner), or
   each user's own token?
5. ~~Invariant exception~~ — the live wiki READ is accepted (D12); Zephyr writes are decided with
   Phase 5's real upload.
6. ~~Q4~~ — answered: untick with an AI Note (D10). *(Background: §11.3 is the SID feature list ranked `M`/`-`, §11.4 the PRD list marked
   `YES`/`NO` with a Priority `1`/`2`/`3`/`-`; `-` = not supported or N/A — D4, §4a.)*
7. ~~Q5~~ — answered: in the first build, report-only (D11).
8. ~~Cases in two cycles (5)~~ — moot: cases are shared, not cloned (D2).
9. **C8465 Bootloader Tests (Automated) is empty** — intended (to be filled), or should the tool
   skip empty cycles?
10. ~~UTC label~~ — the status line and the page now say "UTC" (2026-10-05).
11. ~~§11.4 Priority `-` with Supported `YES`~~ — answered: **the Supported column decides**
    (Terrence, 2026-10-05; the reader's rule).
12. **A one-cycle plan emptied by Q2.** With a plan cut (Q1) restricted to the Test Strategy's word,
    the model unticked Advanced Management's only cycle (Q2) on four TPS rows (AMF-Controller,
    OpenFlow, gNMI, Wireless Manager) — the same outcome. Accept (the user re-ticks), or also hold a
    cycle that is its plan's only one to the Q1 rule?
13. **Skip unticked cases AT the cycle clone?** (2026-10-07) The cycle-clone dialog's criteria are
    sent as the body's `tql`. If TQL can exclude cases by key, a clone could leave unticked cases
    out and the remove-case save (§6a) would not be needed. Untested — testing it is another real
    clone.
14. **Archived clones on other templates.** C8458 carried a link to the archived P3264 (§6a); any
    template cycle with such a link pulls every future clone of it into that archived plan, and the
    plan-side reads `zt_snapshot` relies on would not show it. Whether any other template cycle has
    one has not been checked (GET only, ~30 s per cycle from the cycle side).
