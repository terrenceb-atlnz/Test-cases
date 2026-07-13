# Objective Drafting Process (Repeatable Steps 1–4)

**Purpose**  
This document captures the repeatable drafting steps (now 1–4) used to enrich thin AWPTCM manual test cases in Zephyr.  

The goal is to synthesize **Objectives** as bulleted lists of artefacts (verifiable outcomes / desired end states) from historical TestLink data + cross-reference of the full Zephyr database + enriched ATPyLib automated suites, then draft corresponding Zephyr `testScript` steps and record traceability (including intelligent Zephyr cross-refs) to related cases that cover the same intent.

The output format for `objective` must be an HTML `<ul><li>...</li></ul>` list. The steps are the procedural verifications. See the reference XML export for the exact desired structure.

These steps produce the raw material that is recorded in the standardized per-case directory under `refined-cases/<AWPTCM-Txxxx>/`.

**Important**
- Objectives describe **artefacts** (what should be true), not the process or instructions.
- The number of objective bullets and the number of testScript steps is **not uniform** across cases. Use as many as needed for clear coverage.

**General Principles (applies to all areas)**
- The `objective` is a bulleted list of **artefacts** — declarative statements of desired end states or verifiable outcomes (e.g. "A port with no pluggable present defaults to...").
- Do **not** write procedural language ("Verify that...", "Set the port...") in the objective bullets.
- Always cover positive (happy path, defaults, supported) + negative (incompatible, error, unsupported).
- Explicitly call out observability/reporting ("...correctly reports...", "...accurately reflects...").
- Include special conditions relevant to the feature (no pluggable, hot-swap, LPI, unsupported configs, defaults, interop, etc.).
- Keep language platform-agnostic and reusable across similar manual cases.
- Use decisions/*.json primary matches ("m") + candidates to bootstrap; expand via keyword search in test suites.
- Reference the structure in `zephyr-scale-tests-export*.xml` exports (the `<objective>` contains the `<ul>` of artefacts; steps are separate).

---


## Key Data Sources

| File | Purpose |
|------|---------|
| `data/suites/test_id_description.json` | Flat map of all ATPyLib test IDs → description + log_analysis |
| `data/suites/suite_*.enriched.json` | Full enriched details for a suite (use for deep review) |
| `data/suites/suite_index.md` | Quick overview of available suites |
| `data/testlink_awp.json` | Historical TestLink cases (AWP- ids) for context and thin steps |
| Recent `zephyr-scale-tests-export*.xml` | Current Zephyr case structure, folder, labels (for later steps) |
| `data/zephyr_master.json` | Master list of cases with fields like `folder`, `labels`, `precondition` |
| `Zephyr-Database-30_Jun_2026.xml` | Full inherited Zephyr export (120 MB, 2.32M lines, ~45k cases across many projects). **Immutable source of truth. Never load the whole file.** |
| `data/zephyr_full/zephyr_cases.jsonl` + `slim_index.json` | **Recommended working format** (generated once via streaming parse). 54 MB JSONL (full normalized cases) + tiny fast-load index. Use for all regular Step 3 cross-references. See `data/zephyr_full/README.md` and `tool/extract_zephyr_xml.py`. |
| `data/decisions/dec_*.json` | Reviewed primary matches ("m") + confidence ("c") + rationale ("w") for traceability bootstrap |

**Common commands for exploration** (run from `Test-cases/`):
```sh
# Search descriptions for keywords
python3 -c '
import json
data = json.load(open("data/suites/test_id_description.json"))
for tid, entry in data.items():
    desc = (entry.get("description") or "").lower()
    if "auto" in desc and "speed" in desc:
        print(tid, entry.get("description","")[:100])
'

# Read a specific enriched suite
cat data/suites/suite_1342_enriched.json | head -100

# Look up primary decision + why for a case
python3 -c '
import json, glob
key="AWPTCM-T33235"
for f in sorted(glob.glob("data/decisions/dec_*.json")):
    d = json.load(open(f))
    if key in d:
        print(f, key, "->", d[key])
        break
'

# Zephyr web link template (use in traceability.md)
# https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T33234
# Markdown: [AWPTCM-T33234](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T33234)

# Helper: given keys, output ready markdown list items for traceability (run after selecting keys)
python3 -c '
import json, sys
keys = ["AWPTCM-T24", "AWPTCM-T33233"]  # replace with your selected keys
cases = {}
with open("data/zephyr_full/zephyr_cases.jsonl") as f:
    for line in f:
        for k in list(keys):
            if f"\"{k}\"" in line[:60]:
                cases[k] = json.loads(line)
                keys.remove(k)
        if not keys: break
for k, c in cases.items():
    obj = "Yes" if (c.get("objective") or "").strip() else "No"
    print(f"1. **[{c[\"key\"]}](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/{c[\"key\"]})** — {c[\"title\"]}")
    print(f"   - Folder: {c[\"folder\"]}")
    print(f"   - Objective: {obj}")
    print(f"   - Steps: {len(c.get(\"steps\", []))}")
    print(f"   - Justification: ...\n")
'

# === Zephyr full DB cross-reference (Step 3) - RECOMMENDED ===
# Load tiny index (fast) then filter
python3 -c '
import json
idx = json.load(open("data/zephyr_full/slim_index.json"))
matches = [c for c in idx if "auto" in (c.get("title","")+" "+c.get("folder","")).lower()][:10]
for m in matches:
    print(m["key"], m["num_steps"], m["has_objective"], m["title"][:55])
'

# Fetch full normalized case for a specific key (stream the JSONL)
python3 -c '
import json, sys
target = "AWPTCM-T24"
with open("data/zephyr_full/zephyr_cases.jsonl") as f:
    for line in f:
        if target in line[:30]:
            case = json.loads(line)
            print(json.dumps({"key":case["key"], "title":case["title"], "objective":case["objective"][:300], "steps":len(case["steps"])}, indent=2))
            break
'

# Quick ad-hoc with grep on JSONL (titles + folders)
grep -o "\"title\":\"[^\"]*[Aa]uto[^\"]*\"" data/zephyr_full/zephyr_cases.jsonl | head -5
```

---

## Step 1: Define the Objective (Artefact Bullets)

1. Read the current (usually very thin) objective or title for the AWPTCM-Txxxx case.
2. Review the primary match and notes from the corresponding entry in `data/decisions/dec_*.json` (and full candidates in `data/candidates.json`).
3. Review relevant historical TestLink cases (search `data/suites/testlink_awp.json` by AWP- id or keywords).
   - Start with the **primary decision match** ("m" in `decisions/`) and the top entries in `candidates.json`.
   - Broaden to other cases from the same or closely related suite families that exercise the core behaviour described in the manual case title and objective.
   - Prefer cases whose titles/summaries directly describe the key feature or behaviour under test.
   - **Explicitly document and show the list of relevant TestLink cases** (include at minimum: ID, title, suite, and a short justification for inclusion). Record this list to support traceability and artefact synthesis.
   - **User review**: Pause for user review and confirmation of the documented TestLink list (primary + relevant cases) before continuing to ATPyLib analysis or artefact synthesis.
   - Perform an additional review step for **tangentially related cases** (conduct broader searches using keywords derived from the feature area — e.g., for Port: "no pluggins", "defaults", "hot-swap", "pluggable insert"; for OSPF: "adjacency", "lsa", "area", "neighbor", "hello"; for other areas: appropriate feature-specific terms — plus any mentions of reporting/status/show commands, defaults, or error handling). Assess whether these introduce new artefacts not covered by the core relevant cases or are adequately addressed by them.
4. Review enriched ATPyLib cases that exercise the same area (see Step 4).
5. Produce a list of **declarative artefact statements**. Each bullet describes a desired end state or verifiable outcome.
   - Focus exclusively on **what should be true** after the scenario (artefacts), not instructions or process steps.
   - Cover positive scenarios, negative/failure cases, special conditions, and correct reporting.
   - Keep each bullet concise and observable.
   - The number of bullets varies per case (typically 1–10).

**Output format for `objective`** (exact string to store in `zephyr_payload.json` inside the case directory):

```html
<ul>
<li>A port with no pluggable present defaults to automatic speed and duplex negotiation.</li>
<li>Inserting a supported pluggable results in successful autonegotiation and link establishment.</li>
<li>A port configured for Auto speed and duplex establishes a link with a compliant link partner.</li>
<li>The port accurately reports Auto mode together with the negotiated speed and duplex values.</li>
...
</ul>
```

**Reference example** (from `zephyr-scale-tests-export*.xml` for AWPTCM-T33234):

```xml
<objective><![CDATA[<ul><li>A port with no pluggable present defaults to automatic speed and duplex negotiation.</li><li>Inserting a supported pluggable results in successful autonegotiation and link establishment.</li><li>A port configured for Auto speed and duplex establishes a link with a compliant link partner.</li><li>Link establishment succeeds when one side is set to Auto and the partner is forced to a supported speed or duplex.</li><li>The port accurately reports Auto mode together with the negotiated speed and duplex values.</li><li>Link status is correctly reported as up once autonegotiation completes.</li><li>Automatic speed and duplex negotiation produces a working link across all supported configurations with a compliant partner.</li></ul>]]></objective>
```

**Worked Examples**

**AWPTCM-T33233 – Port - Auto Negotiation**

```html
<ul>
<li>A port with no pluggable present defaults to automatic speed and duplex negotiation.</li>
<li>Inserting a supported pluggable results in successful autonegotiation and link establishment.</li>
<li>A port configured for Auto speed and duplex establishes a link with a compliant link partner.</li>
<li>Link establishment succeeds when one side is set to Auto and the partner is forced to a supported speed or duplex.</li>
<li>The port accurately reports Auto mode together with the negotiated speed and duplex values.</li>
<li>Link status is correctly reported as up once autonegotiation completes.</li>
<li>Automatic speed and duplex negotiation produces a working link across all supported configurations with a compliant partner.</li>
</ul>
```

---

## Step 2: Draft Zephyr-ready `testScript` Steps

1. Create a logical sequence of verification steps that exercise the artefacts listed in Step 1.
2. Use action-oriented language (the style used in the reference XML):
   - "Verify default behavior and autonegotiation with no pluggable present..."
   - "Set the port to Auto for speed and duplex. With link partner also on Auto, confirm..."
   - "Vary link partner configurations..."
   - "Test with incompatible..."
   - "Hot-insert and hot-remove..."
3. The first step (index 0) is often a **notes / traceability step** that preserves original thin content, wiki links, and a note about related ART tests / Traceability (see the reference XML). When Zephyr cross-references were used, include a short note such as "Related Zephyr cases and style references linked in Traceability" (with any particularly important direct links if they are not already in the historical note).
4. Subsequent steps are the clean verification actions. `expectedResult` is typically left empty.
5. Format exactly for the Zephyr Scale API (as stored in `zephyr_payload.json` inside the case directory):

   ```json
   "testScript": {
     "type": "steps",
     "steps": [
       { "description": "...", "expectedResult": "" },
       ...
     ]
   }
   ```

6. Keep steps high-level enough to be reusable across platforms but specific enough to be testable.
7. Include both happy-path and error-path scenarios.
8. The number of steps is **not fixed**. Match the coverage needed for the artefacts.

**Reference step style** (excerpt from the XML for AWPTCM-T33234):

```xml
<step index="1">
  <description>Verify default behavior and autonegotiation with no pluggable present (Auto as default for speed and duplex). Insert a supported pluggable and confirm autonegotiation occurs and link is established.</description>
</step>
<step index="2">
  <description>Set the port to Auto for speed and duplex. With link partner also on Auto, confirm link is established and port reports as Auto while showing the negotiated speed/duplex.</description>
</step>
```

**Worked Example – T33233 (Auto Negotiation) steps**

```json
"testScript": {
  "type": "steps",
  "steps": [
    {
      "description": "The testing for this is covered by the auto test : https://wiki.atlnz.lc/awpwiki/index.php/5000_mdi_mdix. Note: the automated test covers multiple test cases. Related ART Tests linked in Traceability.",
      "expectedResult": ""
    },
    {
      "description": "Verify default behavior and autonegotiation with no pluggable present (Auto as default for speed and duplex). Insert a supported pluggable and confirm autonegotiation occurs and link is established.",
      "expectedResult": ""
    },
    {
      "description": "Set the port to Auto for speed and duplex. With link partner also on Auto, confirm link is established and port reports as Auto while showing the negotiated speed/duplex.",
      "expectedResult": ""
    },
    {
      "description": "Vary link partner configurations across supported speeds and duplex modes (one side Auto, both sides Auto, partner forced to supported rates). Confirm successful link establishment in each case.",
      "expectedResult": ""
    },
    {
      "description": "Test with incompatible partner speed/duplex settings. Confirm link does not establish (or is correctly reported as down).",
      "expectedResult": ""
    },
    {
      "description": "Hot-insert and hot-remove supported pluggables while the port is set to Auto. Confirm link negotiation occurs cleanly on insertion and link status updates correctly on removal.",
      "expectedResult": ""
    },
    {
      "description": "Where the platform and media support it, test with LPI (Low Power Idle) enabled and disabled on Auto-negotiated links. Confirm LPI behavior and that link remains stable.",
      "expectedResult": ""
    }
  ]
}
```

**T33234 (Auto MDI/MDI-X)** follows the same pattern, substituting polarity/MDI/MDIX language in the verification steps.

**Worked Example – T33235 (Fixed port Speed) steps**

```json
"testScript": {
  "type": "steps",
  "steps": [
    {
      "description": "Set the port to a supported fixed speed and full duplex (e.g. 1000/Full). Confirm the link comes up at exactly that speed/duplex, the port reports the fixed speed (not Auto), and traffic can be forwarded.",
      "expectedResult": ""
    },
    {
      "description": "Repeat for other supported fixed speeds on the media type (100/Full, 1000/Full, etc. as applicable). Confirm link establishment at the exact configured rate and correct reporting in each case.",
      "expectedResult": ""
    },
    {
      "description": "Test fixed speed with half and full duplex where supported. Confirm correct link-up and reporting for each duplex setting at the fixed speed.",
      "expectedResult": ""
    },
    {
      "description": "Configure an unsupported speed on the port (or force mismatch with partner). Confirm link does not come up or is reported down, and status reflects the misconfiguration.",
      "expectedResult": ""
    },
    {
      "description": "Hot-insert / hot-remove supported pluggables or change cables while port is set to fixed speed. Confirm link state updates correctly and fixed configuration is retained after re-insertion where applicable.",
      "expectedResult": ""
    },
    {
      "description": "Verify show interface and related status commands accurately reflect the fixed speed/duplex configuration and current link state.",
      "expectedResult": ""
    }
  ]
}
```

*Note: Fixed speed cases share many concerns (hot-swap, reporting, link partner interop) with Auto cases but focus on exact rate enforcement rather than negotiation. Adjust step count to the artefacts.*

---



## Step 3: Cross-Reference the Zephyr Database (Intelligent)

**Purpose**  
After the objective artefacts (Step 1) and Zephyr-ready `testScript` steps (Step 2) have been drafted, perform a targeted, intelligent cross-reference against the full inherited Zephyr test case database. This step sits **between Step 2 and Step 4** (ATPyLib analysis).

**Goals of this cross-reference**
- Discover similar, sibling, or related cases already present in Zephyr (by title, folder path, labels, or functional keywords).
- Review how comparable cases express `objective` (if any) and `testScript` steps for style, phrasing, level of detail, and conventions used in the actual Zephyr Scale project.
- Identify additional artefacts or edge conditions that appear in other Zephyr cases for the same area.
- Locate exemplars of well-structured cases (even outside the thin MASTER template cases) to improve consistency.
- Record explicit traceability to other Zephyr cases (e.g. "See also AWPTCM-Txxxx in same folder for overlapping behaviour").
- Catch potential duplication before investing in ATPyLib deep-dive and final upload.

**Critical constraint**  
The database file (`Zephyr-Database-30_Jun_2026.xml`) is over **2.3 million lines**. It must never be loaded wholesale into memory or parsed naively on every case.

**Recommended access method (efficient + durable)**
Use the pre-generated durable artifacts (never touch the raw XML for queries):

- `data/zephyr_full/slim_index.json` — Load this entirely (≈10 MB). Fast in-memory filtering by folder, labels, title keywords, `has_objective`, `num_steps`.
- `data/zephyr_full/zephyr_cases.jsonl` — Stream only the matching full records when you need the complete `objective` + `steps`.
- Regenerate anytime with: `python3 tool/extract_zephyr_xml.py --xml Zephyr-Database-30_Jun_2026.xml --out-dir data/zephyr_full --force`

See the commands in the "Common commands for exploration" section above and `data/zephyr_full/README.md`.

**Search strategies (use the index first)**
1. Filter the slim index by folder path (note: folders in the full export vary; many cases live outside the current MASTER tree).
2. Filter by labels or title keywords taken from the current AWPTCM case + artefacts.
3. For candidates that look promising (especially those with `has_objective: true` and multiple steps), stream the jsonl to retrieve full objective + step text.
4. Prioritize:
   - Cases in similar functional areas (even if different folder).
   - Cases that have rich declarative objectives (good exemplars).
   - Siblings or near-duplicates of the target case.

**What to record per relevant hit**
- key, title, folder
- Whether it had a useful `objective` (and a couple of bullets or structure notes)
- Step count + style notes (action-oriented language? use of expected results? number of steps)
- Why relevant (style guide, extra artefact ideas, similar scenario, duplication risk, good exemplar)

**Document the list for traceability.md (similar to Top Relevant TestLink Cases)**

After reviewing candidates via `slim_index.json` + full cases from the JSONL, explicitly document every Zephyr test case that was identified and used for the cross-reference.

Use this consistent format (always include the **web link**):

```markdown
## Zephyr Cross-References (Step 3)

**Relevant Zephyr Scale cases identified**

These cases were reviewed from the full Zephyr database for style, objective structure, step patterns, artefacts, and overlap/siblings.

1. **[AWPTCM-T24](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T24)** — VRF: Check operation/performance of 1008 PIM-SM interfaces across 63 VRF's
   - Folder: /PIM-SM/PIM-SMv4/2111 1024 PIM Interfaces
   - Objective: Yes (per-VRF bullet list)
   - Steps: 6
   - Justification: Strong exemplar of declarative per-group objective bullets + systematic verification steps for commands and isolation. Pattern for reporting and cross-VRF behaviour.

2. **[AWPTCM-T33233](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T33233)** — Port - Auto Negotiation
   - Folder: /New Platform Test (MASTER)/New Platform Template/Port
   - Objective: (current thin state or after update)
   - Steps: ...
   - Justification: Direct sibling in Port area. ...
```

**Groups to consider**
- Siblings / same-folder or same-label cases
- Functionally similar cases (other folders/projects)
- Strong exemplars (rich objectives or particularly clear step structure)

**User review pause recommended** for the documented Zephyr list (parallel to the TestLink list), especially if it leads to changes in the draft objective or steps.

Always use the full markdown web link format shown above so the keys are clickable. The base URL is `https://jira.atlnz.lc/secure/Tests.jspa#/testCase/{KEY}`.

When you later run the uploader (`tool/upload_refined.py --execute`), the cases listed in this section will automatically have **web links (tracelinks)** created inside the target Zephyr case (exactly like the ATPyLib entries). The full `traceability.md` is also attached.

Record the final list in `traceability.md`. This becomes part of the permanent traceability for the case.

This approach is fast, repeatable, and the data is preserved in both the original XML and the normalized JSONL.

**What to do with findings**
- Use them to **refine** the objective bullets or step descriptions (e.g. adopt consistent phrasing, add missing artefact, align step style).
- If major changes result, consider a short user review before moving on.
- Document decisions: "Adopted wording from AWPTCM-Txxxx for reporting accuracy bullet."

**Output to capture in `traceability.md`**

Add / populate this section:

```markdown
## Zephyr Cross-References (Step 3)
- Siblings / same-folder cases reviewed:
  - AWPTCM-Txxxx (title) — folder — relevance
- Functionally similar cases (other labels/folders):
  - ...
- Exemplar objectives / step patterns adopted or compared:
  - ...
- Notes / refinements made as a result:
```

Do **not** continue to Step 4 (ATPyLib) until the Zephyr cross-reference findings have been reviewed and incorporated (or explicitly scoped out).

**Tool support note**: The server-backed Ask CK workbench (`ask-ck/CK-main/` — Objective/Test Case Generator) provides real candidate data for Steps 1-2 and LLM-assisted pre-selection for Step 3 (via retrieval + `suggest_atp` prompt), with user confirmation required. See `ask-ck/CK-main/SERVER-README.md`.

---

## Step 4: Examine ATPyLib Automated Suites One-by-One for Coverage + Gaps

1. Start with `data/suites/suite_index.md` and a broad keyword search in `test_id_description.json`.
2. Search for terms taken directly from the title, primary decision, and the intended artefacts (e.g. `fixed`, `speed`, `1000`, `"link comes up"`, `unsupported`, `polarity`).
3. For each promising test ID, read the full description + `log_analysis`:
   - What exact behavior does it exercise?
   - Was it actually run (`analysed: true`)?
   - On what platform / software version?
   - Result (PASS / FAIL / UNSUPPORTED)?
4. Build a short list of the **most relevant** ATPyLib cases (usually 4–8 IDs). Include the primary decision match's related automated coverage and expand for breadth.
5. Explicitly note gaps:
   - Behaviors only covered in TestLink historical cases (e.g. certain defaults or "no pluggable")
   - Missing or thin coverage in automation (e.g. specific speeds, LPI, unsupported)
   - Suites that are only partially related or command-only vs behavioral

**Example search command** (adapt keywords per case):
```sh
python3 -c '
import json
data = json.load(open("data/suites/test_id_description.json"))
for tid, entry in data.items():
    d = (entry.get("description") or "").lower()
    if any(k in d for k in ["speed bundle", "link comes up at speed", "fixed", "unsupported speed"]):
        print(tid, ":", entry.get("description","")[:110])
' | head -20
```

**Cases identified for T33233 / T33234 (example)**

- `1342.301.12` – Command Execution: Speed Bundle (auto)
- `1342.301.13` – Command Execution: Polarity Bundle (auto)
- `1346.1001.20000000` – Confirm link comes up at speed auto
- `1346.1001.20` – Confirm link comes up at all supported speeds
- Hot-swap / pluggable handling from suites `5049`, `5500`, `7000` (LIF/XEM cases)

**Gaps noted during review**
- "No pluggable present" default behavior is primarily documented in older TestLink cases.
- LPI interaction with auto-negotiation has limited direct coverage in the enriched suites.
- Hot-swap recovery is covered at the stack/module level rather than pure port-level pluggable tests.

Record the final list of relevant IDs — this list becomes the "ART Test Cases" string used later (Traceability & Upload Prep section). Also cross-reference the primary decision ID from `decisions/`.

---

## Repeatable Workflow (Proven Pattern)

1. Create `refined-cases/AWPTCM-Txxxx/` directory.
2. Build `traceability.md` starting with:
   - Primary Decision (from `decisions/dec_*.json`)
   - Top Relevant TestLink Cases (primary + siblings from same suite)
3. **User review pause** — present the documented TestLink list for confirmation before continuing.
4. Perform tangential review (broader keyword search) and record conclusion.
5. Draft objective artefact bullets (Step 1) + Zephyr `testScript` steps (Step 2).
6. **Zephyr Database cross-reference (Step 3)** — intelligently search using `data/zephyr_full/slim_index.json` + JSONL (see dedicated section).
   - Identify relevant cases (siblings, similar, exemplars).
   - **Build documented list** of every used/identified Zephyr case with full web links, title, folder, objective/steps summary, and justification (format shown in Step 3).
   - Refine drafts based on findings.
7. **User review pause (optional but recommended)** — present the documented Zephyr cross-reference list.
8. ATPyLib review (Step 4: search `test_id_description.json` + enriched suites) + gaps + ART string.
9. User confirms objective.
10. Write final `traceability.md` (full structure below) + `zephyr_payload.json` (objective + testScript with minimal first "Note: Related ART Tests..." step. Optionally add "Related Zephyr cases linked in Traceability.").

**Standard `traceability.md` structure**
```
# Traceability & Supporting Data for AWPTCM-Txxxx (Title)
## Primary Decision
## Top Relevant TestLink Cases
## Zephyr Cross-References (Step 3)
## ATPyLib Cases (Step 4)
## Gaps Noted
## Tangential Cases Reviewed
## ART Test Cases String
```

Example snippet for the Zephyr section (with required web links):

```markdown
## Zephyr Cross-References (Step 3)

**Relevant Zephyr Scale cases identified**

1. **[AWPTCM-T24](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/AWPTCM-T24)** — VRF: Check operation/performance of 1008 PIM-SM interfaces across 63 VRF's
   - Folder: /PIM-SM/PIM-SMv4/2111 1024 PIM Interfaces
   - Objective: Yes (per-VRF bullet list)
   - Steps: 6
   - Justification: ...
```

## Checklist – Steps 1–4 Complete?

- [ ] Objective written as `<ul><li>` artefact bullets (declarative end-states, not process)
- [ ] Zephyr `testScript` steps drafted in correct JSON structure (number varies)
- [ ] Zephyr cross-reference (Step 3) performed using `data/zephyr_full/` (slim_index + JSONL); every identified/used case documented in traceability.md **with full web link** (https://jira.atlnz.lc/secure/Tests.jspa#/testCase/KEY), title, folder, objective/steps info and justification. Format parallels Top Relevant TestLink Cases.
- [ ] Relevant ATPyLib cases identified via search + manual review of enriched data (cross-ref primary decision)
- [ ] Gaps explicitly noted (especially anything only in TestLink or thinly covered)
- [ ] Short list of ATPyLib IDs ready to be turned into a "ART Test Cases: ..." string later
- [ ] Work saved in `refined-cases/<AWPTCM-Txxxx>/zephyr_payload.json` (objective + testScript) and `traceability.md`

---

See the main `Test-cases/README.md` and reference exports such as `zephyr-scale-tests-export*.xml` for current state and the desired output format.

---

**Usage notes**
- Start with Port family cases (T33233+) or next undecided high-confidence decisions.
- Adapt the generic template and special conditions list per area (IPv6, QoS, Switching, ARP, etc.).
- For non-Port areas, drop pluggable/LPI references and substitute feature-appropriate conditions (e.g. restart, failover, scale, unsupported options).
- During drafting, if you discover a better primary match or additional coverage, update the corresponding `data/decisions/dec_XX.json` entry (and note confidence).

**Tool assistance**: The Ask CK server app (`ask-ck/CK-main/`) now surfaces real candidates for Steps 1-2 and provides LLM pre-selection assistance for Step 3 ATPyLib (user still confirms). Step 4 synthesis includes human-readable display. See `ask-ck/CK-main/SERVER-README.md`. (In the Ask CK UI these process steps appear as Generator steps 2-6.)

**Mini skeleton for a non-Port area (example: basic IPv4 ICMP echo)**

Objective bullets (artefact style):
<ul>
<li>The device responds to ICMP echo requests sent to its configured IPv4 addresses.</li>
<li>ICMP echo replies are generated with the correct source address selection.</li>
<li>Loopback interface addresses respond correctly to echo requests.</li>
<li>Error conditions (unreachable destinations, oversized packets) are handled and reported appropriately.</li>
</ul>

Typical steps areas:
- Default / configured interface responds to ping from compliant peer.
- Loopback address handling.
- Source address selection / reply behavior.
- Negative: unreachable / filtered cases, oversized packets, rate limits if applicable.
- Reporting via counters or logs if relevant.

Search seeds: `icmp`, `echo`, `ping`, `9996` (from decisions), `loopback`.

---

## Next Steps / Traceability & Upload Prep (after Steps 1–4)

After completing Steps 1–4:

1. Consolidate the list of ATPyLib test IDs (from Step 4 + primary decision match).
2. Record / update the mapping in the relevant `decisions/dec_XX.json` if not already precise (use "m" for best single, or expand later for many-to-one).
3. Create the standardized output directory (if it does not already exist):
   `Test-cases/refined-cases/<AWPTCM-Txxxx>/`
4. Inside the directory, create two files:
   - `traceability.md` — Contains the primary decision, relevant TestLink cases, **Zephyr cross-references (Step 3, with web links)**, ATPyLib cases, gaps, tangential review notes, and the ART Test Cases string. Listing Zephyr cases here will cause the uploader to create actual "Web Links" (tracelinks) on the case in Zephyr.
   - `zephyr_payload.json` — Contains the final `objective` (as `<ul><li>` HTML) and `testScript` in the exact structure expected by the Zephyr Scale API / bulk upload.
5. Optionally add a free-text "ART Test Cases: ..." note in `traceability.md` for later Zephyr attachment.
6. When ready for upload, use the dedicated uploader (recommended):

   ```
   cd Test-cases
   JIRA_KEY=... python3 tool/upload_refined.py --dry-run --keys AWPTCM-Txxxx
   JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-Txxxx --verify
   ```

   Or target groups: `--groups "Port (7)" "IPv4 (44)"` (etc). See `tool/upload_refined.py --help`.
   The script sends `objective` (as `<ul>`) + `testScript` (normalized to `STEP_BY_STEP`) via the ATM REST API.

7. After upload, mark progress (e.g. update review batches or a tracking md) and optionally rebuild `refined-viewer.html`.

See `README.md`, `tool/`, and `data/decisions/` for supporting scripts and prior batch decisions.

---

## Lessons Learned & Current Status (as of 2026-06-29)

**Key refinements made:**
- Converted the drafting process into a clean, reusable template (see Repeatable Workflow section).
- Standardized per-test-case output: `refined-cases/<AWPTCM-Txxxx>/` with `traceability.md` (decisions, TestLink list, ATPyLib, gaps, ART string) + `zephyr_payload.json` (objective `<ul>` + testScript).
- User-review pause after documenting TestLink list (primary + relevant); tangentials optional/omittable when approved.
- Generalized for any area (Port, IPv4 ARP/DHCP/Static/BGP/VRF, PoE/LED, Bootloader, Auth, etc.). "Minimal first testScript step" rule for partial ART coverage.
- Number of objective bullets and steps is flexible; focus on declarative artefacts (end states), not procedures.
- For low/null-primary cases: curate the full relevant TestLink *feature family* + cross-reference dedicated ART suites (e.g. 1355 for NLB).
- **Platform-agnostic language:** Qualify specifics with "on some platforms if applicable" or "per device spec" (per user feedback on LED/fault behavior variation).
- **Thin TL / automation-driven cases:** When primary is minimal (e.g. "check supported" or "run ART"), focus on feature-family + ART validation; document gaps explicitly.
- **Subgroup organization:** Use descriptive subgroups (e.g. "IPv4 ARP (xx)/", "IPv4 DHCP (xx)/", "IPv4 Static (xx)/", "IPv4 VRF (xx)/", "IPv4 BGP (xx)/", "Sanity Check (15)/") for manageability.
- **User feedback loop:** Incorporate refinements quickly (e.g. platform notes, generalization); continue explicit pauses.

**Current state of processed cases:**
- ~30+ cases fully processed through the workflow across groups: Port (~7), IPv4 variants (ARP/DHCP/Static/BGP/VRF ~10+), PoE/LED/Sanity (~5), Switching (~4), Auth/Security (~4), Management (~2), Bootloader (~1).
- Recent focus: IPv4 areas (T43849 Local Proxy ARP, T43851 DHCP ARP Probe, T43853 120-day lease, T43854 DNS Relay, T43855 IPv4 Static, T43858 BGPv4, T43859 VRF-Lite traceroute).
- Workflow validated on thin Zephyr cases, VRF isolation, platform variation, and mixed TL/ART sources.
- See [SESSION_STATE.md](SESSION_STATE.md) for full chronological activity, detailed lessons learned per batch/case, exact lists, and wrap-up.

**Recommended next actions:**
- Process remaining high-confidence decisions from dec_05+ (e.g. T43859 siblings, T43860 IP Route Filter, dec_06+ PoE/ECMP/stack cases).
- Consider adding a small helper script in `tool/` (e.g. `scaffold_case.py`) to initialize new `refined-cases/<key>/` directories.
- When ready, feed `zephyr_payload.json` files into upload tooling targeting Zephyr Scale `objective` + `testScript`.
- Periodic sync of lessons/counts back to this doc and README.md.

*Document maintained as a living template. All case-specific history and lessons moved to `refined-cases/` subdirectories and [SESSION_STATE.md](SESSION_STATE.md).*
