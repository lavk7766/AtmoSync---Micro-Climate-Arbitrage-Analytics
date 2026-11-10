
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from kafka import OffsetAndMetadata, TopicPartition

import kafka_client.consumer as consumer_module


def create_test_message(offset, value, key=b"CONT001"):
    return SimpleNamespace(
        topic="container_sensor_telemetry",
        partition=0,
        offset=offset,
        key=key,
        value=value,
    )


def create_mock_consumer(messages):
    consumer = MagicMock()
    consumer.__iter__.return_value = iter(messages)
    return consumer


def test_valid_message_is_processed_and_committed(monkeypatch, capsys):
    message = create_test_message(
        100,
        b'{"event_id": "test-001", "container_id": "CONT001"}'
    )

    mock_consumer = create_mock_consumer([message])

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        lambda *args, **kwargs: mock_consumer,
    )

    consumer_module.consume_messages(
        max_messages=1,
        group_id="test-group",
        auto_offset_reset="latest",
    )

    expected_partition = TopicPartition(
        "container_sensor_telemetry", 0
    )

    expected_offset = OffsetAndMetadata(101, "", -1)

    mock_consumer.commit.assert_called_once_with({
        expected_partition: expected_offset
    })

    mock_consumer.close.assert_called_once_with(autocommit=False)

    output = capsys.readouterr().out

    assert "Messages received: 1" in output
    assert "Messages processed: 1" in output
    assert "Messages rejected: 0" in output


def test_malformed_json_is_rejected_without_stopping(
    monkeypatch, capsys
):
    messages = [
        create_test_message(200, b"{invalid json"),
        create_test_message(
            201,
            b'{"event_id": "test-002", "container_id": "CONT002"}'
        ),
    ]

    mock_consumer = create_mock_consumer(messages)

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        lambda *args, **kwargs: mock_consumer,
    )

    consumer_module.consume_messages(
        max_messages=2,
        group_id="test-group",
        auto_offset_reset="latest",
    )

    assert mock_consumer.commit.call_count == 2

    committed_offsets = [
        call.args[0]
        for call in mock_consumer.commit.call_args_list
    ]

    actual_offsets = [
        next(iter(offset_map.values())).offset
        for offset_map in committed_offsets
    ]

    assert actual_offsets == [201, 202]

    mock_consumer.close.assert_called_once_with(autocommit=False)

    output = capsys.readouterr().out

    assert "Rejected malformed message" in output
    assert "Messages received: 2" in output
    assert "Messages processed: 1" in output
    assert "Messages rejected: 1" in output


def test_consumer_rejects_invalid_message_limit(monkeypatch):
    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        MagicMock(),
    )

    with pytest.raises(ValueError):
        consumer_module.consume_messages(max_messages=0)

    consumer_module.create_consumer.assert_not_called()


def test_consumer_stops_at_message_limit(monkeypatch, capsys):
    messages = [
        create_test_message(
            offset,
            b'{"event_id": "test", "container_id": "CONT001"}'
        )
        for offset in range(300, 305)
    ]

    mock_consumer = create_mock_consumer(messages)

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        lambda *args, **kwargs: mock_consumer,
    )

    consumer_module.consume_messages(
        max_messages=2,
        group_id="test-group",
        auto_offset_reset="latest",
    )

    assert mock_consumer.commit.call_count == 2

    output = capsys.readouterr().out

    assert "Messages received: 2" in output
    assert "Messages processed: 2" in output
