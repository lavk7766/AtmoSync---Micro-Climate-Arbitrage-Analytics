
# Kafka Producer-to-Consumer Verification

**Date:** 18 November 2026
**Project:** AtmoSync MicroClimate Analytics
**Developer:** Aditya Singh Bisht
**Branch:** Aditya-Singh-Bisht

## 1. Objective

Verify live telemetry publishing from the AtmoSync Python simulator to Apache Kafka and consumption using the project's Python Kafka consumer.

## 2. Environment

- Docker container: `atmosync-kafka`
- Kafka image: `apache/kafka:4.4.0`
- Bootstrap server: `localhost:9092`
- Topic: `container_sensor_telemetry`
- Topic partition count: 1
- Replication factor: 1
- Consumer group: `atmosync_python_verification_20261118`
- Python environment: `atmosync`, Python 3.12.16

## 3. Test execution

The simulator was executed with a temporary event limit of 10:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -c "import simulator.sensor_simulator as s; s.MAX_EVENTS = 10; s.main()"
```

The project's Python consumer was started using:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -c "from kafka_client.consumer import consume_messages; consume_messages(max_messages=10, group_id='atmosync_python_verification_20261118', auto_offset_reset='latest', poll_timeout_ms=1000)"
```

## 4. Results

| Metric | Result |
|---|---:|
| Events generated | 10 |
| Events published | 10 |
| Kafka messages consumed | 10 |
| Messages processed | 10 |
| Messages rejected | 0 |
| Event ID matches | 10/10 |
| Partition | 0 |
| Offsets | 1268–1277 |

The producer received successful Kafka acknowledgements for all ten events.

The Python consumer received and processed all ten messages. Each consumed event ID matched the corresponding producer event ID.

## 5. Event reconciliation

| Offset | Event ID |
|---:|---|
| 1268 | `1200c74a-63d8-4375-ad9f-abbc96f31765` |
| 1269 | `68dcf31f-d37d-4ab5-8a76-7248fd6d31f3` |
| 1270 | `3c8eb4b3-4a39-4048-8f7f-ff5c3de61fcd` |
| 1271 | `dbc4b13e-207d-4bd1-821c-c001c33ee9b3` |
| 1272 | `de58145e-8cb2-4153-be85-2587d7e5d0ea` |
| 1273 | `24e37a3a-f92b-406b-8211-25e91c1c2bc7` |
| 1274 | `17935b1d-0d8c-4419-a5a1-9d364bcd0b92` |
| 1275 | `dd59d46d-b623-4a00-b632-e779cc4d8cbf` |
| 1276 | `a5d782e2-d8fb-41ca-9a71-a6730cbf56a8` |
| 1277 | `b3c6a845-6006-45be-b8f5-370edd76dae5` |

## 6. Important limitations

- This test used generic synthetic telemetry because the canonical container metadata and product spoilage reference CSVs were unavailable.
- Temperature fault injection was therefore inactive during this run.
- The test verifies Kafka publishing and Python consumer processing, not Snowflake ingestion.
- Kafka was running as a single-broker, single-replica local development setup.

## 7. Conclusion

The live Python simulator-to-Kafka-to-Python-consumer flow was successfully verified for ten messages.

All ten published event IDs were reconciled with the consumed messages. No messages were rejected.

**Status: PASS — Generic-mode Kafka producer/consumer verification.**
