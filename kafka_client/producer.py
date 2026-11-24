
from kafka import KafkaProducer
from kafka.serializer import DefaultSerializer, JsonSerializer

from kafka_client.kafka_config import (
    BOOTSTRAP_SERVERS,
    TELEMETRY_TOPIC,
    PRODUCER_ACKS,
    PRODUCER_RETRIES,
)


class TelemetryProducer:

    def __init__(self, topic=TELEMETRY_TOPIC):
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Kafka topic must be a non-empty string")

        self.topic = topic

        self.producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=JsonSerializer(),
            key_serializer=DefaultSerializer(),
            acks=PRODUCER_ACKS,
            retries=PRODUCER_RETRIES,
        )

    def send_event(self, event):
        future = self.producer.send(
            topic=self.topic,
            key=event["container_id"],
            value=event,
        )

        return future.get(timeout=10)

    def close(self):
        self.producer.flush()
        self.producer.close()
