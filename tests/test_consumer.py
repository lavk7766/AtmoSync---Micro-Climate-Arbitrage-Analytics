
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from kafka import OffsetAndMetadata, TopicPartition
from kafka.errors import KafkaConnectionError, KafkaError

import kafka_client.consumer as consumer_module


def create_test_message(offset, value, key=b"CONT001"):
    return SimpleNamespace(
        topic="container_sensor_telemetry",
        partition=0,
        offset=offset,
        key=key,
        value=value,
    )


def create_batch(messages):
    partition = TopicPartition(
        "container_sensor_telemetry", 0
    )
    return {partition: messages}


def create_mock_consumer(batches):
    consumer = MagicMock()
    consumer.poll.side_effect = batches
    return consumer


def test_valid_message_is_processed_and_committed(
    monkeypatch, capsys
):
    message = create_test_message(
        100,
        b'{"event_id": "test-001", "container_id": "CONT001"}'
    )

    mock_consumer = create_mock_consumer([
        create_batch([message])
    ])

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

    mock_consumer.close.assert_called_once_with(
        autocommit=False
    )

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

    mock_consumer = create_mock_consumer([
        create_batch(messages)
    ])

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

    mock_consumer.close.assert_called_once_with(
        autocommit=False
    )

    output = capsys.readouterr().out

    assert "Rejected malformed message" in output
    assert "Messages received: 2" in output
    assert "Messages processed: 1" in output
    assert "Messages rejected: 1" in output


def test_consumer_rejects_invalid_message_limit(monkeypatch):
    factory = MagicMock()

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        factory,
    )

    with pytest.raises(ValueError):
        consumer_module.consume_messages(max_messages=0)

    factory.assert_not_called()


def test_consumer_stops_at_message_limit(
    monkeypatch, capsys
):
    messages = [
        create_test_message(
            offset,
            b'{"event_id": "test", "container_id": "CONT001"}'
        )
        for offset in range(300, 305)
    ]

    mock_consumer = create_mock_consumer([
        create_batch(messages)
    ])

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


def test_consumer_retries_after_temporary_connection_failure(
    monkeypatch, capsys
):
    message = create_test_message(
        400,
        b'{"event_id": "retry-001", "container_id": "CONT001"}'
    )

    mock_consumer = create_mock_consumer([
        KafkaConnectionError("Temporary broker failure"),
        create_batch([message]),
    ])

    factory = MagicMock(return_value=mock_consumer)

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        factory,
    )

    sleep = MagicMock()
    monkeypatch.setattr(
        consumer_module.time,
        "sleep",
        sleep,
    )

    consumer_module.consume_messages(
        max_messages=1,
        group_id="recovery-test",
        max_reconnect_attempts=2,
        reconnect_backoff_seconds=1,
    )

    # The same consumer object is retained.
    factory.assert_called_once()

    sleep.assert_called_once_with(1.0)

    mock_consumer.commit.assert_called_once()

    mock_consumer.close.assert_called_once_with(
        autocommit=False
    )

    output = capsys.readouterr().out

    assert "Transient Kafka error" in output
    assert "Messages processed: 1" in output


def test_consumer_stops_after_retry_limit(
    monkeypatch, capsys
):
    errors = [
        KafkaConnectionError("Broker unavailable"),
        KafkaConnectionError("Broker unavailable"),
        KafkaConnectionError("Broker unavailable"),
    ]

    mock_consumer = create_mock_consumer(errors)

    factory = MagicMock(return_value=mock_consumer)

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        factory,
    )

    sleep = MagicMock()
    monkeypatch.setattr(
        consumer_module.time,
        "sleep",
        sleep,
    )

    consumer_module.consume_messages(
        group_id="retry-limit-test",
        max_reconnect_attempts=2,
        reconnect_backoff_seconds=1,
        max_reconnect_backoff_seconds=5,
    )

    factory.assert_called_once()

    assert mock_consumer.poll.call_count == 3

    delays = [
        call.args[0]
        for call in sleep.call_args_list
    ]

    assert delays == [1.0, 2.0]

    mock_consumer.close.assert_called_once_with(
        autocommit=False
    )

    output = capsys.readouterr().out

    assert "Kafka retry limit reached" in output


def test_consumer_does_not_retry_non_retriable_error(
    monkeypatch, capsys
):
    mock_consumer = create_mock_consumer([
        KafkaError("Non-retriable Kafka failure")
    ])

    factory = MagicMock(return_value=mock_consumer)

    monkeypatch.setattr(
        consumer_module,
        "create_consumer",
        factory,
    )

    sleep = MagicMock()
    monkeypatch.setattr(
        consumer_module.time,
        "sleep",
        sleep,
    )

    consumer_module.consume_messages(
        group_id="non-retriable-test",
        max_reconnect_attempts=5,
    )

    factory.assert_called_once()
    mock_consumer.poll.assert_called_once()
    sleep.assert_not_called()

    mock_consumer.close.assert_called_once_with(
        autocommit=False
    )

    output = capsys.readouterr().out

    assert "Non-retriable Kafka error" in output


def test_consumer_rejects_invalid_reconnect_settings():
    with pytest.raises(ValueError):
        consumer_module.consume_messages(
            max_reconnect_attempts=-1
        )

    with pytest.raises(ValueError):
        consumer_module.consume_messages(
            reconnect_backoff_seconds=0
        )

    with pytest.raises(ValueError):
        consumer_module.consume_messages(
            poll_timeout_ms=0
        )

def test_offset_commit_retries_after_connection_failure(
    monkeypatch
):
    message = create_test_message(
        500,
        b'{"event_id": "commit-retry", "container_id": "CONT001"}'
    )

    consumer = MagicMock()

    consumer.commit.side_effect = [
        KafkaConnectionError("Temporary broker failure"),
        None,
    ]

    sleep = MagicMock()
    monkeypatch.setattr(
        consumer_module.time,
        "sleep",
        sleep,
    )

    consumer_module.commit_message_offset(
        consumer,
        message,
    )

    assert consumer.commit.call_count == 2
    sleep.assert_called_once_with(1.0)


def test_offset_commit_does_not_retry_permanent_error(
    monkeypatch
):
    message = create_test_message(
        501,
        b'{"event_id": "commit-failure", "container_id": "CONT001"}'
    )

    consumer = MagicMock()
    consumer.commit.side_effect = KafkaError(
        "Permanent commit failure"
    )

    sleep = MagicMock()
    monkeypatch.setattr(
        consumer_module.time,
        "sleep",
        sleep,
    )

    with pytest.raises(KafkaError):
        consumer_module.commit_message_offset(
            consumer,
            message,
        )

    consumer.commit.assert_called_once()
    sleep.assert_not_called()
