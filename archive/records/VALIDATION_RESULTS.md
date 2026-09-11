# Comprehensive ART Validation Report
**Date**: 2026-06-23 (Generated post-enrichment)  
**Scope**: All 116 enriched suites validated against ART source pages  
**Method**: Direct comparison of test_id sets extracted from enriched JSON vs ART HTML pages

**Project context**: See [the root README](../../README.md). This validation ensures the enriched Automated Test Suites accurately support deriving Objectives for Manual AWPTCM Test Cases and many-to-one suite mappings.

---

## Summary
| Category | Count |
|----------|-------|
| ✅ Perfect Match | 109/116 |
| ⚠️ Count Mismatch | 5/116 |
| ❌ Fetch Error | 2/116 |
| **Total** | **116** |

---

## Critical Mismatches (Data Loss Detected)

### 🔴 Suite 1354: Severe Loss
- **ART Reports**: 1623 tests
- **Enriched Has**: 426 tests
- **Missing**: 1,197 tests (73.8% loss)
- **Issue**: Nearly 3/4 of test cases missing from enriched file

### 🔴 Suite 6002: Severe Loss
- **ART Reports**: 1192 tests
- **Enriched Has**: 328 tests
- **Missing**: 864 tests (72.5% loss)
- **Issue**: Nearly 3/4 of test cases missing from enriched file

### 🟡 Suite 2024: Partial Loss
- **ART Reports**: 337 tests
- **Enriched Has**: 310 tests
- **Missing**: 27 tests (8.0% loss)

### 🟡 Suite 2026: Partial Loss
- **ART Reports**: 327 tests
- **Enriched Has**: 295 tests
- **Missing**: 32 tests (9.8% loss)

### 🟡 Suite 6100: Minimal Loss
- **ART Reports**: 29 tests
- **Enriched Has**: 21 tests
- **Missing**: 8 tests (27.6% loss)

---

## Fetch Errors (2 suites - likely network timeout)
- **Suite 2034**: Unable to fetch ART page
- **Suite 2035**: Unable to fetch ART page

---

## Perfect Matches (109 suites)
All other suites show 100% test ID alignment between enriched files and ART source.

Suites: 1330–1353, 1355–1372, 1399–1502, 2000–2023, 2025, 2027–2033, 2036, 5009, 5049, 5500, 5700–5701, 5704, 5706–5708, 5710–5711, 5714, 6000–6001, 6004–6012, 6101, 6201, 6400, 6901, 6911–6914, 7000–7001, 8002–8003

---

## Investigation Required

### Hypothesis 1: ART Includes Duplicate/Parent Tests
Some ART pages may include tests from sub-categories or harness steps that my enrichment process filtered or didn't capture. Suite 1354 and 6002 show disproportionate losses.

### Hypothesis 2: Enrichment Data Loss
The enrichment process may have encountered errors for these suites and failed to capture all tests.

### Hypothesis 3: ART Page Structure Changed
The regex extraction pattern may miss test cases with non-standard URL formatting on these specific suites.

---

## Recommended Next Steps
1. **Manual inspection** of Suite 1354's ART page to understand structure
2. **Spot-check** test case extraction for Suite 6002
3. **Review** enrichment logs for suites 1354, 6002, 2024, 2026, 6100
4. **Fix fetch errors** for suites 2034–2035 with retry logic
5. **Rerun extraction** with adjusted regex if needed
6. **Update enriched files** with missing test cases once root cause identified

---

## Data Integrity Assessment
- **Good News**: 94% of suites (109/116) are 100% complete and accurate
- **Bad News**: 4.3% of suites (5/116) have significant data loss
- **Critical**: Suite 1354 (1,197 missing) and 6002 (864 missing) require immediate investigation
- **Action**: Do NOT proceed to Phase 3 (coverage matching) until mismatches resolved
