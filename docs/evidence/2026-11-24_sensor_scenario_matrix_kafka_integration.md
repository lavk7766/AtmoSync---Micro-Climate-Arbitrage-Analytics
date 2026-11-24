# Sensor Scenario Matrix — Kafka Integration Evidence

**Date:** 24 November 2026

**Project:** AtmoSync Micro-Climate Analytics

**Component:** Python IoT Simulator and Apache Kafka
**Environment:** Local development, Windows, Python 3.12.16, kafka-python 3.0.13

## 1. Objective

Validate normal sensor readings, sustained temperature and humidity excursions, overlapping faults, independent recovery, and delayed-event handling through the application Kafka producer and consumer.

## 2. Test Configuration

- Container: CONT001
- Product: Apple
- Product stage: General fresh apples
- Temperature reference: -1°C to 4°C
- Humidity reference: 90% to 95%
- Temperature fault: 9°C, active from T+5s to T+20s
- Humidity fault: 75%, active from T+10s to T+25s
- Kafka topic: atmosync_scenario_matrix_0861fba1
- Consumer group: atmosync-scenario-group-46a41366
- Kafka partition: 0

The test used a dedicated topic. The main `container_sensor_telemetry` topic was not used.

## 3. Scenario Results

Seven events were generated using the existing event builder and canonical product reference. All seven passed `validate_event()` before publishing.

| Arrival | Event time (UTC) | Temperature | Humidity | Expected condition |
|---:|---|---:|---:|---|
| 1 | 06:35:31 | 2.79°C | 94.29% | Normal |
| 2 | 06:35:36 | 9.00°C | 90.40% | Temperature excursion |
| 3 | 06:35:41 | 9.00°C | 75.00% | Both faults |
| 4 | 06:35:46 | 9.00°C | 75.00% | Both faults sustained |
| 5 | 06:35:51 | 0.17°C | 75.00% | Temperature recovered |
| 6 | 06:35:56 | 0.24°C | 90.09% | Both recovered |
| 7 | 06:35:53 | 3.55°C | 75.00% | Delayed event |

The seventh event was deliberately published after event six, despite carrying an earlier timestamp. Its readings reflect the fault schedule at T+22 seconds: temperature had recovered, while humidity was still abnormal.

## 4. Kafka Publishing and Consumption

The application `TelemetryProducer` published all seven records to the dedicated topic.

The application `consume_messages()` function consumed the records in Kafka arrival order.

| Check | Actual result |
|---|---:|
| Records published | 7 |
| Records consumed | 7 |
| Records processed | 7 |
| Records rejected | 0 |
| Published offsets | 0–6 |
| Consumer committed offset | 7 |
| Partition | 0 |

All event IDs and original timestamps were preserved. The delayed event was not reordered by the consumer.

## 5. Automated Test Results

The full project test suite completed successfully:

- Previous suite: 242 passing tests
- Combined temperature/humidity scenario test: 1 passing test
- Sensor validation matrix: 43 passing tests
- **Total: 286 passing tests**

Compilation check using `python -m compileall -q simulator kafka_client tests` also completed successfully.

The validation matrix covers missing and null sensor readings, non-finite and non-numeric values, physical humidity and coordinate boundaries, and valid boundary values.

## 6. Conclusion

The local application-level simulator-to-Kafka-to-consumer path passed the tested normal, abnormal, recovery, and delayed-event scenarios.

Temperature and humidity faults operated simultaneously and recovered independently. The consumer processed all seven records and committed the final offset.

## 7. Scope and Limitations

- The live integration test used one container, one product reference, one Kafka topic and one partition.
- Events were validated before publishing. The application consumer currently decodes JSON and commits offsets; it does not independently perform sensor-schema validation or event-time reordering.
- Missing and physically invalid sensor-value rejection was verified through unit tests, not by publishing invalid sensor records to Kafka.
- This run did not test Snowflake ingestion, duplicate handling downstream, dbt transformations, Superset dashboards, or alerts.
- No production food-safety determination is implied by the simulated product reference thresholds.
