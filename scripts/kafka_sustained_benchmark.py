"""Controlled sustained-load benchmark for the AtmoSync Kafka pipeline.

Uses the existing application producer, consumer factory, manual offset
commit helper, and telemetry validator.

Run from the repository root. Uses a dedicated empty Kafka topic.
"""

import json
import math
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

from kafka import TopicPartition

from kafka_client.producer import TelemetryProducer
from kafka_client.consumer import create_consumer, commit_message_offset
from simulator.data_validator import validate_event


TOPIC = "atmosync_aditya_sustained_20261125"
GROUP = "atmosync-aditya-sustained-20261125"
BOOTSTRAP = "localhost:9092"

MESSAGE_COUNT = 1000
TARGET_RATE_PER_SECOND = 50.0
POLL_TIMEOUT_MS = 200
LAG_SAMPLE_EVERY = 25


def percentile(values, percent):
    """Nearest-rank percentile."""
    if not values:
        return None

    ordered = sorted(values)
    index = max(0, math.ceil(percent / 100 * len(ordered)) - 1)
    return ordered[index]


def make_event(sequence):
    """Create one valid event using the existing nine-field schema."""
    return {
        "event_id": str(uuid.uuid4()),
        "container_id": "SUSTAINED_BENCHMARK_001",
        "timestamp": datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "temperature_c": 4.0,
        "humidity_pct": 90.0,
        "vibration_g": 0.1,
        "latitude": 28.61393,
        "longitude": 77.20877,
        "source_type": "synthetic_benchmark",
    }


def verify_empty_topic_and_group():
    """Refuse to benchmark a topic or group containing old test data."""
    from kafka import KafkaConsumer

    partition = TopicPartition(TOPIC, 0)

    probe = KafkaConsumer(
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP,
        enable_auto_commit=False,
    )

    try:
        end_offset = probe.end_offsets([partition])[partition]
        committed = probe.committed(partition)

        print("Initial topic end offset:", end_offset)
        print("Initial group committed offset:", committed)

        if end_offset != 0 or committed is not None:
            raise RuntimeError(
                "Benchmark topic/group is not fresh. "
                "Do not mix benchmark runs."
            )
    finally:
        probe.close()


def run_consumer_worker(ready, stop, result):
    """Consume, validate and manually commit records in one thread."""
    consumer = None
    partition = TopicPartition(TOPIC, 0)

    try:
        consumer = create_consumer(
            group_id=GROUP,
            auto_offset_reset="earliest",
            topic=TOPIC,
        )

        # Wait until the consumer has actually joined and received partition 0.
        assignment_deadline = time.monotonic() + 30

        while time.monotonic() < assignment_deadline:
            consumer.poll(timeout_ms=POLL_TIMEOUT_MS)

            if partition in consumer.assignment():
                ready.set()
                break

            if stop.is_set():
                return

        if partition not in consumer.assignment():
            raise TimeoutError("Consumer did not receive partition 0.")

        first_message_time = None
        last_commit_time = None
        seen_event_ids = set()

        while result["processed"] + result["rejected"] < MESSAGE_COUNT:
            if stop.is_set():
                break

            records = consumer.poll(timeout_ms=POLL_TIMEOUT_MS)

            for messages in records.values():
                for message in messages:
                    received_at = time.perf_counter()

                    if first_message_time is None:
                        first_message_time = received_at

                    result["received"] += 1

                    try:
                        event = json.loads(message.value.decode("utf-8"))
                        valid, reason = validate_event(event)

                        if not valid:
                            raise ValueError(reason)

                        event_id = event["event_id"]

                        if event_id in seen_event_ids:
                            result["duplicates"] += 1
                        else:
                            seen_event_ids.add(event_id)

                        event_time = datetime.fromisoformat(
                            event["timestamp"].replace("Z", "+00:00")
                        )

                        latency_ms = (
                            datetime.now(timezone.utc) - event_time
                        ).total_seconds() * 1000

                        result["latencies_ms"].append(
                            max(0.0, latency_ms)
                        )

                        # Commit only after validation and processing.
                        commit_message_offset(consumer, message)
                        result["processed"] += 1

                    except (
                        UnicodeDecodeError,
                        json.JSONDecodeError,
                        TypeError,
                        ValueError,
                    ):
                        # Match the existing application's reject-and-skip
                        # policy so an invalid event does not block the stream.
                        commit_message_offset(consumer, message)
                        result["rejected"] += 1

                    last_commit_time = time.perf_counter()

                    completed = (
                        result["processed"] + result["rejected"]
                    )

                    # Sample committed consumer lag periodically.
                    if completed % LAG_SAMPLE_EVERY == 0:
                        end_offset = consumer.end_offsets(
                            [partition]
                        )[partition]

                        committed = consumer.committed(partition)

                        if committed is not None:
                            lag = max(0, end_offset - committed)
                            result["sampled_lag"].append(lag)

        result["first_message_time"] = first_message_time
        result["last_commit_time"] = last_commit_time

    except Exception as error:
        result["error"] = repr(error)
        ready.set()

    finally:
        if consumer is not None:
            consumer.close(autocommit=False)


