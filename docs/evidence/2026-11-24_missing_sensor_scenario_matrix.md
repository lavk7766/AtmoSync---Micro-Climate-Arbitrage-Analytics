# Missing Sensor Reading Scenario Matrix

Date: 24 November 2026
Owner: Aditya
Fixture type: Warehouse-only test data
Reviewed dbt commit: origin/manash 200d4c8

## Purpose

Provide reproducible raw telemetry records for testing missing sensor
readings, timestamp gaps and recovery behaviour in the container
telemetry staging model and spoilage-risk mart.

These records are deliberately incomplete. They are not production
telemetry and must not be published through the normal Kafka producer
or the validated Kafka-to-Snowflake loader.

## Files

- data/scenarios/missing_sensor_reading_scenarios.jsonl
- data/scenarios/missing_sensor_container_metadata.csv

The JSONL records mirror the raw table shape:

- EVENT_PAYLOAD (JSON/VARIANT)
- KAFKA_TOPIC
- KAFKA_PARTITION
- KAFKA_OFFSET

The accompanying CSV supplies metadata for the three synthetic
test containers. All use Apple so they can match the product
spoilage reference in an isolated test environment.

## Scenario matrix

| Container | Events | Scenario | Expected validation |
|---|---:|---|---|
| TEST_MISSING_TEMP_001 | 4 | Temperature null at T+5s, valid readings resume at T+10s | Staging retains all four rows, including the null. Mart must not silently bridge across the missing sample and count the full 10-second interval as observed. |
| TEST_MISSING_HUM_001 | 4 | Humidity null at T+5s, valid readings resume at T+10s | Staging retains all four rows. Humidity coverage must not be represented as fully observed without a missing-value indicator or equivalent treatment. |
| TEST_LONG_GAP_001 | 3 | 20-second gap followed by readings at 5-second intervals | The 20-second gap is unknown exposure; subsequent readings resume observed intervals. Historical unknown exposure remains visible. |

## Current model behaviour expected from source inspection

### Missing temperature

The current stg_container_telemetry model retains the row because
container_id is present. The current mart_spoilage_risk model then
filters rows where temperature_c is null.

For TEST_MISSING_TEMP_001, this leaves three readings. The mart
calculates a 10-second interval between T+0 and T+10, then a
5-second interval between T+10 and T+15. Both are counted as
observed intervals under the current SQL.

This is the specific behaviour the fixture is intended to expose:
the missing sample is removed before interval calculation, allowing
the mart to bridge across it.

### Missing humidity

The staging model retains the null humidity value. The current
spoilage mart does not filter null humidity and does not calculate
humidity excursion duration or humidity completeness.

With the supplied sequence, the current data-quality classification
can be OBSERVED despite one missing humidity measurement. This should
be reviewed against the design requirement that missing readings must
not be treated as normal conditions.

Whether missing humidity should make the overall shelf-life estimate
ineligible requires coordinator approval.

### Long gap and recovery

For TEST_LONG_GAP_001, the current mart identifies the 20-second
interval as unknown exposure. The subsequent 5-second interval is
observed. The historical unknown exposure remains in the aggregate,
so data_quality_status remains INCOMPLETE_COVERAGE.

## Expected raw and staging checks

For an isolated test load:

1. Confirm 11 unique event IDs.
2. Confirm 3 distinct test container IDs.
3. Confirm all 11 event payloads have valid timestamps and coordinates.
4. Confirm the staging model retains all 11 rows.
5. Confirm exactly one temperature value is null.
6. Confirm exactly one humidity value is null.
7. Confirm the three metadata rows join to the Apple product reference.
8. Compare current mart output to the behaviours documented above.
9. Re-run after any agreed missing-reading fix and compare the result.

## Important implementation distinction

The production application validator and current Kafka-to-Snowflake
loader intentionally reject null temperature and humidity fields.
That validation must remain unchanged for normal application traffic.

These fixtures are designed for controlled warehouse-level testing
that bypasses the production loader.

The raw table uses a VARIANT event payload, so JSON null values can
be represented in the fixture. However, no load SQL or Kafka publish
command is included here.

## Test environment safety

Do not insert these rows into the shared production raw table or
publish them to the normal telemetry topic.

Use an isolated Snowflake test database/schema or a controlled clone
of the raw tables, and configure the dbt source to point to that
isolated test data before executing the models.

The fixed dbt source currently points to ATMOSYNC.RAW. Do not assume
that running dbt against the normal profile is isolated.

## Approval and follow-up

- Confirm missing-temperature interval semantics with Lav and Manash.
- Confirm whether missing humidity makes data quality incomplete.
- Keep unknown exposure separate from observed aging.
- Do not treat missing readings as normal conditions.
- Do not change production event validation to accommodate these fixtures.

These fixtures are test inputs, not approved food-safety rules or
operational spoilage recommendations.
