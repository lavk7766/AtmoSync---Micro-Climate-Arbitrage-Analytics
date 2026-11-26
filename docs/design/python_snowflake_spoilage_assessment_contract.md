# Python-Snowflake Spoilage Assessment Integration Contract

**Project:** AtmoSync - Micro-Climate Arbitrage Analytics

**Owner:** Aditya Singh Bisht

**Date:** 26 November 2026

**Status:** Proposed Python integration contract.
Requires coordination and approval before operational use.

## 1. Purpose

Define the interface between the Snowflake/dbt spoilage-risk mart
and the Python arbitrage evaluation engine.

The Python adapter will validate container spoilage assessments
before allowing them to be used in arbitrage calculations.

The adapter does not calculate food-safety limits or independently
establish product remaining shelf life.

## 2. Existing Snowflake Fields

The inspected mart_spoilage_risk model on origin/manash commit
5880b2e currently outputs:

| Field | Intended use |
|---|---|
| container_id | Container identification |
| product_name | Product identification |
| latest_temperature_c | Latest available temperature |
| latest_humidity_pct | Latest available humidity |
| initial_shelf_life_hours | Reference shelf life |
| cumulative_aged_hours | Calculated cumulative aging |
| remaining_shelf_life_hours | Calculated remaining shelf life |
| remaining_shelf_life_pct | Remaining life percentage |
| risk_level | NORMAL, WARNING or HIGH_RISK |
| unknown_exposure_hours | Unknown telemetry exposure |
| reading_count | Count of readings surviving current mart filters |
| data_quality_status | OBSERVED, INCOMPLETE_COVERAGE, INSUFFICIENT_READINGS or DEV_PLACEHOLDER |
| latitude | Latest available latitude |
| longitude | Latest available longitude |
| last_reading_at | Timestamp of latest surviving reading |
| is_assumption_based | Indicates prototype assumptions |

## 3. Known Source Limitations

The inspected SQL filters null temperature readings before calculating
telemetry intervals.

This can bridge surrounding readings and incorrectly classify missing
temperature exposure as observed exposure.

Missing humidity readings are not independently reflected in the
current data-quality classification.

The existing missing-sensor warehouse validation documented both
issues.

Consequently:

- OBSERVED alone is not proof of complete sensor coverage.
- reading_count does not necessarily represent all source readings.
- last_reading_at may not represent the latest source event.
- remaining_shelf_life_hours may be optimistic when missing readings
  are not accounted for.

The Python adapter must not silently treat these fields as reliable.

## 4. Proposed Additional Snowflake Fields

The following fields are proposed for the future mart interface:

| Field | Type | Purpose |
|---|---|---|
| source_reading_count | INTEGER | Number of source readings before sensor-field filtering |
| missing_temperature_reading_count | INTEGER | Number of readings with missing temperature |
| missing_humidity_reading_count | INTEGER | Number of readings with missing humidity |
| missing_temperature_interval_count | INTEGER | Number of intervals affected by missing temperature |
| missing_temperature_interval_hours | FLOAT | Exposure duration affected by missing temperature |
| sensor_data_sufficient | BOOLEAN | Explicit data-quality eligibility indicator |
| assessment_updated_at | TIMESTAMP UTC | Time the spoilage assessment was calculated |

These fields are proposals and have not yet been confirmed by
the data engineering owner or project coordinator.

## 5. Python Adapter Required Fields

The Python adapter will require:

- container_id
- product_name
- latest_temperature_c
- latest_humidity_pct
- initial_shelf_life_hours
- cumulative_aged_hours
- remaining_shelf_life_hours
- risk_level
- unknown_exposure_hours
- reading_count
- data_quality_status
- latitude
- longitude
- last_reading_at
- is_assumption_based
- source_reading_count
- missing_temperature_reading_count
- missing_humidity_reading_count
- missing_temperature_interval_count
- missing_temperature_interval_hours
- sensor_data_sufficient
- assessment_updated_at

Until the additional fields are available, the current mart output
will be treated as incomplete for automated arbitrage eligibility.

## 6. Proposed Data Validation Rules

### Container and product

- container_id must not be empty.
- product_name must not be empty.
- Product names must match canonical project reference names.
- Automatic semantic aliases will not be inferred.

### Sensor readings

- Temperature must be numeric and finite.
- Humidity must be numeric, finite and between 0 and 100.
- Latitude must be between -90 and 90.
- Longitude must be between -180 and 180.

### Shelf life

- initial_shelf_life_hours must be positive.
- remaining_shelf_life_hours must be finite and non-negative.
- remaining shelf life must not exceed initial shelf life.
- cumulative_aged_hours must be non-negative.

### Data quality

- missing temperature count must be zero.
- missing humidity count must be zero.
- missing temperature interval count must be zero.
- missing temperature interval hours must be zero.
- unknown exposure hours must be zero under the conservative prototype policy.
- reading count must be at least two.
- sensor_data_sufficient must explicitly be true.
- data_quality_status must be OBSERVED.
- DEV_PLACEHOLDER assessments are not eligible.

### Timestamp freshness

- last_reading_at must be timezone-aware.
- assessment_updated_at must be timezone-aware.
- Timestamps must be evaluated against an explicit UTC evaluation time.
- Maximum permitted sensor age and assessment age must be configurable.
- No arbitrary production freshness threshold is assumed.

## 7. Adapter Output

The adapter will return:

| Field | Purpose |
|---|---|
| status | ELIGIBLE_FOR_ARBITRAGE_EVALUATION or INSUFFICIENT_DATA |
| container_id | Validated container |
| product_name | Canonical product |
| remaining_shelf_life_hours | Validated remaining life |
| risk_level | Validated risk classification |
| sensor_data_sufficient | Validated eligibility flag |
| assessment_updated_at | Assessment timestamp |
| last_reading_at | Latest source reading timestamp |
| is_assumption_based | Prototype qualification |
| prototype_only | Indicates use of assumption-based data |
| reason_codes | Reasons for ineligibility |

The adapter will not itself issue a rerouting recommendation.

## 8. Integration with the Arbitrage Engine

Only assessments returned as
ELIGIBLE_FOR_ARBITRAGE_EVALUATION may proceed to the
Python arbitrage evaluator.

An INSUFFICIENT_DATA result must stop automated evaluation.

The existing HIGH_RISK and financial comparison rules remain
subject to coordinator approval.

## 9. Initial Regression Scenarios

1. Complete and fresh assessment.
2. Missing temperature.
3. Missing humidity.
4. Missing temperature intervals.
5. Unknown exposure.
6. Development placeholder.
7. Insufficient reading count.
8. Missing remaining shelf life.
9. Invalid risk classification.
10. Stale sensor reading.
11. Stale spoilage assessment.
12. Invalid container/product mapping.
13. Invalid coordinates.
14. Contradictory data-quality indicators.
15. Assumption-based assessment.

## 10. Scope and Limitations

This contract is for prototype integration and independent Python
testing.

The current Snowflake mart has not yet been modified to expose
all proposed fields.

Business rules for data-quality eligibility and spoilage thresholds
require coordinator approval.

No production food-safety or commercial rerouting claims are made.
