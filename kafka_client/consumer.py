
import json

from kafka import KafkaConsumer, TopicPartition, OffsetAndMetadata
from kafka.errors import KafkaError

from kafka_client.kafka_config import (
    BOOTSTRAP_SERVERS,
    TELEMETRY_TOPIC,
    CONSUMER_GROUP_ID,
    AUTO_OFFSET_RESET,
    ENABLE_AUTO_COMMIT,
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
    )


def commit_message_offset(consumer, message):
    """Commit only the next offset after this message."""
    partition = TopicPartition(message.topic, message.partition)

    consumer.commit({
        partition: OffsetAndMetadata(message.offset + 1, "", -1)
    })


def consume_messages(
    max_messages=None,
    group_id=CONSUMER_GROUP_ID,
    auto_offset_reset=AUTO_OFFSET_RESET,
):
    if max_messages is not None and max_messages <= 0:
        raise ValueError("max_messages must be greater than zero")

    consumer = None

    received = 0
    processed = 0
    rejected = 0

    try:
        consumer = create_consumer(group_id, auto_offset_reset)

        print(f"Listening to topic: {TELEMETRY_TOPIC}")
        print(f"Consumer group: {group_id}")
        print("Press CTRL+C to stop.\n")

        for message in consumer:
            received += 1

            try:
                key = (
                    message.key.decode("utf-8")
                    if message.key else None
                )

                value = json.loads(message.value.decode("utf-8"))

            except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
                rejected += 1

                print(f"Rejected malformed message at offset {message.offset}")
                print(f"Reason: {error}")

                # Skip the malformed record to avoid repeatedly blocking.
                commit_message_offset(consumer, message)

            else:
                print("Received message:")
                print("Key:", key)
                print("Value:", json.dumps(value, indent=4))

                # Commit only after successful processing.
                commit_message_offset(consumer, message)
                processed += 1

            if max_messages is not None and received >= max_messages:
                print("\nConfigured consumer message limit reached.")
                break

    except KeyboardInterrupt:
        print("\nConsumer stopped by user.")

    except KafkaError as error:
        print(f"Kafka error: {error}")

    except Exception as error:
        print(f"Unexpected consumer error: {error}")

    finally:
        if consumer is not None:
            consumer.close(autocommit=False)
            print("Consumer connection closed.")

        print("\nConsumer Summary")
        print(f"Messages received: {received}")
        print(f"Messages processed: {processed}")
        print(f"Messages rejected: {rejected}")


if __name__ == "__main__":
    consume_messages()
