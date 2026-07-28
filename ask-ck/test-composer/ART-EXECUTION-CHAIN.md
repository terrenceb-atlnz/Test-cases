# ART Execution Chain — how ATPyLib runs, in dependency order

> **Purpose.** Test Composer will automate execution of the PyTest files produced by
> PyTest Creator. To do that it must emulate (or directly reuse) ART's existing run
> infrastructure. This document is the ordered dependency chain of how a real ART run
> works — *first X so we can do Y* — from run-control config down to a single testset.
>
> **Status:** traced from the live framework on tb470 (`/home/st-art/framework/`,
> READ-ONLY — see [[testbox-framework-readonly]]) on 2026-07-21: `config_gen.py`,
> `Setup.py`, `runAll.py`, `runTestSuite.py`, `ATTestSet.py`, `ATTestCase.py`, plus a
> real 101-case run log. Where something is inferred rather than read, it says so.
>
> **Two entry points, and which one WE use.** ART can be driven two ways:
> - **Suite runner** (`runAll.py` → `runTestSuite.py`): the full batch orchestrator —
>   reads `<hostname>.cfg`, optionally loads firmware, runs whole suites, publishes to
>   a DB. This is the chain documented below in full.
> - **Direct single-script** (`sudo python3 test-<suite>.<set>.py -s <setup> -v`): runs
>   ONE testset against a setup file, no config.cfg, no DB publish. **This is what
>   PyTest Creator's `pt_exec.py` does today** (steps 6–9 below only). Test Composer
>   will likely stay on this direct path but may need to emulate parts of the suite
>   chain (build load, config-driven options) — hence documenting the whole thing.

---

## The chain, in dependency order

