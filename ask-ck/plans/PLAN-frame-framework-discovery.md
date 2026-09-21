# PLAN — The frame discovers its topology through the framework, never `[misc]`

> ## Status (read first)
>
> **APPROVED 2026-09-21 (Terrence), IN PROGRESS.** Replaces `PLAN-frame-role-set.md` (reverted
> the same day: `b96255c`, `f354f14`) and retires the `[misc]` role contract of
> `TOPOLOGY-PROFILES.md` (2026-07-30) and `pt_profiles.py`.
>
> Progress: step 1 frame + detection + prompts + lint ☐ · step 2 preflight + retire profiles ☐ ·
> step 3 spec + docs + memory ☐

## Terrence's ruling (2026-09-21)

> "I dont want the [misc] section to be callable as a workaround for not using the existing
> framework commands. We have a suite of 'show' commands that identify whatever we need to, the
> information shouldnt require pre-loading variables to know it."

Two corrections that led there, both verified against the 827-script corpus in `ck.db`:

1. **`swi_a`, `swi_b`, `stk_a` ARE the framework's portable role vocabulary.** `init_swi('swi_a')`
   297 uses, `init_swi('swi_b')` 168, `init_stk('stk_a')` 192; a role-named lookup such as
   `init_swi('dutA')` appears **zero** times (`dutA`, `swiSrc`, `tb` are script-local variables).
   Every bench maps those slots to its own hardware, so `init_swi('swi_b')` is not bench-specific.
   `ck_role_dut` duplicated this.
2. **Media is a fact the device reports**, with `show system pluggable` / `show interface <port>
   status`, which `pt_media.py` already parses. `ck_link_<role>` pre-declared what one show
   command answers, and could go stale the moment someone swapped a module.

The only real gap the old layer covered — two cables of different media between the same
device pair — is closed by asking the device which is which, not by tagging the file.

## How the framework already identifies the partner (evidence)

From `raw-data/test_scripts/5712_Release_Testing_Transceivers/` (the framework's own pluggable
suite) and the ART corpus:

| need | framework call | corpus uses |
|---|---|---|
| the DUT | `setup.init_swi('swi_a')`, `setup.init_stk('stk_a')` | 297 / 192 |
| the DUT's stack, if any | `swi.get_stack()` (None when standalone), `stack.all_members()` | 270 / 139 |
| every cable on a device | `dev.get_all_port_links()` → `{far_device: [(local_port, far_port), …]}` | 38 |
| the testbox among them | `isinstance(far, ATTestBox.TestBox)` | `library_5712._get_swi_tb_link` |
| the media in a port | `show interface <port> status` (Type column), `show system pluggable` | 34 scripts |

So a **link partner is any device with a `[portlink]` to the DUT that is not the testbox and not
one of the DUT's own stack members.** It is not an explicit range. `sample.stack_and_peer.setup`
declares `stk_a = swi_a, swi_b`, a peer `swi_c`, and one line `swi_c-swi_b = port1.0.25-port2.0.25`;
`init_portlink(stk, swiDst)` finds it by walking the stack's members.

## Design

### The frame's `init()` (`pt_script_template.py.jinja`)

```python
def init(self, setup):
    tb  = setup.init_tb()
    dut = setup.init_swi('swi_a')                     # the framework's DUT slot
    stk = dut.get_stack()
    if stk is not None:                               # a stacked bench: ports belong to members,
        dut = setup.init_stk(stk.name)                # commands go to the master — bind the stack
    self.tb, self.dutA = tb, dut
    topo = self._ck_discover(dut)                     # one pass over dut.get_all_port_links()
    # one block per role the case needs — rendered from _detect_links(), fixed handles:
    (dut.portA, tb.ethA)              = self._ck_take(topo, 'tb')          # required
    (dut.portPeer, peer)              = self._ck_take(topo, 'copper')      # required
    (dut.portFibre, fibre_peer)       = self._ck_take(topo, 'fibre',  optional=True)
    (dut.portCuSfp, cusfp_peer)       = self._ck_take(topo, 'cusfp',  optional=True)
```

`_ck_discover(dut)` walks `dut.get_all_port_links()` once. For every `(local, far)` on a partner
that is not the testbox and not a stack member it runs `show interface <local> status` and
`show system pluggable`, and classifies the DUT-side port:

| role | DUT-side port |
|---|---|
| `tb` | the far device is the `TestBox`; no media requirement (`ROLE_REQUIRES['tb'] == ()`) |
| `copper` | `twisted_pair`, **fixed** port preferred, a copper-SFP link only if no fixed one is free |
| `cusfp` | `twisted_pair` **and** listed by `show system pluggable` (a module in a cage) |
| `fibre` | `fibre` |

Assignment order `tb → cusfp → fibre → copper`, one link per role, never shared, so a case that
needs both a copper test port and a copper-SFP cage (T33234) gets two different ports. Two roles
that land on the same far switch share one device object (`init_swi` once per partner).

