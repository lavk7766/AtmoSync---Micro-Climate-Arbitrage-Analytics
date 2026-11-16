import pytest
from unittest.mock import MagicMock, call

import kafka_client.producer as producer_module


def test_producer_initializes_with_configured_settings(monkeypatch):
    fake_kafka_client = MagicMock()
    json_serializer = object()
    key_serializer = object()

    captured_settings = {}

    def fake_kafka_producer(**kwargs):
        captured_settings.update(kwargs)
        return fake_kafka_client

    monkeypatch.setattr(
        producer_module,
        "KafkaProducer",
        fake_kafka_producer,
    )

    monkeypatch.setattr(
        producer_module,
        "JsonSerializer",
        lambda: json_serializer,
    )

    monkeypatch.setattr(
        producer_module,
        "DefaultSerializer",
        lambda: key_serializer,
    )

    producer = producer_module.TelemetryProducer()

    assert producer.producer is fake_kafka_client

    assert captured_settings == {
        "bootstrap_servers": producer_module.BOOTSTRAP_SERVERS,
        "value_serializer": json_serializer,
        "key_serializer": key_serializer,
        "acks": producer_module.PRODUCER_ACKS,
        "retries": producer_module.PRODUCER_RETRIES,
    }


def test_send_event_uses_container_id_as_message_key():
    fake_kafka_client = MagicMock()
    future = MagicMock()
    metadata = object()

    future.get.return_value = metadata
    fake_kafka_client.send.return_value = future

    producer = producer_module.TelemetryProducer.__new__(
        producer_module.TelemetryProducer
    )
    producer.producer = fake_kafka_client

    event = {
        "event_id": "test-event-001",
        "container_id": "CONT001",
        "temperature_c": 5.5,
        "humidity_pct": 65.0,
    }

    result = producer.send_event(event)

    fake_kafka_client.send.assert_called_once_with(
        topic=producer_module.TELEMETRY_TOPIC,
        key="CONT001",
        value=event,
    )

    future.get.assert_called_once_with(timeout=10)

    assert result is metadata


def test_send_event_propagates_broker_errors():
    fake_kafka_client = MagicMock()
    future = MagicMock()

    fake_kafka_client.send.return_value = future
    future.get.side_effect = RuntimeError("Kafka broker unavailable")

    producer = producer_module.TelemetryProducer.__new__(
        producer_module.TelemetryProducer
    )
    producer.producer = fake_kafka_client

    event = {
        "event_id": "test-event-002",
        "container_id": "CONT002",
    }

    with pytest.raises(RuntimeError, match="Kafka broker unavailable"):
        producer.send_event(event)


def test_send_event_rejects_missing_container_id():
    fake_kafka_client = MagicMock()

    producer = producer_module.TelemetryProducer.__new__(
        producer_module.TelemetryProducer
    )
    producer.producer = fake_kafka_client

    event = {
        "event_id": "test-event-003",
    }

    with pytest.raises(KeyError, match="container_id"):
        producer.send_event(event)

    fake_kafka_client.send.assert_not_called()


def test_close_flushes_before_closing_producer():
    fake_kafka_client = MagicMock()

    producer = producer_module.TelemetryProducer.__new__(
        producer_module.TelemetryProducer
    )
    producer.producer = fake_kafka_client

    producer.close()

    assert fake_kafka_client.method_calls == [
        call.flush(),
        call.close(),
    ]