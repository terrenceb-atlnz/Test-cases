# PLAN — The frame binds a ROLE SET (tb / copper / fibre / cusfp), not two booleans

> ## Status (read first)
>
> **APPROVED 2026-09-21, IN PROGRESS.** The last deferred T33234 repair (memory `frame-binds-two-roles-only`,
> three-layer diagnosis). Decisions taken with Terrence 2026-09-21: `cusfp` is a first-class role + profile;
> pluggable roles (fibre, cusfp) are OPTIONAL-with-UNSUPPORTED while tb/copper abort; handles are
> `portFibre`/`fibre_peer.portDut` and `portCuSfp`/`cusfp_peer.portDut`, copper keeps `peer`/`portPeer`/`portDut`.
>
> Progress: step 1 vocabulary + preflight ☐ · step 2 detection + frame + prompts ☐ · step 3 docs/wrap ☐


## Context

The generated frame (`pt_script_template.py.jinja`) can bind exactly two links: `links.tb`
(`dut.portA <-> tb.ethA`) and `links.peer` (`dut.portPeer <-> peer.portDut`, media role
`copper` OR `fibre` via `_detect_link_role`). `_detect_links()` returns `{"tb": bool, "peer":
bool}`; TOPOLOGY-PROFILES.md collapses `copper`/`fibre` onto ONE handle set; there is no
`cusfp` (copper-SFP) role anywhere — not in `pt_profiles.PROFILES`, not in
`pt_media.ROLE_REQUIRES`, not in the spec table.

AWPTCM-T33234 needs four links at once (`tb`, `copper`, `cusfp`, `fibre`). The frame emitted
two, so the `setup` UNIT invented the rest and bound the copper test port from the `tb` role (a
testbox NIC) while every copper case asserted against `peer.portDut`: 4 of the first review's 6
highs were this one gap (memory `frame-binds-two-roles-only`, three-layer diagnosis verified
2026-09-17). The hand repair introduced `portFibre`/`fibre_peer`, `portCuSfp`/`cusfp_peer`,
`assert_media=False` binding for pluggable roles, `<role>_supported` flags and an
`assert_role_media_now()` helper — all of which the frame should own. Two latent bugs found
while planning: the saved script calls `assert_role_media(..., 'cusfp')`, which the shipped
`ck_media` REFUSES as an unknown role (would abort at step 16 on the bench); and
`pt_preflight` cannot read `_ck_bind_link` call sites, so every ART-frame script gets
"LINK role None" problems and an un-runnable verdict (seen today on T33234).

