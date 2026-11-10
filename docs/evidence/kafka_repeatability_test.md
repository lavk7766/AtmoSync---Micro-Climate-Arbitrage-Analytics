# AtmoSync — Kafka Producer–Consumer Repeatability Test

**Test date:** 9 November 2026
**Component:** Python IoT Simulator and Apache Kafka
**Owner:** Aditya Singh Bisht

## 1. Objective

Verify that the Python IoT Simulator can repeatedly generate sensor telemetry, publish events to Apache Kafka, and allow a Kafka consumer to receive and process the published records with manual offset commits.

## 2. Test Environment

| Parameter | Configuration |
|---|---|
| Operating system | Windows |
| Python | 3.12.16 |
| Kafka version | Apache Kafka 4.4.0 |
| Kafka deployment | Docker |
| Broker address | localhost:9092 |
| Kafka topic | container_sensor_telemetry |
| Simulated containers | 5 |
| Simulation interval | 5 seconds |
| Maximum events | 25 |
| Consumer group | atmosync_repeatability_20261109 |
| Auto offset commit | Disabled |
| Offset reset | Latest |

## 3. Test Procedure

1. Started the Kafka broker using Docker.
2. Started a fresh Kafka consumer group with a limit of 25 messages.
3. Configured the consumer to start from the latest available offset.
4. Started the Python IoT Simulator with `MAX_EVENTS = 25`.
5. Allowed the producer and consumer to complete their respective limits.
6. Inspected the consumer group's committed offsets using Kafka's consumer-groups command.
7. Restored the simulator configuration to `MAX_EVENTS = None`.

## 4. Results

| Metric | Result |
|---|---:|
| Events generated | 25 |
| Events published | 25 |
| Messages received | 25 |
| Messages processed | 25 |
| Messages rejected | 0 |
| Producer/consumer count match | 25/25 |

### Kafka Offset Verification

The following results were obtained using Kafka's consumer-groups inspection command:

| Metric | Result |
|---|---:|
| Current committed offset | 1127 |
| Log-end offset | 1127 |
| Consumer lag | 0 |
| Active consumer members after completion | 0 |

The consumer processed the configured 25-message batch and exited. The committed offset matched the log-end offset at the time of inspection.

## 5. Outcome

**Result: PASSED**

The controlled test demonstrated that:

- The simulator generated and published 25 telemetry events.
- The consumer received and processed all 25 messages.
- No malformed messages were reported during this test.
- Manual offset commits completed successfully.
- Kafka reported zero remaining consumer lag after completion.
- Producer and consumer connections closed successfully.

## 6. Automated Test Results

The complete Python test suite was run after the implementation changes.

**Result: 25 tests passed.**

Coverage includes:

- Consumer message processing and offset commits.
- Malformed JSON handling.
- Consumer message-limit behaviour.
- Simulator event-count control.
- Continuous simulation shutdown.
- Sensor event generation and validation.
- GPS route movement.

## 7. Limitations and Observations

- Total test duration and throughput were not measured.
- End-to-end processing latency was not measured.
- Duplicate-event frequency was not independently measured.
- Malformed-message handling was tested using mocked unit-test messages, not an intentionally malformed live Kafka record.
- Broker outage recovery and automatic reconnection were not demonstrated.
- Snowflake persistence was outside the scope of this test.

This test verifies a controlled simulator-to-Kafka-to-consumer flow. It does not establish production-scale performance or zero-latency processing.

## 8. Configuration After Testing

The simulator was restored to:

```python
MAX_EVENTS = None
```

This preserves continuous simulation mode. A finite event limit can be configured for future controlled tests.