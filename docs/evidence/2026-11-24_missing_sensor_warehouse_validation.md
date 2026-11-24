# Missing Sensor Warehouse Validation

**Date:** 24 November 2026  
**Project:** AtmoSync – Micro-Climate Arbitrage Analytics  
**Validated by:** Manash Mandal  
**Fixture commit:** 5aba60e  
**Specification audit commit:** 9cc33eb

## 1. Objective

Validate the existing Snowflake and dbt spoilage-risk pipeline against controlled missing-sensor scenarios provided by Aditya.

## 2. Test Environment

- Database: ATMOSYNC_TEST_MANASH
- dbt target: fixture_test
- Warehouse: ATMOSYNC_WH
- Raw telemetry records: 11
- Container metadata records: 3
- Product reference: Apple
- Initial shelf life: 720 hours

All seven dbt source definitions and twelve model destinations were verified to resolve to the isolated test database.

The original spoilage calculation logic was not modified.

## 3. dbt Execution

Models executed:

- stg_container_telemetry
- stg_container_metadata
- stg_product_spoilage_reference
- mart_spoilage_risk

Execution results:

PASS=4, WARN=0, ERROR=0, SKIP=0, TOTAL=4

## 4. Staging Validation

All 11 telemetry records were preserved, including one missing temperature value and one missing humidity value.

Result: PASS

## 5. Scenario Results

| Scenario | Mart readings | Aged seconds | Unknown seconds | Data quality |
|---|---:|---:|---:|---|
| Missing temperature | 3 | 15.0012 | 0 | OBSERVED |
| Missing humidity | 4 | 15.0012 | 0 | OBSERVED |
| Long gap | 3 | 5.0004 | 20.0016 | INCOMPLETE_COVERAGE |

Small decimal differences are consistent with numeric rounding.

All three containers reported NORMAL risk and IS_ASSUMPTION_BASED = TRUE.

## 6. Findings

### Missing Temperature — FAIL

The model removes the missing temperature reading before calculating intervals. This bridges surrounding readings and incorrectly counts approximately 15 seconds as observed aging without recording unknown exposure.

### Missing Humidity — FAIL

The model retains all four readings but reports OBSERVED despite a missing humidity value. Missing humidity is not reflected in the current data-quality classification.

### Long Gap and Recovery — PASS

The model correctly records approximately 20 seconds of unknown exposure and resumes aging for the subsequent five-second interval.

## 7. Recommendations

- Prevent silent bridging across missing temperature readings.
- Introduce appropriate data-quality handling for missing humidity.
- Confirm downstream arbitrage eligibility rules for incomplete sensor data.
- Preserve the existing long-gap and recovery behaviour.
- Add regression tests after the missing-sensor handling policy is approved.

## 8. Pending Decisions

Team lead approval is required for the exact treatment of intervals adjacent to missing temperature readings and the downstream eligibility of containers with missing humidity.

No spoilage calculation fixes have been implemented during this baseline validation.

The isolated test database is retained for further testing.

## 9. Conclusion

Warehouse validation has confirmed two missing-sensor handling issues and verified correct long-gap recovery behaviour. The findings are ready for team review.