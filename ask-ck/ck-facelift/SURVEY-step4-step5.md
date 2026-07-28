<!-- Preserved artefact. Do not re-run this survey; re-read it. -->

# OUTCOME: commit 6 was DROPPED (2026-07-28)

> **Decision: do NOT type `WizardSession.step4` / `step5`.** User decision, 2026-07-28,
> after this survey. The rationale lives in `PLAN-backend-module-split.md` under commit 6.
> This file is the evidence behind that decision, kept because **Part B commits 9-10 need
> the consumer map below** — they relocate `gates.py` and the synthesis handlers, which is
> where most of these call sites live.
>
> Produced by a 21-agent survey (7 dimensions -> adversarial verification of every hazard
> -> synthesis), ~1.58M subagent tokens, 49 min. **11 of 13 hazards survived** adversarial
> verification; 4 were blockers. Two claims were independently re-verified by hand before
> the decision: the 17 `isinstance(..., dict)` guards and the transient `stale` key.
>
> Path prefixes in the text below: `$S` = `ask-ck/CK-main/CK_server`, `$R` = repo root,
> `$D` = `ask-ck/objective-drafting/refined-cases`. Line numbers are as of commit `0b47926`
> and will drift — treat them as hypotheses to re-verify, not facts (that lesson is itself
> recorded in the plan's A4+A5 section).

---

# Survey report — typing wizard `step4` / `step5` (commit 6)

Path prefixes used below (expand literally):
- `$S` = `/media/terrenceb/mnt/testbox_home/copilot/Test-cases/ask-ck/CK-main/CK_server`
- `$R` = `/media/terrenceb/mnt/testbox_home/copilot/Test-cases`
- `$D` = `/media/terrenceb/mnt/testbox_home/copilot/Test-cases/ask-ck/objective-drafting/refined-cases`

Declaration sites under review: `$S/models.py:150` (`step4`), `$S/models.py:154` (`step5`) — **wizard**; `$S/models.py:183`, `$S/models.py:184` — **PtSession, different shape, same names**.

My own measurements this session (read-only, scratchpad scripts at `/tmp/claude-1971/-media-terrenceb-mnt-testbox-home-copilot-Test-cases/5eff94ba-b305-4e2c-8e60-efda5ba8e420/scratchpad/{ondisk.py,ondisk2.py,probe.py}`): the on-disk population, the frontend/test/template site counts, and the pydantic 2.13.4 semantics table. ck.db figures are taken from the task context as given and were not re-derived.

---

## 1. The real shape

Two populations. **ck.db** = 35 wizard session rows (given). **On-disk** = `$D`, which I measured: **43** `zephyr_payload.json` and only **2** `*-session.json` (`AWPTCM-T33233`, `AWPTCM-T33373`). Note `REFINED_DIR` is `ask-ck/objective-drafting/refined-cases/`, **not** `ask-ck/refined-cases/` as the task brief said — that directory does not exist.

`objective-drafting` bundles are the *feeder* for step5: `_backfill_from_refined` copies `testScript` verbatim out of `zephyr_payload.json` into `sess.step5` (`$S/routers/wizard.py:375-380`), so the 43 payloads — not the 9 non-empty sessions — are the authoritative step-shape contract.

| dotted path | types | count (ck.db / on-disk) | nullable | who writes | who reads |
|---|---|---|---|---|---|
| `step4` | dict | 35/35 present, **28 empty** / 2 of 2 present, 0 empty | field itself never null | `wizard.py:298,303→` no; writers at `wizard.py:298,314,375,1851,1907,1935,1968,2006,2035,2070` | `wizard.py:248,296,311,347,1850,1999`; `db.py:1022`; export via dump `wizard.py:2180` |
| `step4.objective` | str (sanitized `<ul><li>` HTML) | 7 / 2 of 2 | yes — read as `(x or "").strip()` | `wizard.py:375,1852,1894,2005,2031,2071` (`:2071` **unsanitized**) | `wizard.py:250,349,1928,2241`; `llm.py:957`; `db.py:1024`; `generator.js:162,233` |
| `step4.provenance` | dict | 6 / 2 of 2 | **yes**, `result.get()` can be None | `wizard.py:1853,2073` | **nobody in Python.** Only `generator.js:245,286` (display) |
| `step4.confirmed` | bool | 5 / 2 of 2 (both `True`) | yes (truthiness only, never `is True`) | `wizard.py:298,376,1854,1900,1905,1930,2074` | `wizard.py:297,1911`; `db.py:1035`; `generator.js:164,244,533` |
| `step4.confirmed_at` | str ×3, **null** ×1 / str ×2 | 4 / 2 of 2 | **yes** | `wizard.py:298(None),1855(None),1901,1906(None),1931,2075` | **ZERO readers.** grep over all `*.py` and all `static/` → writes only |
| `step4.testScript` | dict ×3, **null** ×1 / dict ×1 + **null** ×1 | 4 / 2 of 2 | **yes** | `wizard.py:1857,1967,2032` + preserved at `:1857` | `wizard.py:313,350,2220`; `db.py:1027`; `generator.js:227` |
| `step4.backfilled` | bool | 1 / **0 of 2** | yes | `wizard.py:376` only | **ZERO readers** (no `.py`, no `static/`) |
| `step4.stale` | bool | **0 of 35** / **0 of 2** | yes | `wizard.py:298` | **`generator.js:163` only** — a live browser contract invisible to any data-derived survey |
| `step5` | dict | 10/35 present, **5 empty** / 2 of 2 present | never null | `wizard.py:303,314,380,1964,2025,2077` | `wizard.py:301,312,348,1857`; `db.py:1023` |
| `step5.testScript` | dict | 5 / 2 of 2 | yes (`or {}` everywhere) | `wizard.py:314,380,1961,2026,2078` | `wizard.py:302,313,350,2219`; `db.py:1026`; `generator.js:226` |
| `step5.provenance` | dict | 1 / **1 of 2** | yes | `wizard.py:2027,2079` | `generator.js:285` only |
| `step5.confirmed` | bool | 1 / **0 of 2** | yes | `wizard.py:303,380` | `pytest_create.py` no; wizard reads it nowhere; `generator.js` no |
| `step5.backfilled` | bool | 1 / **0 of 2** | yes | `wizard.py:380` only | **ZERO readers** |
| `step5.stale` | bool | **0 of 35** / **0 of 2** | yes | `wizard.py:303` | **`generator.js:185` only** |
| `*.testScript.type` | str, always literal `"steps"` | 8/8 ck.db, **43/43** payloads | — | `llm.py:695,1020`; `wizard.py:1959,2239` | **ZERO readers** |
| `*.testScript.steps` | list | 8 scripts / 15+15+7 on-disk sessions; **43 payloads** | yes (`.get("steps", [])`) | same as above | `wizard.py:2223`; `llm.py:766,993`; `db.py:1026`; `generator.js:273` |
| `…steps[].description` | str | **74/74** ck.db + **276/276** payloads = **350/350** | **no** — hard-required by `llm.py:781-782` | `llm.py:663,676,992`; `wizard.py:2234` | `wizard.py:2232`; `llm.py:770,776,1003`; `pytest_create.py:662`; `generator.js:280` |
| `…steps[].expectedResult` | str | **350/350** | yes — always `or ""` | `llm.py:665,992` | `wizard.py:2234,2236`; `pytest_create.py:666`; `generator.js:281` |

**Divergences between the two populations — all of them:**

1. **`step4.provenance` is multi-generational, and on-disk proves it.** `AWPTCM-T33373-session.json` step4.provenance has **10** keys, no nulls: `{auth_method, error, gaps_prompt, gaps_response, model, objective_prompt, objective_response, provider, steps_prompt, steps_response}` — the legacy *combined* shape from `$S/llm.py:1051-1055`, which today's `synthesize_objectives` (`$S/llm.py:925-933`, 7 keys) never emits. `AWPTCM-T33233-session.json` has a **different** 4-key legacy shape `{auth_method, note, provider, source}` with `provider` and `auth_method` **both null**, in *both* step4 and step5. Conversely current code writes `objective_used` (`$S/llm.py:1010`) which appears in **0 of 35** ck.db rows **and 0 of 2** on-disk bundles. Persisted provenance is neither a subset nor a superset of what the code can produce.
2. **`confirmed_at` has both string formats on disk too**: `'2026-07-12T23:03:55.652444'` (T) in T33373, `'2026-07-13 03:11:37.604091'` (space — what `json.dumps(default=str)` writes, `$S/db.py:976`, documented `$S/timeutil.py:12-14`) in T33233. Both parse via `datetime.fromisoformat` — verified.
3. **`step5.confirmed` / `step5.backfilled` appear in ck.db (1 row each) but in 0 of 2 on-disk bundles.** T33373's step5 is `{testScript}` only. n=2; do not read anything into this.
4. **`stale` is in NEITHER population** (0/35, 0/2) yet is written by shipped code and read by the browser. Any model derived from data alone will omit it. This is the single most dangerous gap in the shape.
5. **`step4.testScript = null` occurs in both populations** (1 ck.db row; T33233 on disk). Non-`Optional` here is a load-time `ValidationError` — probed: `ValidationError` for `{"testScript": None}` against a non-Optional field.
6. **`full_session` on disk holds `{llm}` or `{}`** — no nested copy of step4/step5. No second shape hidden inside the bundles. Verified in both files.
7. **Nothing reads `*-session.json` back.** grep for a reader across all `*.py` finds none. The 2 bundles are provenance-only; a serialization change cannot break code there, only a human comparing artefacts.

**Sample-size honesty:** the *key inventory* rests on 7 non-empty step4 rows + 5 non-empty step5 rows + 2 on-disk bundles. That is thin, and it demonstrably missed `stale` and `objective_used`. The *step-entry* contract is the opposite: **350/350 uniform `{description, expectedResult}`** across two independent populations. Type `TestStep`/`TestScript` with confidence; treat `Step4`/`Step5` key sets as provisional and keep them open.

---

## 2. Proposed models

```python
# --- $S/models.py, inserted above class WizardSession (models.py:142) ---

class TestStep(BaseModel):
    """One Zephyr test step. 350/350 persisted entries (74 in ck.db + 276 across the 43
    on-disk zephyr_payload.json) are exactly {description, expectedResult} — the tightest
    contract in the session. `description` is hard-required by validate_zephyr_payload
    (llm.py:781-782) but is left defaulted here, because save_steps (wizard.py:1954-1959)
    and _backfill_from_refined (wizard.py:378-380) currently accept unvalidated input and
    let export complain. Requiring it converts "warn at export" into "reject at the door",
    which is a behaviour change, not a typing change."""
    model_config = ConfigDict(extra="allow")
    description: str = ""
    expectedResult: str = ""


class TestScript(BaseModel):
    """`type` is write-only and always the literal "steps" (llm.py:695, 1020;
    wizard.py:1959, 2239; 8/8 ck.db + 43/43 on-disk). No reader anywhere."""
    model_config = ConfigDict(extra="allow")
    type: str = "steps"
    steps: List[TestStep] = Field(default_factory=list)


class Step4(BaseModel):
    """Objective synthesis. EVERY field Optional-with-default: 28 of 35 persisted rows are
    an empty dict, and the keys that do occur are sparse (objective 7, provenance 6,
    confirmed 5, confirmed_at 4, testScript 4, backfilled 1)."""
    model_config = ConfigDict(extra="allow")
    objective: Optional[str] = None            # sanitized <ul><li> HTML; read as (x or "").strip()
    provenance: Optional[Dict[str, Any]] = None  # DELIBERATELY free-form — see justification
    confirmed: bool = False
    confirmed_at: Optional[str] = None         # STAYS A STRING in this commit — see justification
    testScript: Optional[TestScript] = None    # legacy location, actively re-mirrored; null in 1 ck.db row + 1 on-disk bundle
    backfilled: bool = False                   # write-only (wizard.py:376)
    stale: bool = False                        # 0/35 in ck.db, 0/2 on disk, but WRITTEN by
                                               # wizard.py:298 and READ by generator.js:163.
                                               # Omitting it silently kills the stale badge.


class Step5(BaseModel):
    """Test-step synthesis."""
    model_config = ConfigDict(extra="allow")
    testScript: Optional[TestScript] = None
    provenance: Optional[Dict[str, Any]] = None
    confirmed: bool = False
    backfilled: bool = False
    stale: bool = False                        # wizard.py:303 -> generator.js:185
```

And, **only if** the annotation flip is actually taken (see §5 — I recommend against it in commit 6):

```python
class WizardSession(BaseModel):
    ...
    step4: Step4 = Field(default_factory=Step4)   # was models.py:150
    step5: Step5 = Field(default_factory=Step5)   # was models.py:154
```

**Declared vs free-form — `provenance` is the hard case, and the answer is: leave it a dict.**
13 distinct sparse keys in ck.db, and the on-disk population adds a **third** generation (10-key combined shape in T33373; 4-key `{source, note, provider, auth_method}` with two nulls in T33233) while current code emits an `objective_used` key that exists in neither population. No Python code anywhere introspects it — the only consumer is a display panel at `$S/static/js/generator.js:245,285`. Typing it would be pure churn plus a permanent migration liability, and would gain nothing: `Dict[str, Any]` already round-trips every generation losslessly. `objective`, `confirmed`, `backfilled`, `stale` and `testScript` are the ones worth declaring; `provenance` is not.

**`extra=` — must be `"allow"`. This is the data-loss decision.** Probed on 2.13.4:

| setting | `Step4(**{"objective":"o","future_key":1}).model_dump()` |
|---|---|
| `"ignore"` (**pydantic default**) | `{'objective': 'o'}` — **key silently gone** |
| `"allow"` | `{'objective': 'o', 'future_key': 1}` |
| `"forbid"` | `ValidationError` |

`"ignore"` is a live data-loss path, not a hypothetical: `$S/routers/wizard.py:298` writes `stale`, which appears in a survey-derived model only if you *know* to add it; with `"ignore"` the next `WizardSession(**raw)` drops it and the unconditional `_persist_session` at `$S/routers/wizard.py:656` erases it from ck.db. `"forbid"` is worse than useless here — `SynthesisRequest.session` is typed `WizardSession` (`$S/models.py:193`) and the browser POSTs back the whole session it last received (`generator.js:249,290,595,632,677`), so `"forbid"` would 422 every synthesis and export request coming from a session that happens to carry `stale`. **`extra="allow"` on all four models, plus declaring `stale` explicitly** (belt and braces: `"allow"` preserves it on round-trip, the declaration makes it visible to the schema and to `model_dump` defaults).

**`confirmed_at`: keep it a `str` in commit 6. Do not reuse `UtcDatetime` here.**
The round-trip is *technically* proven — `StepState.confirmed_at` (`$S/models.py:49`) already does it: `model_dump()` leaves a `datetime`, `db.save_session`'s `json.dumps(..., default=str)` (`$S/db.py:976`) writes `'… 12:00:00.123456+00:00'`, and `models._coerce_utc` → `as_utc` reads both separators back (`$S/timeutil.py:51-53`). Both legacy naive formats in ck.db **and** both formats on disk parse via `fromisoformat` (verified). And there is **zero read pressure**: grep over every `*.py` finds only writes (`wizard.py:298,1855,1901,1906,1931,2075`) plus `StepState`'s own field, and grep over `$S/static/` finds **0 hits** in 0 files. So nothing breaks.

But it changes the wire format from `'2026-07-15T00:42:37.575327'` to `'2026-07-15T00:42:37.575327+00:00'`, and that flows straight into the exported `*-session.json` (`$S/routers/wizard.py:2319`, written at `:2403`) — a published artefact. That is a data-format change to a shipped file, and it does not belong in a commit called "add types". Split it. `$R/ask-ck/ck-facelift/PLAN-backend-module-split.md:608-616` reaches the same conclusion independently.

**`default` vs `default_factory`: use `default_factory`.** Pydantic v2 does deep-copy a mutable model default per instance — probed: `a.step4 is b.step4` → `False`, so `= Step4()` carries no shared-state hazard and today's `= {}` at `models.py:150` is likewise safe. But `default_factory=Step4` states the intent instead of relying on that copy semantics, and `List[TestStep]` inside `TestScript` should be `default_factory=list` for the same reason. No behavioural difference measured; this is a legibility call.

**`validate_assignment=True`: NO, and here is the part that undercuts the whole "non-behavioural first step" framing.**

Probed (2.13.4):

| | `validate_assignment=False` (default) | `validate_assignment=True` |
|---|---|---|
| `WizardSession(**raw)` from ck.db | step4 **becomes `Step4`** | step4 becomes `Step4` |
| `sess.step4 = {"objective":"o","stale":True}` | stays a **plain `dict`**; `model_dump()` still emits it, with one `UserWarning: PydanticSerializationUnexpectedValue` | coerced to `Step4`; `stale` kept (because `extra="allow"`) |
| `sess.step4["confirmed"] = True` | `TypeError: 'Step4' object does not support item assignment` | same |
| `sess.step4 = "junk"` | accepted, persisted, `ValidationError` on next load | `ValidationError` at the assignment |

With `va=False` the annotation is **cosmetic for writes** and you inherit `PydanticSerializationUnexpectedValue` warning noise on every dump. With `va=True` the 13 in-place mutation sites the plan enumerates (`$R/ask-ck/ck-facelift/PLAN-backend-module-split.md:641-645`: `wizard.py:1894,1900,1901,1905,1906,1927,1930,1931,1961,1967,2005,2031,2032`) need rewriting to `model_copy(update=...)`.

**The trap: `va=False` does not make the change non-behavioural.** Construction always validates. `WizardSession(**raw)` at `$S/routers/wizard.py:213` coerces the persisted dicts into models *regardless* of `validate_assignment` — which is exactly what detonates every hazard in §3. `va=False` merely makes the breakage *intermittent* (a model until the first raw-dict assignment de-types the field back to a dict, then normal again), i.e. state-dependent and harder to diagnose. `va=True` at least makes it deterministic and therefore test-visible. If you flip the annotations at all, flip `validate_assignment` with them.

---

## 3. Blocking hazards

Six survive verification. **H1–H3 share one root cause**, stated once:

> A pydantic model is not a `dict`. `$S/routers/wizard.py:213` `WizardSession(**raw)` coerces the persisted step4/step5 dicts into `Step4`/`Step5` on every cold load. **Nine** `isinstance(..., dict)` guards on those attributes then take the `else {}` branch — `$S/routers/wizard.py:249, 296, 301, 311, 312, 347, 348, 1850, 1999` — and a fully-populated step4 reads as empty. Probed: `isinstance(Step4(), dict)` → `False`; `Step4().get('x')` → `AttributeError`; `Step4()['x']` → `TypeError: not subscriptable`. The eight `sess.stepN or {}` sites (`:248, 1857, 1893, 1925, 1960, 1966, 2004, 2030`) never yield `{}` either, because `BaseModel` defines no `__bool__` — probed: `"__bool__" in BaseModel.__dict__` → `False`, `bool(Step4())` → `True`.
>
> **Three guards are NOT affected — do not "fix" them:** `$S/routers/wizard.py:2219, 2220, 2241` read the locals assigned at `:2180-2181` from `sess_dict = model_to_dict(stored)` (`:2170`), and `model_dump()` recurses to plain dicts. Same for `$S/llm.py:969` (dump-derived) and all six `$S/db.py:1022-1035` reads (raw ck.db JSON, never the model). **That asymmetry is the diagnostic signature**: export keeps working while Step 5 becomes unreachable, so it presents as "the objective vanished from the UI but the exported bundle is fine."

### H1 — `_backfill_from_refined` clobbers the session and writes the loss to ck.db (severity: blocker, permanent data loss)

**Mechanism.** `$S/routers/wizard.py:347-351` computes `has_obj`/`has_steps` through the dead guards. Both go `False`, the early-out at `:352-353` never fires, and `:375-376` / `:379-380` replace step4 and step5 **wholesale** with `{objective|testScript, confirmed: True, backfilled: True}` — dropping `provenance`, `confirmed_at`, `stale` and legacy `step4.testScript`. `:390-395` then force-marks step1-3 `confirmed=True, backfilled=True`. `load_case` calls it unconditionally at `:648` and persists at `:656`. This is the **only** step4/step5 guard whose falsification gates a *write* (`not has_obj` / `not has_steps`) rather than a read — that inversion is the entire mechanism.

**Repro (executed by the adversarial pass over all 35 real rows, against a *copy* of ck.db).** Shipped code: fires on 8/35, **0 lose data**. Typed (naive commit 6): fires on **13/35**, **4 lose data** — `AWPTCM-T33233` (`confirmed_at`, `provenance` → null), `AWPTCM-T33234` (`provenance`, `step4.testScript`; objective **replaced**), `AWPTCM-T33373` (`confirmed_at`, `provenance`, `testScript`), `AWPTCM-T43851` (`provenance`, `testScript`; objective replaced). With `validate_assignment=True` it is non-idempotent **forever**: the objective becomes un-editable, reverted on every `load_case`.

**Two corrections to the hazard as filed:** it is **not** reproducible on shipped code (the filed repro "edit the objective, reload, the edit is gone" needs commit 6 first), and the blast radius is **4 sessions, not 43 cases** — 43 is the bundle count; 13 of 35 sessions have a bundle; 5 of those have a non-empty objective.

**Mitigation.** ck.db is the permanent, never-rebuilt source of truth, so this is unrecoverable. Fix the guards *in the same commit*; add a regression test asserting `_backfill_from_refined(WizardSession(**db.load_session('wizard','AWPTCM-T33233')))` is `False`; and separately make `_load_persisted` refuse to overwrite on validation failure.

### H2 — Step 5 becomes unreachable after any server restart (severity: blocker)

**Mechanism.** `_session_objective` (`$S/routers/wizard.py:246-251`) hits the dead guard at `:249` and returns `""` → `_session_has_objective` `False` → `_can_synthesize_steps` `False` → `POST /synthesize_steps` 400s at `$S/routers/wizard.py:1991-1995` "No objective on session. Complete Step 4 first." No exception, no log; the objective is sitting in ck.db the whole time.

**Repro (executed E2E through the real endpoint, real ck.db row, server pointed at a copy).** `AWPTCM-T30649` (objective_len 1307, step1-3 all confirmed). Untyped control: `POST /api/wizard/synthesize_steps` → **200**, `_session_objective` → `'<ul>\n<li>DHCPv6 server address-range…'`. Typed, `va=False`: → **400 "No objective on session"**, `_session_objective` → `''`. Aggravator: `SynthesisRequest.session` is `WizardSession` (`$S/models.py:193`), so `req.session.step4` is a `Step4` too — `isinstance(req.session.step4, dict)` at `:1999` is `False` **and** the `elif isinstance(req.session, dict)` fallback at `:2001-2002` was already dead code, so the user cannot even work around the 400 by re-POSTing the objective the browser still holds.

**Note the filed evidence cited "wizard.py:2988-2992" for the raise — wrong; the file is 2515 lines and the raise is at `:1991-1995`. `AWPTCM-T33233` as a repro key is also wrong (step1-3 `confirmed=False`, so it fails the earlier `_can_synthesize` gate at `:1986-1990`); use `AWPTCM-T30649` or `AWPTCM-T33373`.**

**Mitigation.** Rewrite all nine guards + eight `or {}` sites to be model-aware, in the same commit as the typing — or route every read through one normalizing accessor `def _s4(sess) -> dict: return models.model_to_dict(sess.step4)`. **Every existing test builds the session by assignment, which (at `va=False`) leaves a plain dict and cannot see this.** The invariant test must construct via `WizardSession(**db.load_session(...))`.

### H3 — the `stale` invalidation cascade goes dead: regression of an explicitly-fixed export-contradiction bug (severity: blocker)

**Mechanism.** `_invalidate_downstream` (`$S/routers/wizard.py:285-306`) reads through the dead guards at `:296`/`:301`, so `s4.get("objective") and s4.get("confirmed")` is `False` and `stale` is **never written**. `$S/static/js/generator.js:163,185` read exactly that key to render "⚠ Stale — selections changed"; absent, `objConf` at `:164` wins and the badges read "✓ Confirmed" / "✓ Ready". `export()` gates only on `_can_synthesize` (steps 1-3) at `$S/routers/wizard.py:2146` — there is no step4-stale check — so the contradictory bundle reaches disk. That is verbatim the bug the comment at `$S/routers/wizard.py:1568-1577` says was fixed: *"export a bundle whose zephyr_payload.json (old generation) contradicted its own traceability.md (new selections)"*. `wizard.py:298` and `:303` are the **only** writers of `stale`; nothing else can set it.

**Repro (executed against the real `_invalidate_downstream`).** Untyped: `{'step4': True, 'step5': True}`, `stale: True` on both. Typed: `{'step4': False, 'step5': False}`, `getattr(step4,'stale')` → MISSING, `step4.confirmed` still `True`, badges render "✓ Confirmed" / "✓ Ready".

**Correction: this half is NOT silent.** `$R/tests/test_export_authority_batch_a.py:277-282,331` subscript the field (`s.step4["stale"]`, `body["session"]["step4"]["stale"]`), which raises `TypeError` against a model — the backend suite fails loudly, so commit 6 cannot ship this undetected. `$R/js-tests/stale-badges.spec.js` re-implements `badge4For` locally (spec lines 27-38) and keeps passing green, so the **frontend layer gives no signal at all.** Also note `tests/…:291` `assert "stale" not in s.step4` passes **vacuously** on a model.

**The genuinely silent half (H4) is separate.**

### H4 — `extra="ignore"` (the pydantic default) silently drops `stale`, defeating the H3 fix (severity: high, fully silent)

**Mechanism.** `stale` is in **0 of 35** ck.db rows **and 0 of 2** on-disk bundles, so any model derived from the data omits it. Probed: with default `extra="ignore"`, `Step4(**{**raw, "stale": True})` **succeeds** and dumps without the key. `invalidated` reports `True`, the API returns 200, the badge still reads "✓ Confirmed", no error, no log. Fixing the isinstance guards is therefore **not sufficient**.

**Repro.** `Step4(**{"objective":"o","future_key":1}).model_dump()` → `{'objective': 'o'}` under `extra="ignore"`; `{'objective': 'o', 'future_key': 1}` under `"allow"`.

**Mitigation.** `extra="allow"` on all four models **and** declare `stale: bool = False` on both `Step4` and `Step5`. Same applies to `objective_used` (`$S/llm.py:1010`) and PT's `invalidated_at` (`$S/routers/pytest_create.py:364`) — three undeclared keys that exist only in code, not in data.

### H5 — a naive edit of "all four `stepN: Dict[str, Any]` lines" breaks every PyTest Creator confirm with `TypeError` (severity: blocker, avoidable by scope)

**Mechanism.** `PtSession` declares the same two field names at `$S/models.py:183,184` with completely unrelated shapes (step4 = `{decision,…}`, marked **RETIRED** at `$S/models.py:169-170`; step5 = `{fragments, selected, dropped, accounting, confirmed, selections_fingerprint, provenance}`). `_confirm` mutates the field object **in place**: `$S/routers/pytest_create.py:351-354` `step = getattr(sess, step_key) or {}` → `step["confirmed"] = True` → `setattr(...)`, reached through a generic loop over `STEP_KEYS` (`$S/routers/pytest_create.py:51`) that includes `"step4"` and `"step5"`. `_invalidate_from` (`:361-365`) does the same. Probed: `Step4()["confirmed"] = True` → `TypeError: 'Step4' object does not support item assignment`.

Second PT casualty: `'selected' not in step5` (`$S/routers/pytest_create.py:579`, duplicated at `$R/tool/pt_grade.py:101`) is a **load-bearing membership test** distinguishing "key absent → legacy, treat the whole pool as selected" from "present but empty → nothing selected". A typed model always has the attribute, so that back-compat branch dies silently.

**Mitigation.** Keep `PtSession` entirely out of scope. Touch only `$S/models.py:150` and `:154`.

### H6 — every wizard case flips to "in progress" in `/cases` (severity: medium, cosmetic but user-visible)

**Mechanism.** `$S/db.py:1029` `has_step4 = bool(s4) or has_obj` is the **one** site that depends on step4 being exactly `{}` / falsy. Probed: an all-defaults `Step4().model_dump()` → `{'objective': None, 'provenance': None, 'confirmed': False, 'confirmed_at': None, 'testScript': None, 'backfilled': False, 'stale': False}` → `bool(...)` **`True`**. `load_case` persists unconditionally (`$S/routers/wizard.py:656`), so the first cold load of each of the **28** empty-step4 sessions writes a dict of nulls into ck.db and `has_step4` becomes `True` for all 35. `$S/db.py:1031` then admits every row into the progress map, and `$S/routers/wizard.py:931-933` labels them `[has draft]` / `[synth done]`.

**Mitigation.** Derive it from content — `has_step4 = has_obj or has_steps` — or dump with `exclude_defaults=True`. Probed: `Step4().model_dump(exclude_defaults=True)` → `{}` → falsy, and a genuinely-set `stale=True` still survives it. Caution: applying `exclude_defaults` at the `safe_session_dict` level would also strip `step1-3` defaults, a wider change than intended; prefer fixing `db.py:1029`.

### Explicitly refuted — do not re-raise

- **"Mixed dict/model state → `AttributeError` 500 on `/synthesize_objectives`."** Unreachable as stated. `dict(model)` works in pydantic v2 (probed: `dict(Step4(objective='o'))` → full dict), so the five `dict(stored.step4 or {})` mutation sites do not raise. **Residual real issue (medium):** on a cold load the guards at `:311, :312, :1850` collapse to `{}`, so `_migrate_legacy_step4_to_step5` no-ops and `:1851`'s wholesale replacement short-circuits the `testScript` carry-over — `AWPTCM-T43851`'s 5-step legacy testScript is destroyed in **both** locations and `_persist_session` at `:1870` writes the loss. Plus a latent warm-cache clobber: the `:312` guard makes the migration fire even when step5 already has a testScript, reassigning `sess.step5 = {"testScript": …}` and dropping other keys — exposed on `AWPTCM-T33234` and `AWPTCM-T33373`, harmless today only because their step4/step5 testScripts were verified byte-identical and step5 holds nothing else. Both are instances of H1/H2's root cause, not a separate class.
- **"`validate_assignment=False` → non-dict persisted → session 404s forever."** Refuted on both counts. Pre-existing with **zero delta**: it reproduces identically on today's `step4: Dict[str, Any]` (`[type=dict_type]` instead of `[type=model_type]`). And "404s forever" is false — `load_case` treats `_load_persisted() → None` as "no session yet" (`$S/routers/wizard.py:636,639`) and the next upsert overwrites the poisoned row (`$S/db.py:958-965`); no manual row deletion is needed. Residual: silent single-case data loss with a 200 response and only a `log.warning` at `$S/routers/wizard.py:217` — worth fixing, but it is not a reason to slow commit 6 down. Useful side note: it *is* an argument for turning `validate_assignment=True` on while you are in there.

I consider both refutations sound; each was executed, not reasoned.

---

## 4. Blast radius

**Backend — Python sites** (my counts, `grep -cE 'step4|step5'`):

| file | raw hits | of which need changing (wizard scope) | why |
|---|---|---|---|
| `$S/models.py` | 10 | **2** (`:150`, `:154`) + the docstring at `:148-156` | the declarations; `:183,184` are PtSession → out of scope |
| `$S/routers/wizard.py` | 62 (**32** are `.step4`/`.step5` attribute accesses) | **32** — 15 writes (`:298,303,314,375,380,1851,1907,1935,1964,1968,2006,2025,2035,2070,2077`), 8 `or {}` (`:248,1857,1893,1925,1960,1966,2004,2030`), 9 dead guards (`:249,296,301,311,312,347,348,1850,1999`) | attribute-vs-item access + isinstance |
| `$S/db.py` | 6 | **1** (`:1029`) | all six read RAW ck.db JSON, never the model; only `has_step4` is semantically wrong |
| `$S/llm.py` | 8 | **0** | `:956,957,967,969,1039` all operate on the `model_to_dict` dump |
| `$S/routers/pytest_create.py` | 23 | **0** if PtSession stays untyped; **6+ break hard** if not (`:351,354,361,365,442,579,1947`) | H5 |
| `$R/tool/pt_grade.py` | 13 | **0** | reads the raw ck.db payload (`:99-103,499-501,547`) |

**→ 35 backend sites need editing (2 + 32 + 1), all in 3 files. 44 further sites are provably safe** (`db.py` ×5, `llm.py` ×8, `pytest_create.py` ×23, `pt_grade.py` ×13 — minus overlap) **because they read dumps or raw JSON, not the model.**

**Frontend — 24 raw hits across 4 files**, of which **0 need changing** and **12 are behavioural dependencies**:
- `$S/static/js/generator.js` — 16 hits: **12 real session reads** (`:162,163,164,185,226,227,233,244,245,285,286,533`), plus `:165,186` = DOM element ids, `:577` = the `invalidated` response dict, `:756` = a comment. Every read is `s.step4 && s.step4.x` on JSON, so explicit nulls are tolerated; a **dropped `stale`** is not (H4).
- `$S/static/index.html` — 2 hits, both DOM ids (`:445,471`). No change.
- `$S/static/js/nav.js` — 1 hit, a comment (`:104`). No change.
- `$S/static/js/pytest.js` — 5 hits, all **PT** step5 (`:597,600,607,632,645`). No change if PT is out of scope.

**Templates — 0.** `grep -rn 'step4|step5' $S/templates/` → 0 hits.

**Tests — 5 files, 2 in wizard scope:**
- `$R/tests/test_export_authority_batch_a.py` — **24 hits, 9 of 20 test functions**: `test_changed_selections_invalidate_downstream`, `test_unchanged_selections_preserve_downstream`, `test_backfill_marks_reviews_confirmed`, `test_backfill_noop_leaves_gate_closed`, `test_confirm_step_endpoint_invalidates`, `test_confirm_step_endpoint_no_change_preserves`, `test_reconfirm_objective_clears_stale`, `test_export_blocked_when_reviews_unconfirmed`, `test_export_rejects_client_supplied_session`, plus a module-level fixture at `:88-92`. **7 assertions break outright** — `:224` `sess.step4.get("objective")` → `AttributeError`; `:277,278,279,281,282,290` subscript → `TypeError`; `:291` and `:355` `"stale" not in s.step4` pass **vacuously**. `:131-132,268-269,351` build by assignment and therefore mask H2 entirely.
- `$R/js-tests/stale-badges.spec.js` — 15 hits, **11 `it()` blocks**, all against a local re-implementation of the badge logic. **Passes green through every hazard in §3** — zero signal.
- Out of wizard scope: `$R/tests/test_pt_grade.py` (7), `$R/tests/test_pt_step_labels.py` (9) — PT; `$R/tests/test_pydantic_v2_and_logging.py` (1) — a comment at `:291`.
- `$R/e2e/` — **0 hits.**

**On-disk artefacts — 45 files under `$D`:**
- **43** `zephyr_payload.json` — read back by `_backfill_from_refined` (`$S/routers/wizard.py:359-380`) **and** by PyTest Creator (`$S/routers/pytest_create.py:641-667`). Not written by commit 6, but they are the input side of H1.
- **2** `*-session.json` (T33233, T33373) — written by export (`$S/routers/wizard.py:2319`, `:2403`), read by **nothing** (grep across all `*.py`). A shape change here is invisible to code; only a human diffing artefacts would notice.

**ck.db rows at risk — 35 wizard** (28 empty step4 → all flip `has_step4` per H6; **4 measurably lose data** per H1: T33233, T33234, T33373, T43851) **+ 3 PT** (only if H5's scope error is made). ck.db is git-LFS-tracked, built once, never rebuilt — there is no rollback for a bad write.

---

## 5. Recommended commit split

**Commit 6 is not safe as one commit, and — more pointedly — it is not safe as an *annotation change* at all in its current form.**

The framing "non-behavioural first step: models only, `extra='allow'`, no serialization change" **does not work**, and this is the single most important finding for the split decision. Flipping `$S/models.py:150,154` to `Step4`/`Step5` is behavioural **the instant it lands**, whatever `validate_assignment` says, because `WizardSession(**raw)` at `$S/routers/wizard.py:213` validates on construction. That one line detonates H1, H2 and H3 on the next server restart. With `va=False` you get the *same* breakage plus non-determinism (the field silently de-types back to a plain dict on the first raw-dict assignment) and `PydanticSerializationUnexpectedValue` warning noise on every dump. There is no configuration of the annotation flip that is behaviour-neutral.

### Recommended: reduce commit 6 to validators at the boundary (1 commit, genuinely zero behaviour delta)

Add `TestStep` / `TestScript` (and, if you like, `Step4` / `Step5`) to `$S/models.py`, and **leave `$S/models.py:150,154` as `Dict[str, Any]`.** Use `TestScript` only where untrusted JSON crosses into the session, immediately `.model_dump()`-ing back to a dict:
- `$S/routers/wizard.py:378-380` — `_backfill_from_refined`, where on-disk bundle content enters step5 completely unvalidated today;
- `$S/routers/wizard.py:1954-1959` — `save_steps`, which accepts any client list with only an `isinstance(list)` check.

This captures the **only** real safety win available (catching a malformed on-disk or client payload) for a fraction of the blast radius: **0 dead guards, 0 mutation-site rewrites, 0 serialization change, 0 test rewrites, 0 ck.db risk.** It also matches the conclusion the plan already reached independently at `$R/ask-ck/ck-facelift/PLAN-backend-module-split.md:652-658`, which says *"Recommendation: do NOT do commit 6 as written… reduce it to using TestScript/TestStep as validators at the backfill boundary."* Note the plan's own justification for the benefit being thin holds up under this survey: `provenance` is inert and stays a dict either way, and `testScript` is already **350/350** uniform in practice.

### If the user wants typed fields anyway: four commits, in this order

1. **`test(models): pin the persisted step4/step5 shape`** — production code untouched. A test that runs `WizardSession(**raw)` over every `kind='wizard'` ck.db row (read-only connection) against the *candidate* models, plus a test that constructs via `WizardSession(**db.load_session(...))` — **not** by assignment — and asserts `_session_objective`, `_invalidate_downstream`, `_migrate_legacy_step4_to_step5` and `_backfill_from_refined` all still behave. This commit is what makes the next three reviewable. **It has not been done and it is the single highest-value verification available.**
2. **`refactor(wizard): route all step4/step5 access through one accessor`** — fields **still** `Dict[str, Any]`. Replace the 9 dead-guard sites and 8 `or {}` sites with one `_s4(sess)/_s5(sess)` helper, and convert the 15 raw-dict assignments to go through a single writer. Provably behaviour-preserving on dicts, mechanically verifiable by grep, and it removes the entire H1/H2/H3 class **before** the type exists. Fix `$S/db.py:1029` here too (H6).
3. **`refactor(models): type step4/step5`** — flip `$S/models.py:150,154` with `extra="allow"`, `validate_assignment=True`, `stale` declared, `confirmed_at` still `str`, `default_factory`. Now a small, revertable diff. Update `$R/tests/test_export_authority_batch_a.py` (9 test functions, 7 assertions) in the same commit.
4. **`refactor(models): unify step4/step5 confirmed_at on UtcDatetime`** — separate, because it changes the wire format of a published artefact (`$D/**/*-session.json`). Zero code readers exist, so the risk is entirely artefact-diff, not runtime.

Do **not** collapse 2 and 3. Step 2 is the whole safety margin.

### PtSession step2-8: explicitly OUT of scope

Four reasons, all verified: (a) `$S/routers/pytest_create.py:351-354,361-365` mutate the field object in place via item assignment, reached through a generic `STEP_KEYS` loop (`:51`) that includes `step4` and `step5` → `TypeError` on every PyTest Creator confirm (H5); (b) `'selected' not in step5` (`:579`, duplicated at `$R/tool/pt_grade.py:101`) is load-bearing back-compat that a typed model destroys silently; (c) PT `step4` is documented **RETIRED** at `$S/models.py:169-170` and is read in exactly one place (`$R/tool/pt_grade.py:547`); (d) PT `step5` shares nothing with wizard `step5` but the field name and `confirmed`/`provenance`. **Whoever writes the diff must edit `$S/models.py:150` and `:154` by line, never by pattern** — `stepN: Dict[str, Any] = {}` matches nine lines in that file, seven of them PtSession's.

---

## 6. What I could NOT verify

Blunt and complete. Everything here is a gap the next engineer inherits.

1. **I did not run the test suite.** Every claim about `$R/tests/*` breaking is from reading source (`test_export_authority_batch_a.py:131-132, 224, 268-291, 331-355`) and from probing pydantic subscript behaviour separately — **not** from a run. The adversarial pass reports `393 passed in 5.24s` with typed step4/step5 monkeypatched in; I did not reproduce that and cannot vouch for it. The "9 of 20 test functions" figure is a static attribution of `step4|step5` grep hits to enclosing `def test_`, not a measured failure list.
2. **No candidate model has been loaded against all 35 real ck.db rows.** This is the highest-value verification available and it has **not** been done as part of the actual commit. It matters more than usual because `$S/routers/wizard.py:213` swallows `ValidationError` into a bare `except Exception` → `None`, and `:656` then unconditionally upserts an empty session over the row. One row that fails the new model loses its objective, testScript and provenance permanently, with nothing but a `log.warning` at `:217`. Concrete null shapes that a non-`Optional` field would reject, all present in live data: `step4.testScript = null`, `step4.confirmed_at = null`, `provenance.provider = null`, `provenance.auth_method = null`.
3. **The frontend survey dimension I was handed was truncated mid-sentence** (it cuts off inside the `generator.js:285` entry). I re-derived the frontend site inventory myself by grep (24 hits / 4 files / 12 real reads) and read `generator.js:162-165, 184-186, 226-233, 244-245, 273-286, 533, 575-580`. I did **not** audit the rest of `generator.js`, nor `pytest.js` beyond confirming its 5 hits are PT-only, nor the full badge/DOM logic, nor `provenance.js`'s POST body construction beyond the survey's claim about it.
4. **I did not read the 43 `zephyr_payload.json` files individually** — I aggregated them programmatically (`scratchpad/ondisk2.py`). The 276/276 `{description, expectedResult}` figure is a key-frequency count, so a payload with an *extra* per-step key would show up, but I did not eyeball content, HTML validity, or encoding.
5. **The provenance provenance is unknown.** I confirmed current code (`$S/llm.py:925-933, 1007-1016, 1051-1055`) emits neither the 4-key `{source, note, provider, auth_method}` shape nor a shape carrying both `objective_prompt` and `steps_prompt`, and I found both in live data (ck.db and on disk). **I cannot say which commit wrote either, or whether more generations exist that neither population happens to contain.** The `stale` and `objective_used` cases prove the key inventory is code-dependent, not data-derivable — so treat the key list as provisional, permanently.
6. **`$R/tool/upload_refined.py`** (shelled out by `push_to_zephyr`) reads on-disk `zephyr_payload.json` rather than step4/step5, so I treated it as out of scope and **did not read it**. If any variant of commit 6 changes the exported payload shape, check it separately.
7. **I did not verify the pydantic-2.13.4 semantics table against any other pydantic version.** Everything in §2 was probed on exactly `pydantic 2.13.4 / Python 3.13.14` in `$R/.venv`. A dependency bump could invalidate the `extra=`, `validate_assignment`, `bool(model)` and mutable-default-copy findings.
8. **`_can_synthesize_steps` and `_session_has_objective`** contain no direct step4/step5 access — both go through `_session_objective` (`$S/routers/wizard.py:246-251`), which is the single reader. `validate_zephyr_payload` and `build_traceability_note` likewise never touch step4/step5 directly; `build_traceability_note` ignores its `session` argument entirely (`$S/llm.py:725-726`). Verified by reading, not by execution.
9. **I did not test the export path end-to-end under a typed model.** My claim that `$S/routers/wizard.py:2219, 2220, 2241` stay safe rests on `model_dump()` recursing to plain dicts (documented behaviour + the survey's probe that `model_to_dict` deep-copies), not on an executed export. The consequence if I am wrong is worse, not better: the placeholder objective `"<ul><li>Objective not yet synthesized</li></ul>"` would enter the bundle and then be caught by `validate_zephyr_payload`'s ≥3-`<li>` rule at `$S/llm.py:760` — loud, by luck rather than design.
10. **No Playwright / browser run** (prohibited, and the user's standing preference is manual UI testing). Every frontend claim is static reading. In particular, **the frontend consequences of H2/H3/H4 have not been observed in a browser** — only inferred from `generator.js:162-164, 185`.
11. **`$D` counts are as of this session.** Another stream edits this repo concurrently (see the shared-tree memory note); 43/2 could change under you. Re-run `find $D -name 'zephyr_payload.json' | wc -l` before relying on the number.