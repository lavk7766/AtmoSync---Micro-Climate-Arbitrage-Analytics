import json

from kafka import KafkaProducer

from kafka_client.kafka_config import (
    BOOTSTRAP_SERVERS,
    TELEMETRY_TOPIC,
    PRODUCER_ACKS,
    PRODUCER_RETRIES,
)


class TelemetryProducer:

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8"),
            acks=PRODUCER_ACKS,
            retries=PRODUCER_RETRIES,
        )

    def send_event(self, event):
        future = self.producer.send(
            topic=TELEMETRY_TOPIC,
            key=event["container_id"],
            value=event,
        )

        return future.get(timeout=10)

    def close(self):
        self.producer.flush()
        self.producer.close()