`_ck_take(topo, role, optional=False)`: a required role with no matching link raises
`RuntimeError("BENCH PROBLEM …")` naming the DUT's discovered links; an optional role sets
`self.<role>_supported = False` and returns `(None, None)` (Terrence's optional-with-UNSUPPORTED
ruling of 2026-09-21 stands). The far switch's port is homed as `<peer>.portDut`, as today.

**No `init_portlink()` at all** — the tuples from `get_all_port_links()` already hold the port
objects (`library_5712._get_swi_tb_link` uses them directly), and choosing by media is what
`init_portlink`'s first-unused rule could not do. **No `get_all_misc()`.** No `ck_media.parse_link_ref`.

The module-level `assert_role_media_now(testCase, dut, port, role)` (the T33234 hand-repair
helper) stays in the frame for the insertion cases; `cusfp` is added to `pt_media.ROLE_REQUIRES`
(twisted pair) — the latent refusal found on 2026-09-21 is still real.

### Detection (`_detect_links`, router)

Returns the role set `{tb, copper, fibre, cusfp}` from the step wording and the slice-C `claim`s
(the reverted detection, minus its `misc` consequences). `peer` remains a derived alias.

### Lint (router `_lint_generated`)

Today: "a direct `init_portlink()` outside `_ck_bind_link` is an error". Becomes: a direct
`init_portlink()` / `init_swi()` / `init_stk()` in a **unit** (outside `TestSet.init`) is an
error — the frame owns binding — and a unit reading `.port<X>` the frame never bound is an
error, as now. `_skeleton_bound_ports` reads `_ck_take(..., '<role>')` call sites.

### Prompts

`pt_fill_rules.jinja` rule 3 and `pt_generate_step.jinja`: the handles are unchanged (`tb`,
`ethA`, `portA`, `peer`, `portPeer`, `peer.portDut`, `fibre_peer`, `portFibre`, `cusfp_peer`,
`portCuSfp`, `self.testSet.<role>_supported`); the wording "the bench's role contract" becomes
"discovered from the bench's `[portlink]`s and the DUT's own show output".

### Preflight (`pt_preflight.py`)

Reads `_ck_take(..., '<role>')` demands and checks what is knowable offline: the bench declares
a testbox↔DUT link when `tb` is demanded, and at least as many DUT↔partner `port` links as
partner roles demanded. **Media is not knowable offline** and the verdict says so: "N partner
links declared; which is copper/fibre/copper-SFP is read from the device at run time".
`--profile` and the `pt_profiles` import go.

### Retired

- `ask-ck/tools/pt_profiles.py`, `tests/test_pt_profiles.py` (deleted).
- `pt_media.parse_link_ref` (only the `misc` format used it).
- `TOPOLOGY-PROFILES.md` rewritten: what a bench must **cable**, how the frame **discovers** it,
  and the limitations. The `[misc]` block, the profile table and "Adding a profile" go; the
  2026-07-30 report block is dropped (it documented the retired checker).
- Memory `topology-profiles-contract` rewritten to the new truth; `frame-binds-two-roles-only`
  gets a closing note.
- tb470's `[misc] ck_profile / ck_role_dut / ck_cap_*` lines are **inert** from now on. They live
  in `device-testing`, Terrence's file; he edits them (his call, 2026-09-21).

## Decisions taken 2026-09-21

- Discover media from the device, not "bind first and assert in the test" (Terrence).
- Revert `e022e1c` + `6ada916` rather than rework forward (Terrence).
- DUT on a stacked bench = the stack that contains `swi_a` (ports belong to members and are
  declared per member in `[portlink]`; commands go to the master). Claude, from the bench file
  (`ck_role_dut = stk_a`) and `init_stk` 191/191 in stack suites.
- Empty cage at `init()`: **see open question below.**

## Empty cages — ruled 2026-09-21

Terrence: *"cages themselves arent 'fibre' or 'copper' cause theyre empty."* So discovery
classifies an empty cage as `absent` and **never** assigns it a media role. A pluggable role
(`fibre`, `cusfp`) is satisfied only by a link whose module is **fitted at `init()`**; otherwise
`self.<role>_supported = False` and the case reports UNSUPPORTED. Insertion steps therefore
start from a fitted module (remove, verify down, re-insert, verify up). Exposing an empty cage
as its own handle for "insert into an empty slot" cases is **not** built; it would be a new
role, and a new ask.

## Verification

- Gate before/after each step. Known red: zephyr corpus floor only.
- Render the frame for T33234's real sequence (session read-only): four `_ck_take` blocks,
  compiles, no `misc`, no `init_portlink`.
- `pt_preflight.py --setup tb470.setup.current` on the rendered frame: `tb` satisfiable (three
  testbox links), one partner (`swi_e`) with two `port` links → copper satisfiable, fibre/cusfp
  reported as "no third/fourth partner link declared" (optional roles, UNSUPPORTED at run time).
- Manual for Terrence: a scratch Port case → Extract → Generate; the setup prompt lists the
  handles; `init()` needs no hand edit. The saved T33234 script still carries the `misc`
  helper — regenerating it is a separate ask.
