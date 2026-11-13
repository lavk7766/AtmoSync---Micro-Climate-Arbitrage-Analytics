# Loader and Simulator Integration Test: 13 November 2026

The telemetry in this test is simulated (`source_type = synthetic_simulated`). It is not the real sensor dataset.

## Setup
- Simulator: branch Aditya-Singh-Bisht, commit 5c9e30c, run unmodified except MAX_EVENTS = 50 in a separate working copy (not committed). It ran twice (50 events each).
- Kafka: local single broker (apache/kafka 3.8.0), topic container_sensor_telemetry, 3 partitions
- Loader: ingestion/kafka_to_snowflake.py with GPS validation on (GPS_REQUIRED not disabled), consumer group atmosync-snowflake-loader

## Results
| Check | Result |
|---|---|
| Events published by the simulator | 100 (two runs of 50: 07:12:24 to 07:13:11 and 07:57:37 to 07:58:24 UTC) |
| Loader dry runs | 2 runs, 50 valid and 0 rejected each |
| Loader real runs | 2 runs, 50 valid and 0 rejected each (100 loaded) |
| Kafka consumer lag after the second load | 0 on all 3 partitions |
| Rows in RAW_CONTAINER_TELEMETRY (topic container_sensor_telemetry) | 100, distinct event_ids 100 |
| Containers | 5, with 20 events each |
| Events without GPS | 0 |
| Latitude range | 12.9716 to 28.61413 |
| Longitude range | 72.8334 to 88.36389 |
| Temperature range | 2.13 to 9.97 C |
| dbt run / dbt test on the simulator telemetry | PASS=10 / PASS=49 |

## Distance between the first and the last event of each container
| Container | Events | Distance (km) |
|---|---|---|
| CONT001 | 20 | 0.686 |
| CONT002 | 20 | 0.999 |
| CONT003 | 20 | 0.751 |
| CONT004 | 20 | 1.003 |
| CONT005 | 20 | 0.374 |

## Observations
- Each container moves between 0.4 and 1.0 km from its first to its last event.
- Both runs start every container at the same coordinates (for example CONT001 at 28.61393, 77.20877 in run 1 and in run 2). A container's track is therefore not continuous across runs.
- In the second run, temperature, humidity and vibration change from one reading to the next and show no gradual trend. For example, CONT001 temperature in four consecutive readings was 2.97, 8.03, 4.15 and 7.99 C. The values stay inside the configured ranges (temperature 2 to 10 C, humidity 40 to 90 %, vibration 0 to 1 g).
- MART_CONTAINER_LATEST now holds 5 rows, one per container, with the latest event of the second run (07:58:23 to 07:58:24 UTC).

## Evidence
- Logs: docs/evidence/2026-11-13_dbt_run_simulator_telemetry.txt and docs/evidence/2026-11-13_dbt_test_simulator_telemetry.txt
- Screenshots: docs/screenshots/2026-11-13/ (01 end of the simulator run, 02 loader dry run, 03 loader real run, 04a and 04b Snowflake summaries, 05 container movement, 06 dbt test result, 07 mart_container_latest)