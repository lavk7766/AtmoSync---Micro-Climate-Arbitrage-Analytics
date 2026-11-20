# Kafka-to-Snowflake Loader Audit

**Date:** 20 November 2026
**Project:** AtmoSync MicroClimate Analytics
**Audited source:** origin/manash, commit 92fa61e
**Audit owner:** Aditya Singh Bisht

## 1. Objective

Independently inspect and test the Kafka-to-Snowflake ingestion loader without modifying Manash's branch or requiring live Snowflake credentials.

## 2. Kafka dry-run integration test

A temporary Kafka topic was created:

- Topic: atmosync_snowflake_dryrun_20261120
- Partition: 0
- Replication factor: 1
- Broker: localhost:9092

Ten events were published by the AtmoSync simulator.

The loader was executed using its --dry-run option. It consumed and validated the messages without connecting to Snowflake or inserting database rows.

| Metric | Result |
|---|---:|
| Events published | 10 |
| Events validated | 10 |
| Events rejected | 0 |
| Snowflake inserts | 0 |
| Kafka offsets | 0-9 |

The loader successfully joined its consumer group, read the ten events, validated their JSON payloads and closed its consumer connection.

## 3. Existing loader validation tests

Manash's existing validation script was extracted from origin/manash and executed locally.

Results:

- GPS-required cases: 14/14 passed
- GPS-optional cases: 2/2 passed
- Total: 16/16 passed

These tests did not require a live Snowflake connection.

## 4. Additional validation audit

Eight additional edge cases were tested against the original loader.

| Case | Original loader behavior |
|---|---|
| Non-numeric humidity | Raised TypeError |
| Temperature NaN | Incorrectly accepted |
| Temperature positive infinity | Incorrectly accepted |
| Temperature negative infinity | Incorrectly accepted |
| Vibration NaN | Incorrectly accepted |
| Vibration positive infinity | Incorrectly accepted |
| Vibration negative infinity | Incorrectly accepted |
| Timestamp without timezone | Incorrectly accepted |

Eight validation gaps were reproduced.

## 5. Candidate validation improvement

A corrected validation function was applied only to a temporary audit copy of the loader.

The candidate:

- Rejects non-numeric humidity cleanly.
- Rejects non-finite temperature and vibration values.
- Requires timezone-aware timestamps.
- Preserves existing GPS validation behavior.

Results against the corrected temporary candidate:

| Test suite | Result |
|---|---:|
| Existing validation tests | 16/16 passed |
| Additional regression cases | 8/8 passed |
| Combined checks | 24/24 passed |

The temporary candidate was not committed to the project and did not modify Manash's branch.

## 6. Raw ingestion and deduplication review

The raw table RAW_CONTAINER_TELEMETRY stores:

- EVENT_PAYLOAD
- KAFKA_TOPIC
- KAFKA_PARTITION
- KAFKA_OFFSET
- INGESTED_AT

The inspected table definition has no primary-key or unique constraint.

The Kafka loader inserts batches into the raw table and commits Kafka offsets after a successful insert.

A crash after an insert but before the Kafka offset commit may cause an event to be inserted again. This is an at-least-once ingestion behavior.

The dbt staging model deduplicates using event_payload:event_id and keeps the latest ingested_at record.

The staging schema also applies not_null and unique tests to event_id.

Recommendation: consider adding a deterministic tie-breaker using Kafka metadata to the staging model's deduplication ordering.

## 7. Outstanding items

The following remain unverified or dependent on project integration access:

1. Actual Snowflake login and connection.
2. Actual raw telemetry insertion.
3. Insert/retry behavior against a live Snowflake table.
4. Database-level record count and duplicate verification.
5. Full dbt execution against the current Snowflake database.

Canonical container metadata and product spoilage reference CSVs are also still required for product-aware simulator testing.

## 8. Conclusion

The Python simulator-to-Kafka-to-consumer flow has been verified with ten reconciled events.

The Kafka-to-Snowflake loader successfully validated ten real Kafka messages in dry-run mode, with zero rejected records and no database writes.

The original loader passed its 16 existing validation checks. Eight additional validation gaps were reproduced and fixed in an isolated candidate, which passed all 24 checks.

No changes were made to Manash's branch or Snowflake database during this audit.

**Status: PASS - Kafka dry-run and isolated loader validation audit.**
**Live Snowflake ingestion: PENDING.**
