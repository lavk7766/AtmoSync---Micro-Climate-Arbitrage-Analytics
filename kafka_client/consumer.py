
import json
import time

from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from kafka.errors import KafkaError

from kafka_client.kafka_config import (
    BOOTSTRAP_SERVERS,
    TELEMETRY_TOPIC,
    CONSUMER_GROUP_ID,
    AUTO_OFFSET_RESET,
    ENABLE_AUTO_COMMIT,
    CONSUMER_RECONNECT_BACKOFF_MS,
    CONSUMER_RECONNECT_BACKOFF_MAX_MS,
)


def create_consumer(
    group_id=CONSUMER_GROUP_ID,
    auto_offset_reset=AUTO_OFFSET_RESET,
):
    return KafkaConsumer(
        TELEMETRY_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
        enable_auto_commit=ENABLE_AUTO_COMMIT,
        reconnect_backoff_ms=CONSUMER_RECONNECT_BACKOFF_MS,
        reconnect_backoff_max_ms=CONSUMER_RECONNECT_BACKOFF_MAX_MS,
    )


def commit_message_offset(
    consumer,
    message,
    max_retries=5,
    backoff_seconds=1.0,
    max_backoff_seconds=30.0,
):
    """Commit the next offset, retrying transient Kafka errors."""

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")

    if backoff_seconds <= 0 or max_backoff_seconds <= 0:
        raise ValueError("Backoff values must be positive")

    partition = TopicPartition(message.topic, message.partition)

    offset_data = {
        partition: OffsetAndMetadata(message.offset + 1, "", -1)
    }

    for attempt in range(max_retries + 1):
        try:
            consumer.commit(offset_data)
            return

        except KafkaError as error:
            if not getattr(error, "retriable", False):
                raise

            if attempt >= max_retries:
                raise

            delay = min(
                backoff_seconds * (2 ** attempt),
                max_backoff_seconds,
            )

            print(
                f"Offset commit failed: {error}. "
                f"Retrying in {delay:.1f} seconds."
            )

            time.sleep(delay)


def consume_messages(
    max_messages=None,
    group_id=CONSUMER_GROUP_ID,
    auto_offset_reset=AUTO_OFFSET_RESET,
    max_reconnect_attempts=5,
    reconnect_backoff_seconds=1.0,
    max_reconnect_backoff_seconds=30.0,
    poll_timeout_ms=1000,
):
    if max_messages is not None and max_messages <= 0:
        raise ValueError("max_messages must be greater than zero")

    if max_reconnect_attempts < 0:
        raise ValueError("max_reconnect_attempts cannot be negative")

    if reconnect_backoff_seconds <= 0:
        raise ValueError("reconnect_backoff_seconds must be positive")

    if max_reconnect_backoff_seconds <= 0:
        raise ValueError("max_reconnect_backoff_seconds must be positive")

    if poll_timeout_ms <= 0:
        raise ValueError("poll_timeout_ms must be positive")

    received = 0
    processed = 0
    rejected = 0
    reconnect_attempt = 0
    consumer = None
    stop_requested = False

    print(f"Listening to topic: {TELEMETRY_TOPIC}")
    print(f"Consumer group: {group_id}")
    print("Press CTRL+C to stop.\n")

    try:
        while not stop_requested:
            try:
                if consumer is None:
                    consumer = create_consumer(
                        group_id,
                        auto_offset_reset,
                    )

                records = consumer.poll(
                    timeout_ms=poll_timeout_ms
                )

                reconnect_attempt = 0

            except KafkaError as error:
                if not getattr(error, "retriable", False):
                    print(f"Non-retriable Kafka error: {error}")
                    break

                reconnect_attempt += 1

                if reconnect_attempt > max_reconnect_attempts:
                    print(
                        "Kafka retry limit reached after "
                        f"{max_reconnect_attempts} retries: {error}"
                    )
                    break

                delay = min(
                    reconnect_backoff_seconds
                    * (2 ** (reconnect_attempt - 1)),
                    max_reconnect_backoff_seconds,
                )

                print(
                    f"Transient Kafka error: {error}\n"
                    f"Retrying poll in {delay:.1f} seconds "
                    f"(attempt {reconnect_attempt}/"
                    f"{max_reconnect_attempts})."
                )

                # Retain the consumer so kafka-python can
                # manage internal broker reconnection.
                time.sleep(delay)
                continue

            # Process available records.
            for partition_messages in records.values():
                for message in partition_messages:
                    received += 1

                    try:
                        key = (
                            message.key.decode("utf-8")
                            if message.key else None
                        )

                        value = json.loads(
                            message.value.decode("utf-8")
                        )

                    except (
                        UnicodeDecodeError,
                        json.JSONDecodeError,
                        TypeError,
                    ) as error:
                        print(
                            f"Rejected malformed message "
                            f"at offset {message.offset}"
                        )
                        print(f"Reason: {error}")

                        # Explicit policy: reject and skip malformed JSON.
                        commit_message_offset(consumer, message)
                        rejected += 1

                    else:
                        print("Received message:")
                        print("Key:", key)
                        print(
                            "Value:",
                            json.dumps(value, indent=4),
                        )

                        # Commit only after successful processing.
                        commit_message_offset(consumer, message)
                        processed += 1

                    if (
                        max_messages is not None
                        and received >= max_messages
                    ):
                        print(
                            "\nConfigured consumer message limit reached."
                        )
                        stop_requested = True
                        break

                if stop_requested:
                    break

    except KafkaError as error:
        print(
            "Consumer stopped after Kafka "
            f"processing/commit failure: {error}"
        )

    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")

    except Exception as error:
        print(f"Unexpected consumer error: {error}")

    finally:
        if consumer is not None:
            try:
                consumer.close(autocommit=False)
                print("Consumer connection closed.")
            except KafkaError as error:
                print(f"Warning while closing consumer: {error}")

        print("\nConsumer Summary")
        print(f"Messages received: {received}")
        print(f"Messages processed: {processed}")
        print(f"Messages rejected: {rejected}")


if __name__ == "__main__":
    consume_messages()
