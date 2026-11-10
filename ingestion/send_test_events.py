"""
Sends test events to Kafka to test the loader (ingestion/kafka_to_snowflake.py).

Sends 10 valid events (container_id TEST001), 1 duplicate event_id,
and 3 bad events that the loader must reject.

Usage:
    python ingestion/send_test_events.py
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from kafka import KafkaProducer

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BOOTSTRAP = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
TOPIC = os.environ["KAFKA_TOPIC"]


def make_event(i):
    return {
        "event_id": str(uuid.uuid4()),
        "container_id": "TEST001",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temperature_c": round(8.0 + i * 0.1, 2),
        "humidity_pct": round(72.0 + i * 0.2, 2),
        "vibration_g": 0.30,
        "source_type": "synthetic_simulated",
    }


def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    events = [make_event(i) for i in range(10)]
    for event in events:
        producer.send(TOPIC, key=event["container_id"], value=event)

    # Duplicate: same event_id sent again (dbt must keep only one)
    producer.send(TOPIC, key="TEST001", value=events[0])

    # Bad events: the loader must reject all three
    bad_humidity = make_event(11)
    bad_humidity["humidity_pct"] = 150
    producer.send(TOPIC, key="TEST001", value=bad_humidity)

    missing_container = make_event(12)
    del missing_container["container_id"]
    producer.send(TOPIC, key="TEST001", value=missing_container)

    bad_number = make_event(13)
    bad_number["temperature_c"] = "hot"
    producer.send(TOPIC, key="TEST001", value=bad_number)

    producer.flush()
    print("Sent 14 events: 10 valid + 1 duplicate + 3 bad.")


if __name__ == "__main__":
    main()