# Kafka-to-Snowflake Loader Compatibility — Dry Run

**Date:** 24 November 2026
**Test owner:** Aditya
**Loader source:** origin/manash
**Test mode:** Dry run (no Snowflake writes)

## Test configuration

- Kafka topic: atmosync_scenario_matrix_0861fba1
- Consumer group: atmosync-snowflake-loader
- Bootstrap server: localhost:9092
- GPS validation: Required
- Starting Kafka offset: 0

## Results

| Metric | Result |
|---|---:|
| Events consumed | 7 |
| Events accepted | 7 |
| Events rejected | 0 |
| Snowflake records inserted | 0 (dry run) |
| Kafka offsets committed | No |

## Console evidence

DRY RUN: 7 valid events

Batch done: 7 valid | total loaded 7 | total rejected 0

Stopping. Loaded 7, rejected 0.

## Screenshot

2026-11-24_kafka_to_snowflake_dry_run.png

## Conclusion

The latest Manash loader successfully consumed and validated all seven events published through the application Kafka producer.

This confirms Kafka-to-loader compatibility and event validation for this test dataset.

Not verified: Live Snowflake insertion, MERGE idempotency, duplicate reprocessing, and dbt execution against these records.