Constraints: `/home/st-art/framework` is not on this host (framework `init_swi` idempotence is
unknown — the frame must not call it twice for the same far device); every `CK_server/*.py`
save reloads production; tb470 currently declares NO `ck_link_*` (profile deliberately empty —
Terrence's decision, untouched by this work); gate `./ask-ck/tools/run_tests.sh`.

## Decisions (Terrence, 2026-09-21)

- **Roles:** `tb`, `copper`, `fibre`, `cusfp` — any subset per case. `cusfp` becomes a
  profile + media role (`TWISTED_PAIR`, like copper: a copper SFP's `Type` reads `1000BASE-T`).
- **Handles (fixed per role):** DUT side `portA` (tb), `portPeer` (copper), `portFibre` (fibre),
  `portCuSfp` (cusfp); far side `tb.ethA`, `peer.portDut`, `fibre_peer.portDut`,
  `cusfp_peer.portDut`. `peer`/`portPeer`/`portDut` keep today's names so every prompt rule,
  test and existing script stays valid.
- **Pluggable roles are optional-with-UNSUPPORTED; core roles abort.** `fibre`/`cusfp` bind by
  port reference (`assert_media=False`), set `self.fibre_supported` / `self.cusfp_supported`,
  and a bench without the role sets the flag False (handles None) instead of aborting; the
  insertion case asserts media with `assert_role_media_now()` and reports UNSUPPORTED
  (`self.supported = False`) when the flag is off. `tb`/`copper` missing → abort, as today.

## Changes

### 1. Role detection → a set (`pytest_create.py`)
- `_detect_links(sequence, fragments, objective)` returns `{"tb", "copper", "fibre", "cusfp": bool}`.
  `copper` = today's `peer` predicate (partner / polarity / speed / duplex …) unless the case is
  fibre-only; `fibre` = `_FIBRE_HINT_RX` or any step `claim.cable == "fibre"`; `cusfp` = a new
  `_CUSFP_HINT_RX` (`copper SFP`, `SFP-T`, `1000BASE-T SFP`, `copper pluggable`, `RJ-45 SFP`) or
  a step whose action names inserting a copper SFP. Slice-C claims are the deterministic input
  when present; text hints stay as the fallback. Keep `peer` as a derived alias
  (`copper or fibre or cusfp`) for the two callers that only need "is there a neighbour".
- `_detect_link_role` retires into the set (kept as a thin wrapper returning `'fibre'` when
  fibre and not copper, for any external caller).

### 2. The frame (`templates/pt_script_template.py.jinja`)
- `_ck_bind_link(self, setup, dut, misc, role, assert_media=True)`: T33234's signature. Far
  devices cached per key (`self._ck_far = {}`) so two links to the same partner never call
  `setup.init_swi(far_key)` twice; the media assertion is skipped when `assert_media=False`
  (logged "media check DEFERRED to the insertion case").
- Module-level `assert_role_media_now(testCase, dut, port, role)` emitted in the frame (the
  T33234 helper) — `passed()`/`failed()` verdict, returns ok.
- `init()`: one block per role in the set. `tb` and `copper` as today (hard abort). `fibre`
  and `cusfp` in `try/except RuntimeError` → `self.<role>_supported`, `dut.port<Role>`,
  `self.<role>_peer` (None on failure) with the T33234 comment explaining why the suite
  continues. `dropped_switches` note unchanged.
- `shortcuts(via)` macro emits per bound role: `portFibre = dut.portFibre`, `fibre_peer =
  via.fibre_peer`, `portCuSfp = …`, `cusfp_peer = …`. `phys_port` picks `portA` if tb, else
  the first bound peer-side port.
- `_skeleton_bound_ports` already reads any number of `_ck_bind_link` calls (rehome handles
  `X.portDut = local`); `_skeleton_bound_devices` gains the `*_peer` names.

### 3. Vocabulary + spec + media + preflight
- `ask-ck/tools/pt_profiles.py`: `"cusfp": Profile(links=("cusfp",), media={"cusfp": "port"},
  summary=copper-SFP link for pluggable insertion tests)`. Spec table row in
  TOPOLOGY-PROFILES.md (`test_spec_table_and_code_list_the_same_profiles` enforces) and a new
  row in "How the generated frame binds these" for each role; a paragraph on optional
  pluggable roles.
- `ask-ck/tools/pt_media.py`: `ROLE_REQUIRES["cusfp"] = (TWISTED_PAIR,)` (fixes the latent
  refusal in T33234's saved script). Test in `tests/test_pt_media.py`.
- `ask-ck/tools/pt_preflight.py`: `parse_script` also reads `self._ck_bind_link(setup, <dut>,
  misc, '<role>')` call sites as a `LinkDemand` on `ck_link_<role>` (role literal), and
  `check()` resolves it against the bench's `[misc] ck_link_<role>` → declared portlink. The
  `init_portlink(dut, far, …)` calls INSIDE the helper are skipped (they are the helper's body,
  not demands). Verdict text names the missing `ck_link_<role>`.

### 4. Prompts
- `pt_generate_step.jinja` link section: role-aware wording for `fibre` / `cusfp` (pluggable:
  "may be None on a bench without it — check `self.testSet.<role>_supported` and report
  UNSUPPORTED via `self.supported = False`"). `pt_fill_rules.jinja` rule 3: the new handles and
  the `<role>_supported` idiom; the `_ck_bind_link`-only rule unchanged.

### 5. Tests
- `tests/test_pt_art_shape.py`: detection tests move to the set shape; new: a 4-role sequence
  renders four bind calls with the fixed handles, the shortcut block carries them, pluggable
  roles are `try/except`-bound with flags, the frame compiles for every role subset (16), one
  far device bound once for two links (source check on the cache).
- New `tests/test_pt_role_set.py` for detection from claims (`claim.cable == 'fibre'` binds
  fibre; a copper-SFP insertion step binds cusfp) and the `peer` alias.
- `tests/test_pt_profiles.py` (cusfp row/code), `tests/test_pt_media.py` (cusfp accepts
  `1000BASE-T`, rejects fibre), `tests/test_pt_preflight.py` (an ART-frame script with
  `_ck_bind_link(..., 'copper')` is runnable against a bench declaring `ck_link_copper`, and
  un-runnable naming the role when it does not).

### 6. Docs, memory, wrap
- SERVER-README (frame section), TOPOLOGY-PROFILES.md, CHANGELOG (why), PROGRESS, SESSION_STATE.
- Memory `frame-binds-two-roles-only`: the frame part → SHIPPED; index line. Keep the diagnosis.

## Order
1. vocabulary (profiles, media, spec row) + preflight — one commit.
2. detection + frame + prompts + tests — one backend save, one commit.
3. docs/memory wrap.

## Verification
- Gate before/after each commit (known red: zephyr corpus floor only, now that preflight is re-aimed).
- Offline: render the frame for T33234's real sequence (from its session, read-only) and diff
  the four bind blocks against the hand-repaired `test-9000.33234.py` init(); `pt_preflight`
  on that script now reports the four `ck_link_*` roles by name instead of "role None".
- Manual for Terrence (no bench change): on a scratch copy of a Port case, Extract → Generate
  → the setup unit's prompt lists the four handles; the generated `init()` needs no hand edit.
