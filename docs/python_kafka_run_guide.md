# AtmoSync — Python IoT Simulator and Kafka Run Guide

**Component owner:** Aditya Singh Bisht
**Last updated:** 9 November 2026

## 1. Prerequisites

The following environment is used for the Python simulator and Kafka integration:

- Windows with PowerShell
- Docker Desktop running
- Python 3.12.16
- Anaconda environment: `atmosync`
- Apache Kafka 4.4.0 running in Docker

Repository location:

```text
C:\Users\User\Desktop\AtmoSync-GitHub
```

Python interpreter:

```text
C:\Users\User\anaconda3\envs\atmosync\python.exe
```

Run all commands from the repository root unless otherwise stated.

## 2. Start and Verify Kafka

Check whether the Kafka container is running:

```powershell
docker ps --filter "name=atmosync-kafka"
```

If the container exists but is stopped, start it:

```powershell
docker start atmosync-kafka
```

Verify that the broker is running and port 9092 is available.

Kafka connection:

```text
localhost:9092
```

Telemetry topic:

```text
container_sensor_telemetry
```

Optional topic verification:

```powershell
docker exec atmosync-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

## 3. Configure the Simulator

Open:

```text
simulator/config.py
```

Current simulator settings:

```python
NUM_CONTAINERS = 5
SIMULATION_INTERVAL_SECONDS = 5
MAX_EVENTS = None
```

`MAX_EVENTS` controls the total number of events generated per run.

- `None`: Continuous simulation until manually stopped.
- `25`: Generate 25 total events and stop automatically.
- Other positive integers: Generate the configured total event count.

The simulator generates readings for the configured containers and publishes valid telemetry events to Kafka.

## 4. Run the Python IoT Simulator

From the repository root:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -m simulator.sensor_simulator
```

The simulator:

1. Creates the configured container IDs.
2. Generates sensor events.
3. Validates each event.
4. Publishes valid events to Kafka.
5. Displays the Kafka topic, partition and offset.
6. Closes the producer when stopped.

Press `CTRL+C` to stop continuous simulation.

## 5. Run the Kafka Consumer

Open a second PowerShell terminal.

Run:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -m kafka_client.consumer
```

The consumer:

1. Connects to the configured Kafka topic.
2. Receives telemetry messages.
3. Decodes and processes valid JSON messages.
4. Rejects malformed messages without terminating the entire consumption loop.
5. Commits offsets manually after processing or rejecting a message.
6. Displays processing statistics.
7. Closes the consumer when stopped.

Press `CTRL+C` to stop the consumer.

## 6. Run a Controlled Producer–Consumer Test

For a finite test, first open `simulator/config.py` and configure:

```python
MAX_EVENTS = 25
```

Start a separate consumer before starting the producer.

Example consumer command:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -c "from kafka_client.consumer import consume_messages; consume_messages(max_messages=25, group_id='atmosync_repeatability_demo', auto_offset_reset='latest')"
```

Start the producer in another terminal:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -m simulator.sensor_simulator
```

Expected result for a controlled 25-event test:

- 25 events generated.
- 25 events published.
- 25 messages received.
- 25 messages processed.
- 0 rejected messages.

Use a fresh consumer group name for an isolated test. The consumer starts at the latest available offset when that group has no previously committed offset.

After testing, restore:

```python
MAX_EVENTS = None
```

## 7. Verify Consumer Offset Progress

Kafka consumer-group progress can be checked using:

```powershell
docker exec -it atmosync-kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group atmosync_repeatability_demo
```

Important columns:

- `CURRENT-OFFSET`: Last committed consumer position.
- `LOG-END-OFFSET`: End of available records.
- `LAG`: Number of records remaining for the consumer group.

A lag of zero indicates that the committed position has reached the log end at the time of inspection.

## 8. Run Automated Tests

Run the complete test suite:

```powershell
& "C:\Users\User\anaconda3\envs\atmosync\python.exe" -m pytest -v
```

The verified test suite on 9 November 2026 contained 25 passing tests covering:

- Kafka consumer processing.
- Malformed JSON handling.
- Manual offset commits.
- Consumer message limits.
- Simulator event-count control.
- Continuous simulation shutdown.
- Sensor event generation.
- GPS route movement.
- Event validation.

## 9. Current Implementation Notes

- Sensor telemetry is synthetic and uses `source_type = "synthetic_simulated"`.
- GPS coordinates are included in sensor events.
- The current simulator uses five containers.
- Transport speeds are illustrative configuration assumptions.
- The consumer uses manual offset commits.
- Malformed records are rejected and skipped after their offsets are committed.
- Kafka-to-Snowflake persistence is handled separately and is not verified by this guide.

## 10. Supporting Test Evidence

The repeatability test report is available at:

```text
docs/evidence/kafka_repeatability_test.md
```

Additional integration evidence is stored in:

```text
docs/evidence/
```

This includes broker status, producer output and consumer GPS verification screenshots.
