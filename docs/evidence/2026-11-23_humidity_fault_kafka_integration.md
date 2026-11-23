# Humidity Fault Injection and Kafka Integration Evidence

**Date:** 23 November 2026
**Project:** AtmoSync Micro-Climate Arbitrage Analytics
**Developer:** Aditya Singh Bisht
**Component:** Python IoT Simulator and Apache Kafka

## 1. Objective

Verify that scheduled humidity fault injection generates product-aware
telemetry events, validates them, publishes them to a live Kafka broker,
and allows the published messages to be consumed and verified.

The test uses a dedicated Kafka topic to avoid mixing controlled test
events with the team's normal telemetry stream.

## 2. Reference Data

The test used the canonical project reference CSV files:

- `data/reference/container_metadata.csv`
- `data/reference/product_spoilage_reference.csv`

Container assignment:

| Field | Value |
|---|---|
| Container | CONT001 |
| Product | Apple |
| Recommended temperature | -1°C to 4°C |
| Recommended humidity | 90% to 95% |
| Data source | FAO |

The injected humidity value was 75%. This is outside the configured
Apple humidity range but remains within the physical sensor validation
range of 0% to 100%.

These reference values are prototype/simulation assumptions and are
not approved production food-safety limits.

## 3. Humidity Fault Schedule

A deterministic simulation clock was used to test the fault boundaries.

| Simulated time | Scenario | Expected humidity |
|---:|---|---:|
| 0 seconds | Normal before fault | 90–95% |
| 5 seconds | Fault start (inclusive) | 75% |
| 10 seconds | Sustained fault | 75% |
| 15 seconds | Recovery (end-exclusive) | 90–95% |

The temperature readings were required to remain within the Apple
reference range throughout the sequence.

## 4. Event Generation Results

All four generated events passed `validate_event()`.

| Scenario | Event ID | Temperature | Humidity |
|---|---|---:|---:|
| Normal before | ae04e70a-02ee-455d-ba9b-332957a0aa4e | 0.28°C | 90.24% |
| Fault start | 58cab534-a987-4805-a63f-a47182646169 | 0.81°C | 75.00% |
| Fault continues | 45e424ea-1530-4a19-9113-eef076f71522 | 2.33°C | 75.00% |
| Recovery | d27c6493-acc6-4719-b6dc-7c97d0873656 | 2.88°C | 93.91% |

All temperatures remained within -1°C to 4°C.

## 5. Kafka Environment

| Setting | Value |
|---|---|
| Broker | localhost:9092 |
| Kafka container | atmosync-kafka |
| Kafka image | apache/kafka:4.4.0 |
| Test topic | atmosync_test_humidity_excursion |
| Partition | 0 |
| Replication factor | 1 |
| Producer acknowledgements | all |
| Producer retries | 5 |
| Consumer auto-commit | Disabled |

The dedicated test topic was created successfully.

The team's main topic, `container_sensor_telemetry`, was not used
or modified by this test.

## 6. Kafka Publishing Results

Four messages were successfully published.

| Scenario | Partition | Published offset |
|---|---:|---:|
| Normal before | 0 | 0 |
| Fault start | 0 | 1 |
| Fault continues | 0 | 2 |
| Recovery | 0 | 3 |

Published offsets: `[0, 1, 2, 3]`.

## 7. Kafka Read-Back Results

The test consumer read the four newly published records from the
dedicated test topic.

| Scenario | Read-back offset | Humidity |
|---|---:|---:|
| Normal before | 0 | 90.24% |
| Fault start | 1 | 75.00% |
| Fault continues | 2 | 75.00% |
| Recovery | 3 | 93.91% |

Verification results:

- Published message count: 4.
- Read-back message count: 4.
- Published and consumed event IDs matched.
- Published and consumed offsets matched.
- Read-back record contents matched the generated events.
- All read-back events passed event validation.
- Main telemetry topic remained untouched.

## 8. Python Test Results

The full Python regression suite was run after implementing the
humidity injector and main simulator scheduling integration.

Result:

`202 passed in 2.35 seconds`

The humidity-specific tests included:

- 17 humidity fault injector tests.
- 10 main simulator humidity schedule tests.

The full test suite also covered the existing simulator, event,
temperature fault and validation behavior.

## 9. Implementation Summary

The humidity implementation includes:

- `simulator/humidity_fault_injector.py`
- Updates to `simulator/sensor_generator.py`
- Updates to `simulator/event_builder.py`
- Optional schedule configuration in `simulator/config.py`
- Main simulator schedule integration in `simulator/sensor_simulator.py`
- `tests/test_humidity_fault_injector.py`
- `tests/test_humidity_simulator_schedule.py`

Humidity fault injection is disabled by default in the normal
simulator configuration.

## 10. Scope and Limitations

The controlled Kafka integration test used direct `KafkaProducer`
and `KafkaConsumer` clients to publish and read back actual records.

It verifies live Kafka broker connectivity, message publication,
message consumption, offsets, event IDs and record contents.

It does not independently verify the project's
`TelemetryProducer.send_event()` wrapper or the application's
`consume_messages()` processing and offset-commit workflow.

It also does not establish end-to-end Kafka-to-Snowflake insertion,
dbt model execution, spoilage-risk calculations or production
food-safety suitability.

Those require separate integration evidence.

## 11. Conclusion

The humidity fault injector generated a normal-to-excursion-to-recovery
telemetry sequence using the actual Apple product reference.

All four events passed validation, were published to the dedicated
Kafka topic, and were successfully read back with matching event IDs,
offsets and contents.

The controlled humidity fault and Kafka message transport test
therefore passed.