def main():
    from kafka import KafkaConsumer

    verify_empty_topic_and_group()

    ready = threading.Event()
    stop = threading.Event()

    result = {
        "received": 0,
        "processed": 0,
        "rejected": 0,
        "duplicates": 0,
        "latencies_ms": [],
        "sampled_lag": [],
        "error": None,
        "first_message_time": None,
        "last_commit_time": None,
    }

    worker = threading.Thread(
        target=run_consumer_worker,
        args=(ready, stop, result),
        name="atmosync-benchmark-consumer",
        daemon=True,
    )

    print("\nStarting application consumer...")
    worker.start()

    if not ready.wait(timeout=35):
        stop.set()
        worker.join(timeout=5)
        raise TimeoutError("Consumer assignment was not established.")

    if result["error"]:
        raise RuntimeError(result["error"])

    print("Consumer assigned partition 0.")
    print("\nStarting sustained producer load...")
    print(f"Target messages: {MESSAGE_COUNT}")
    print(f"Target rate: {TARGET_RATE_PER_SECOND:.1f} events/second")

    producer = TelemetryProducer(topic=TOPIC)
    produced_offsets = []

    producer_start = time.perf_counter()

    try:
        for sequence in range(MESSAGE_COUNT):
            target_time = (
                producer_start + sequence / TARGET_RATE_PER_SECOND
            )

            delay = target_time - time.perf_counter()
            if delay > 0:
                time.sleep(delay)

            event = make_event(sequence)
            metadata = producer.send_event(event)

            produced_offsets.append(metadata.offset)

            if metadata.partition != 0:
                raise RuntimeError(
                    f"Unexpected partition: {metadata.partition}"
                )

            if (sequence + 1) % 100 == 0:
                print(
                    f"Produced {sequence + 1}/{MESSAGE_COUNT} events"
                )

    except Exception:
        stop.set()
        worker.join(timeout=5)
        raise

    finally:
        producer.close()

    producer_end = time.perf_counter()
    producer_duration = producer_end - producer_start

    print("\nProducer finished. Waiting for consumer to drain the topic...")

    worker.join(timeout=90)

    if worker.is_alive():
        stop.set()
        raise TimeoutError("Consumer did not finish within 90 seconds.")

    if result["error"]:
        raise RuntimeError(result["error"])

    if produced_offsets != list(range(MESSAGE_COUNT)):
        raise AssertionError(
            "Producer offsets were not contiguous from 0 to 999."
        )

    if result["received"] != MESSAGE_COUNT:
        raise AssertionError(
            f"Expected {MESSAGE_COUNT} received; got {result['received']}."
        )

    if result["processed"] != MESSAGE_COUNT:
        raise AssertionError(
            f"Expected {MESSAGE_COUNT} processed; got {result['processed']}."
        )

    first = result["first_message_time"]
    last = result["last_commit_time"]

    if first is None or last is None or last <= first:
        raise AssertionError("Invalid consumer processing duration.")

    consumer_duration = last - first
    total_duration = worker_end = time.perf_counter() - producer_start

    # Verify committed offset and topic end offset after consumer shutdown.
    partition = TopicPartition(TOPIC, 0)

    probe = KafkaConsumer(
        bootstrap_servers=BOOTSTRAP,
        group_id=GROUP,
        enable_auto_commit=False,
    )

    try:
        committed = probe.committed(partition)
        end_offset = probe.end_offsets([partition])[partition]
    finally:
        probe.close()

    final_lag = (
        None if committed is None else max(0, end_offset - committed)
    )

    producer_rate = MESSAGE_COUNT / producer_duration
    consumer_rate = MESSAGE_COUNT / consumer_duration
    overall_rate = MESSAGE_COUNT / total_duration

    latencies = result["latencies_ms"]

    report = {
        "topic": TOPIC,
        "consumer_group": GROUP,
        "messages_produced": len(produced_offsets),
        "messages_received": result["received"],
        "messages_processed": result["processed"],
        "messages_rejected": result["rejected"],
        "duplicate_event_ids": result["duplicates"],
        "producer_duration_seconds": round(producer_duration, 3),
        "consumer_processing_seconds": round(consumer_duration, 3),
        "overall_duration_seconds": round(total_duration, 3),
        "producer_events_per_second": round(producer_rate, 2),
        "consumer_events_per_second": round(consumer_rate, 2),
        "overall_events_per_second": round(overall_rate, 2),
        "event_to_consumer_latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "p50": round(percentile(latencies, 50), 2),
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
            "max": round(max(latencies), 2),
        },
        "lag_sampling_interval_records": LAG_SAMPLE_EVERY,
        "lag_sample_count": len(result["sampled_lag"]),
        "maximum_sampled_committed_lag_records": (
            max(result["sampled_lag"])
            if result["sampled_lag"] else None
        ),
        "final_committed_offset": committed,
        "final_topic_end_offset": end_offset,
        "final_lag_records": final_lag,
    }

    print("\n========== SUSTAINED LOAD BENCHMARK ==========")
    print(json.dumps(report, indent=4))

    assert result["rejected"] == 0
    assert result["duplicates"] == 0
    assert committed == MESSAGE_COUNT
    assert end_offset == MESSAGE_COUNT
    assert final_lag == 0

    print("\nSUSTAINED KAFKA BENCHMARK PASSED")


if __name__ == "__main__":
    main()
