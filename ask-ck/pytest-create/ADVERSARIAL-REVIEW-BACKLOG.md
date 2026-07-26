# Ask-CK Adversarial Review — Findings Backlog

**Generated 2026-07-27c** from the paused full-review workflow (`askck-adversarial-review`, run `wf_f53aa173-a88`).
62 candidate findings across 14 risk domains; verification was ~50% complete when paused.
**The top critical/high cluster (6 fixes) was implemented + tested this session** — see the
session entry in PROGRESS.md. The items below are the REMAINING backlog for a later triage pass.

> Status legend: these are *candidate* findings. Some carry a majority-real verdict from the
> partial verification; others are unverified. **Verify each against live code before fixing** —
> the review's own gate refuted ~⅓ of candidates in the completed portion.

| Sev | Category | Location | Summary |
|-----|----------|----------|---------|
| ~~high~~ FIXED | authorization | `agent_bridge.py:38` | ✅ 2026-07-27d — deliver now enforces X-CK-Session job ownership; /next + /result bind to the header. |
| ~~high~~ FIXED | correctness | `llm.py:1347` | ✅ 2026-07-27e — routed through the hardened string-aware extract_json_block (single shared extractor). |
| ~~high~~ FIXED | correctness | `llm.py:1329` | ✅ 2026-07-27e — routed through the hardened string-aware extract_json_block (single shared extractor). |
| ~~high~~ FIXED | cors-missing | `main.py:56` | ✅ 2026-07-27d — CORSMiddleware added, locked to a localhost allowlist (CK_ALLOWED_ORIGINS to widen). |
| high | correctness | `pt_script_template.py.jinja:108` | Step action/verify text is embedded into single-quoted Python string literals sanitized only with replace("'",""), so an embedded newline or trailing backslash produces a SyntaxError-broken skeleton. |
| ~~high~~ FIXED | path-traversal | `pytest_create.py:1150` | ✅ 2026-07-27d — full library filename validated (basename + .py + _NAME_RX) before the path is built; resolved-dir check added. |
| high | correctness | `pytest_create.py:1097` | The lint placeholder-survival check misses the physical-step verification marker `if want in output:  # >>> replace with the real verification condition <<<`, so an unfilled tautological verdict passe |
| ~~high~~ FIXED | path-traversal | `wizard.py:2122` | ✅ 2026-07-27d — case_key validated against _CASE_KEY_RE at the top of export() (before any LLM/write); resolved-target-under-refined-cases check added. Also closes the `wizard.py:1936/1939` export-gate findings (a bogus/traversal key now 400s early). |
| high | state-machine | `wizard.py:1381` | Wizard confirm_step for steps 1-3 has no invalidation cascade, so re-confirming an earlier DB review with changed selections leaves step4 (objective) and step5 (testScript) still marked confirmed from |
| ~~medium~~ FIXED | authorization | `agent_bridge.py:18` | ✅ 2026-07-27d — /next now binds to the X-CK-Session header (query param is legacy fallback only). |
| medium | correctness | `db.py:816` | Hybrid RRF merge drops pinned keep_ids: _rrf_merge sorts all rows by fused score and truncates to limit, so a kept pool item that scores low can be silently removed — violating the 'keep_ids always re |
| medium | robustness | `db.py:821` | HAS_VEC only means 'extension loaded', not 'embeddings exist', so on a keyword-only-built DB every hybrid search needlessly loads and runs the sentence-transformer model before discarding an empty vec |
| medium | correctness | `llm.py:428` | The Anthropic (native) path never checks stop_reason, so a response truncated at the max_tokens cap (default 2000) is accepted as complete, unlike the OpenAI path which raises on finish_reason=length. |
| medium | robustness | `llm.py:425` | The Anthropic path has no empty-content guard: a response with no text blocks (e.g. only thinking blocks or an empty content array) returns content='' with error unset, unlike the OpenAI path. |
| ~~medium~~ FIXED | correctness | `llm.py:618` | ✅ 2026-07-27e — routed through the hardened string-aware extract_json_block (single shared extractor). |
| ~~medium~~ FIXED | correctness | `llm.py:1218` | ✅ 2026-07-27e — routed through the hardened string-aware extract_json_block (single shared extractor). |
| medium | correctness | `llm.py:941` | synthesize_steps drops the LLM's first verification step whenever its description merely contains the substring 'Traceability' or 'Note:', which can delete a legitimate step. |
| medium | missing-auth | `main.py:261` | The server binds 0.0.0.0 (all interfaces) with no authentication on push_to_zephyr, so any host on the LAN can trigger live Zephyr writes using the server-side token. |
| medium | host-key-verification | `pt_exec.py:281` | paramiko AutoAddPolicy disables SSH host-key verification for every connection, so a MITM on the testbox network can impersonate the testbox and capture the SSH session (and password, if auth=password |
| medium | correctness | `pytest_create.py:743` | `_restamp_provenance` mis-attributes a fragment's provenance tag to the wrong TestCase when a fragment's `maps_to` references a SETUP step number, because the orig->class remap only contains non-setup |
| medium | correctness | `pytest_create.py:765` | _restamp_provenance strips the entire leading run of main() comment lines matching _PROVENANCE_ECHO_RX (^\s*#.*\b(ART\|SVT\|legacy\|AI)\b, IGNORECASE), silently deleting legitimate first-line code com |
| medium | state-machine | `pytest_create.py:2068` | Interrupted testbox runs are only re-marked 'stale' inside load_case, not in run_status; after a server restart the polling endpoint keeps reporting the persisted status 'running' forever with active: |
| medium | robustness | `traceability.md.jinja:29` | The Zephyr cross-reference markdown link interpolates s.key/id_or_key into both the [label] and the (URL); a key containing ')', '[' , ']' or whitespace breaks the rendered markdown link, and title/ju |
| medium | state-machine | `wizard.py:1939` | export() falls back to the fully client-controlled req.session when the key is absent from both the in-memory cache and ck.db, and there is NO steps-1..3 gate on export — so a client can write a Compl |
| medium | state-machine | `wizard.py:1648` | The `sessions.get(key) or _load_persisted(key)` pattern can materialize two distinct WizardSession objects for one key; because every _persist_session is a full-object INSERT ... ON CONFLICT overwrite |
| medium | partial-write | `wizard.py:2125` | Export writes 3 files in a loop where zephyr_payload.json (the file that marks a case Complete) is written before the session.json; if a later write throws, the case is silently promoted to Complete w |
| low | input-validation | `agent_bridge.py:44` | deliver_result performs no size or type validation on body['content'] / body['usage'], so an oversized or malformed result is stored verbatim into the per-session debug log and result dict. |
| low | resource-leak | `agent_jobs.py:111` | AgentJobRegistry.gc() is defined but never invoked anywhere, so _queues and _session_seen grow without bound across the lifetime of the process. |
| low | robustness | `db.py:54` | The thread-local read-write WAL connection is safe today only because all db.* calls run on the event-loop thread; the design's stated safety (per-thread conns) does not actually prevent WAL write rac |
| low | robustness | `generator.js:480` | confirmStep fetches /api/wizard/confirm_step without a res.ok check and blindly assigns data.session to S.currentSession, so an error response clobbers the in-memory session with undefined and silentl |
| ~~low~~ FIXED | correctness | `llm.py:1013` | ✅ 2026-07-27e — routed through the hardened string-aware extract_json_block (single shared extractor). |
| low | robustness | `llm.py:494` | resp.iter_lines(decode_unicode=True) can split a multi-byte UTF-8 sequence across chunk boundaries, corrupting streamed content with replacement chars. |
| low | robustness | `provenance.js:75` | provRefresh fetches the dry-run provenance endpoint without checking res.ok, so an HTTP 400/500 error body is parsed as a normal response and silently rendered as '(empty)' instead of surfacing the er |
| low | correctness | `pt_generate_script.jinja:54` | The conditional Py2 rule tells the model that Py2 fragments are 'marked ⚠ PYTHON 2', but that marker is only emitted inside the skeleton (via _render_skeleton line 976), NOT in the 'Reviewer-approved  |
| low | prompt-injection | `pt_generate_script.jinja:10` | Corpus/case-derived free text (case_title, fragment.why, and — across sibling prompts — candidate titles/descriptions/summaries) is interpolated raw into instruction-bearing prompts, so a corpus recor |
| low | robustness | `pytest_create.py:765` | `_restamp_provenance` strips the first legitimate comment line inside a TestCase.main() whenever it merely mentions ART/SVT/legacy/AI, deleting a real documentation comment the model wrote. |
| low | robustness | `pytest_create.py:106` | `_translate_py2` cannot modernize any Py2 fragment whose extracted source is indented (starts at non-zero column), because lib2to3 requires module-level source and raises ParseError on leading indenta |
| low | data-integrity | `upload_refined.py:132` | strip_leading_paren_group's regex \([^)]*\) stops at the first ')', so a legitimate title whose leading parenthesised group itself contains nested parens is mangled and PUT to the live case Name. |
| low | robustness | `upload_refined.py:554` | create_new_version compares majorVersion (from the tests API JSON) with the int TARGET_MAJOR_VERSION and computes major+1; if the API ever returns majorVersion as a string, both raise TypeError and ab |
| low | correctness | `upload_refined.py:523` | create_new_version treats major>=2 as 'already v2.0' and never re-verifies the version produced by the newversion POST, so if a clone lands as a minor bump (v1.1) instead of v2.0 the idempotency guard |
| low | robustness | `wizard.py:2165` | push_to_zephyr shells out to upload_refined.py which reads refined-cases/**/zephyr_payload.json straight from disk with no re-run of validate_zephyr_payload — so a bundle that predates the >=3-<li> va |
| low | robustness | `wizard.py:1964` | export() calls generate_coverage_gaps() (a blocking LLM round-trip) directly in the async endpoint body rather than via run_in_threadpool, stalling the event loop for the whole call and blocking every |
| low | state-machine | `wizard.py:1936` | The /export endpoint has no _can_synthesize confirm gate and will fall back to a client-supplied req.session, so an unconfirmed (confirmed=False) session can be written as a Complete refined-cases bun |
| low | correctness | `wizard.py:1998` | art_string is derived with inconsistent caps (confirm_step caps 8 IDs, export caps 6) and both silently truncate ART IDs beyond the cap, so a case linking many ART tests gets an incomplete/inconsisten |
| low | robustness | `wizard.py:1047` | Search handlers run synchronously on the event loop; a hybrid search executes sentence-transformer inference inline (no run_in_threadpool), blocking all other requests for the duration. |

## Fixed 2026-07-27d — path-traversal + auth batch (rows struck above)
- Library-filename traversal (`pytest_create.py`) — validate full basename before path build
- Export case_key traversal (`wizard.py`) — `_CASE_KEY_RE` at top of export() + resolved-path check (also closes the export-gate `1936/1939` rows)
- Agent-bridge job ownership (`agent_bridge.py`/`agent_jobs.py`) — deliver enforces X-CK-Session ownership
- CORS lockdown (`main.py`) — CORSMiddleware, localhost allowlist, `CK_ALLOWED_ORIGINS` to widen
- +8 regression tests (`tests/test_security_batch2.py`), all in-process (no network/testbox)

## Fixed this session (2026-07-27c) — not in the table above
- SSH command injection (pytest_create.py setup -> pt_exec exec string) — validated + shlex.quote
- Framework-guard bypass (pt_exec _assert_command_allowed) — added redirection/interpreter/subst/rsync/install/-t checks
- Stored XSS (objective HTML) — new html_sanitize.py allowlist, applied at all objective store points
- Secret leak (api_key/token in session dumps + exported *-session.json) — redact_llm_config/safe_session_dict
- Admin reset never cleared PT sessions (wrong kind 'pytest' vs 'pt')
- Export destroyed a real first step (unconditional steps[0] overwrite -> prepend note instead)