### 1. `configs/<hostname>.cfg` — run-control config (suite-runner path only)
- **What:** an INI file (Python `configparser`), one **section per test suite** found
  under the testbox dir, with run-control keys:
  `update` (git-pull latest scripts), `publish` (push results to DB), `norun`,
  **`noconf`** (skip the testset's setup/`configure()` + `tear_down()`),
  `include-tests` / `exclude-tests`, `device` (which console), `tftp-download` (push
  build + clear flash), `keep-gui-files`, `restore-licenses`.
- **Who builds it:** `framework/config_gen.py::makeDefaultConfig()`. Run
  `python3 framework/config_gen.py` → writes `configs/<hostname>.cfg` (default name
  `<hostname>.cfg`; refuses if it already exists). It auto-discovers suite dirs under
  the per-testbox dir and writes a default section for each.
- **Who reads it:** the suite runners `runAll.py` / `runTestSuite.py`, via
  `Setup.get_default_config_file(configDir, hostName)` → `configs/<hostname>.cfg`.
- **NOT read by** `ATTestSet` / `ATTestCase` (verified: `config.cfg` appears nowhere in
  those two modules). So a single-script run does not consult it.
- **Why first:** it decides *what* runs and *how* (which suites, which tests, whether to
  update/publish/skip-config). Everything downstream is gated by its options.

### 2. `configs/<hostname>.setup` — topology declaration
- **What:** declares the physical topology — the testboxes, stacks, switches, and the
  port links between them (`setup.init_tb()/init_stk()/init_swi()/init_portlink()`
  consume it). It defines the named devices (`swi_a`, `stk_a`, …) a testset addresses.
- **Who reads it:** `Setup.py` (parsed into `setup.setupDict` with `switches`/`stacks`
  keys), passed to every `TestSet.init(setup)`. Resolved via
  `Setup.get_default_setup_file(configDir, hostName)` → `configs/<hostname>.setup`, or
  the explicit `-s <file>` argument.
- **Why here:** a testset can't `init()` its devices without it. **This is the one hard
  dependency the DIRECT single-script path shares** (`-s <setup>`).
- **Full schema + a real worked example:**
  **[`ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`](../pytest-create/SETUP-FILE-REFERENCE.md)**
  — every section `Setup.py` parses, with `[stack]` (stack membership),
  `[configured_stackport]` (ports a test must never touch) and
  `[portlink] tb-swi_X = ethN-portA.B.C` (testbox NIC ↔ switch port cabling) called out,
  since those three are declared here and must never be inferred from case text.

### 3. (optional) Firmware build load — `-b <buildname>`
- **What:** `runAll.py` can download + install a firmware build before running
  (`download_build()` → `copyBuild.main()`; TFTP from `ATPYLIB_REMOTE_TFTP_DIR`,
  default `/net/awpbuild/tftpboot`). Gated by the `tftp-download` config option and the
  `-b` arg (`"no"` = use whatever build is currently loaded).
- **Why here:** if you want tests run against a specific build, the DUT must be flashed
  first. Heavyweight; skippable with `-b no`. **Out of scope for our direct path unless
  we choose to test a specific build.**

### 4. `runAll.py` — batch orchestrator (suite-runner path)
- **Sequence** (from its `__main__` + `main()`):
  1. Parse args: `-b build`, `-c config` (default `<hostname>.cfg`), `-s setup`
     (default `<hostname>.setup`), `-k` keep/no-git-sync, `-q` quit-on-fail,
     `-u` run-unsupported, `-v` verbose, `-d` database, `testSuiteNumber...`.
  2. (unless `-k`) git-pull the script repos per the `update` option.
  3. (if requested) `download_build()` to flash firmware (step 3).
  4. For each requested test suite: read its options from the config (`get_test_options`
     — resolves `include-tests`, `device`, `setup`, power-off, publish, etc.).
  5. Invoke **`runTestSuite.py`** per suite with the assembled options (it daemonises by
     default; `-N` to capture return codes).
- **Emulation note for Test Composer:** the valuable, reusable parts here are
  git-sync, build-load, and config→options resolution. For our generated single tests
  we can likely skip 2–3 and go straight to a `runTestSuite`-style launch.

### 5. `runTestSuite.py` — one suite → its testsets
- **Sequence:**
  1. Resolve the suite dir under the testbox dir; **glob `test-*.py`** (line ~982:
     files matching `test-` ending `.py`), or read an explicit test-set list file.
  2. Filter by `include-tests` / `--include-test-cases` (per-test case subsetting;
     extracts `set_id` from `test-SSSS.NNNN[.extra].py`).
  3. For each testset, assemble args including **`-s <setup>`** (lines ~1101/1189) and
     per-test options, then execute the testset.
  4. After the run: optional archive of `*gz`/GUI files, publish per-case results to the
     DB, email a summary with the return code.
- **This is where the chain meets the individual script** — each `test-*.py` is launched
  with the setup file, exactly like our direct path.

### 6. `test-<suite>.<set>.py` — the testset (the unit WE generate)
- Launched as: `sudo python3 test-<suite>.<set>.py -s <setup> -v` (our `pt_exec.py`
  does this directly; `runTestSuite` does it as part of the batch).
- **Runtime lifecycle inside the framework** (`ATTestSet.run(sys.argv)`):
  1. `create_log_file()` → `test-<suiteNum>.<setNum>.log`.
  2. `TestSet.init(setup)` — bind topology from the setup file.
  3. Framework pre-run hygiene (**automatic, no script code**): reboot devices to
     `default.cfg`, power-cycle, clear exception logs, verify stacks/switches
     well-formed, save/restore running config. (Skipped if `noconf`.)
  4. `TestSet.configure()` — one-time suite setup (base config: int/vlan/ip/…). (Skipped
     if `noconf`.)
  5. For each added `TestCase_<n>` in order: `_pre_run()` → `configure()` → `main()`
     (the actual test + `self.passed()/failed()`) → `tear_down()` → `_post_tear_down()`.
     Framework writes the `>> test-… / TEST_CASE_* / << test-…: RESULT (numPassed p
     numFailed f)` block around each.
  6. `TestSet.tear_down()` — one-time suite cleanup. (Skipped if `noconf`.)
- **Log contract** (per-step PASS/FAIL) is specified in
  `../pytest-create/LOGGING-CONTRACT.md`.

### 7–9. Result retrieval (our path)
- **7. Log produced:** `test-<suiteNum>.<setNum>.log` next to the script.
- **8. Retrieve:** SFTP the log back (our `pt_exec.py` gets it by basename).
- **9. Parse:** `pt_exec.parse_framework_log()` → per-case PASS/FAIL/ERROR/UNSUPPORTED +
  numPassed/numFailed. Validated against a real 101-case log.

---

## Distilled: minimum to run ONE generated test (the direct path)

For PyTest Creator / Test Composer running a single generated testset on tb470, the
chain collapses to:

1. **`configs/<hostname>.setup` exists** (topology; device on u5). ← hard requirement.
2. *(maybe)* **`configs/<hostname>.cfg` exists** — needed by the suite runners; the
   direct `-s` path appears NOT to read it. **VERIFY on first real run** (§5b of
   `../pytest-create/PLAN-pytest-testing.md`): if the direct run errors on a missing
   config.cfg, generate it with `config_gen.py`; else it's out of scope.
3. *(optional)* firmware already loaded (skip build-load unless testing a build).
4. `sudo python3 test-<suite>.<set>.py -s <setup> -v` → log → SFTP back → parse.

**On tb470 right now:** neither `configs/tb470.setup` nor `configs/tb470.cfg` exists —
both are Terrence-side prerequisites (topology = physical wiring). The tool generates
the test SCRIPT only; setup/config are environment inputs.

## What Test Composer should reuse vs emulate
- **Reuse directly (read-only, on the box):** `Setup.py` resolution helpers
  (`get_default_config_dir/_setup_file/_config_file`), the framework lifecycle
  (subclass `ATTestSet`/`ATTestCase` — free logging + hygiene), `parse_framework_log`.
- **Emulate / optionally reuse:** the `runTestSuite` launch loop (glob `test-*.py`,
  build `-s` args, execute, collect logs) — this is the model for batching multiple
  generated tests. Firmware build-load (`copyBuild`) and config→options resolution are
  reusable when we want build-specific or config-driven runs.
- **Skip for single generated tests:** git-sync, DB publish, email — unless we later
  want results in the ART results DB.

## Open verifications (do on the first real tb470 run)
- [ ] Does the direct `-s` single-script path need `config.cfg`, or only the `.setup`?
- [x] Exact `.setup` schema needed for tb470 (device on u5) — captured 2026-07-28 in
      **[`ask-ck/pytest-create/SETUP-FILE-REFERENCE.md`](../pytest-create/SETUP-FILE-REFERENCE.md)**:
      a real worked example plus every section `Setup.py` accepts, including `[stack]`,
      `[configured_stackport]`, and the `tb-swi_X = ethN-portA.B.C` cabling convention.
      Writing `configs/tb470.setup` still needs tb470's device list and cabling.
- [ ] Whether `noconf` behavior matters for our generated tests (do we want the
      framework's default-config/power-cycle hygiene, or skip it for speed?).
