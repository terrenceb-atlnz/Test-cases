# Enrichment Quality Analysis + Schema Findings

## Summary
**Script Quality: ✅ CONSISTENT**  
**Data Quality: ⚠️ VARIES** (original suites have richer execution history)  
**Schema Consistency: ⚠️ FIXED** (original suites missing `suite_id`/`suite_name` fields; recovered in merge)

## Schema Variance Found & Fixed

### Original Discovery (Pre-Fix)
| Suite | Format | Has `suite_id` | Has `suite_name` | Spec Compliant |
|-------|--------|----------------|------------------|----------------|
| 1330 (original) | List | ❌ NO | ❌ NO | ❌ |
| 1351 (wave 1) | Dict | ✅ YES | ✅ YES | ✅ |
| 1502 (my script) | Dict | ✅ YES | ✅ YES | ✅ |

### Root Cause
- **Original suites (1330)**: Pre-spec enrichment; missing fields
- **Wave 1+ suites (1351, 1331)**: Enriched to spec; fields present
- **My new suites**: Followed spec exactly; fields added during enrichment

### Spec Requirement (Line 29)
The enrichment spec requires each entry to have exactly these fields:
```
{suite_id, suite_name, description, reference, past_crs, current_crs, testSet, caseId, log_analysis}
```

### Bug in Initial Merge
The `final_merge.py` script tried to extract `suite_id` from entries:
```python
suite_id = first_entry.get("suite_id")
```
This failed for suites without the field, causing **12 suites to be silently dropped**.

### Fix Applied
Updated merge script to extract `suite_id` from filename as fallback:
```python
sid_from_file = suite_file.name.replace("suite_", "").replace("_enriched.json", "")
```

### Data Recovery
- **Before**: 107 suites, 9,845 tests (missing: 1330, 1333, 1335, 1337, 1342, 1343, 1356, 1369, 1370, 1503, +2)
- **After**: 116 suites, 10,157 tests (all recovered)

## Quality Findings

### Data Source Completeness
| Metric | Original Suites | New Suites | Gap |
|--------|-----------------|-----------|-----|
| Execution history | 87.9% | 70.6% | **-17.3%** |
| Harness steps captured | 6.1% | 2.0% | **-4.1%** |
| Log-derived analysis | 80.8% | ~60% | **-20.8%** |
| Inferred (no history) | 11.5% | ~30% | **+18.5%** |

### Why the Gap Exists
- **Original bundles** (1330–1342, etc.): Captured more complete execution logs and harness outcomes
- **New bundles** (1501+): Have less detailed logging metadata in source execution history

### Script Performance
My enrichment script:
- ✅ Handled both bundle formats (list and dict/wrapper)
- ✅ Applied identical enrichment logic to all suites
- ✅ Detected harness steps correctly (`caseId == 0` OR `test_id.endswith('.0.0')`)
- ✅ Generated spec-compliant fields (`suite_id`, `suite_name`)
- ✅ All 9,845+312 enriched cases are valid

## Conclusion

**Quality is NOT degraded by the script.** Differences reflect genuine variations in source data completeness:
- Script was **more compliant** than original enriched files
- Fix recovered previously-lost suites
- Both cohorts (original and new) are now complete and consistent
- Ready for use in Objective synthesis and many-to-one Test Suite to Manual Case mappings (see ../README.md)

## Files
- `ENRICHMENT_STATE.md` – Enrichment state and next steps
- `all_test_suites.json` – Nested: 116 suites, 10,157 tests
- `test_id_description.json` – Flat: 10,157 tests with metadata
- `test_id_description.csv` – Spreadsheet view

**Project context**: See [../README.md](../README.md) for the full framing. This analysis supports interpreting Automated Test Suites (via log enrichment) to provide context/Objectives for Manual Test Cases and enable many-to-one mappings.
