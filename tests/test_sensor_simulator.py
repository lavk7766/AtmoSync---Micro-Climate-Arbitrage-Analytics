
from types import SimpleNamespace

import pytest
import simulator.sensor_simulator as simulator


def test_simulator_stops_at_configured_event_limit(monkeypatch, capsys):
    published_events = []

    class FakeProducer:
        def send_event(self, event):
            published_events.append(event)
            return SimpleNamespace(
                topic="container_sensor_telemetry",
                partition=0,
                offset=len(published_events),
            )

        def close(self):
            pass

    monkeypatch.setattr(simulator, "MAX_EVENTS", 3)
    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001", "CONT002"],
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(
        simulator,
        "build_sensor_event",
        lambda container_id, product_reference=None, fault_injector=None: {
            "container_id": container_id
        },
    )
    monkeypatch.setattr(simulator, "event_to_dict", lambda event: event)
    monkeypatch.setattr(
        simulator,
        "validate_event",
        lambda event: (True, "Event is valid"),
    )
    monkeypatch.setattr(simulator.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
    simulator,
    "load_product_references_for_containers",
    lambda containers: {},
)

    simulator.main()

    output = capsys.readouterr().out

    assert len(published_events) == 3
    assert "Total events generated: 3" in output
    assert "Total events published: 3" in output
    assert "Configured event limit reached." in output


def test_simulator_continuous_mode_stops_on_keyboard_interrupt(
    monkeypatch, capsys
):
    published_events = []
    build_calls = 0

    class FakeProducer:
        def send_event(self, event):
            published_events.append(event)
            return SimpleNamespace(
                topic="container_sensor_telemetry",
                partition=0,
                offset=len(published_events),
            )

        def close(self):
            pass

    def generate_event(
        container_id,
        product_reference=None,
        fault_injector=None,
    ):
        nonlocal build_calls
        build_calls += 1

        if build_calls > 1:
            raise KeyboardInterrupt

        return {"container_id": container_id}

    monkeypatch.setattr(simulator, "MAX_EVENTS", None)
    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001"],
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(simulator, "build_sensor_event", generate_event)
    monkeypatch.setattr(simulator, "event_to_dict", lambda event: event)
    monkeypatch.setattr(
        simulator,
        "validate_event",
        lambda event: (True, "Event is valid"),
    )
    monkeypatch.setattr(simulator.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
    simulator,
    "load_product_references_for_containers",
    lambda containers: {},
)
    simulator.main()

    output = capsys.readouterr().out

    assert len(published_events) == 1
    assert "AtmoSync Simulator Stopped." in output
    assert "Total events generated: 1" in output
    assert "Total events published: 1" in output


def test_simulator_does_not_publish_invalid_events_and_closes_producer(
    monkeypatch, capsys
):
    published_events = []
    close_calls = []

    class FakeProducer:
        def send_event(self, event):
            published_events.append(event)

        def close(self):
            close_calls.append(True)

    monkeypatch.setattr(simulator, "MAX_EVENTS", 1)
    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001"],
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(
        simulator,
        "build_sensor_event",
        lambda container_id, product_reference=None, fault_injector=None: {
            "container_id": container_id
        },
    )
    monkeypatch.setattr(simulator, "event_to_dict", lambda event: event)
    monkeypatch.setattr(
        simulator,
        "validate_event",
        lambda event: (False, "Invalid test event"),
    )
    monkeypatch.setattr(
        simulator,
        "load_product_references_for_containers",
        lambda containers: {},
    )

    simulator.main()

    output = capsys.readouterr().out

    assert published_events == []
    assert close_calls == [True]
    assert "Invalid event: Invalid test event" in output
    assert "Total events generated: 1" in output
    assert "Total events published: 0" in output


def test_simulator_closes_producer_when_publishing_fails(monkeypatch):
    close_calls = []

    class FakeProducer:
        def send_event(self, event):
            raise RuntimeError("Kafka publishing failed")

        def close(self):
            close_calls.append(True)

    monkeypatch.setattr(simulator, "MAX_EVENTS", 1)
    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001"],
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(
        simulator,
        "build_sensor_event",
        lambda container_id, product_reference=None, fault_injector=None: {
            "container_id": container_id
        },
    )
    monkeypatch.setattr(simulator, "event_to_dict", lambda event: event)
    monkeypatch.setattr(
        simulator,
        "validate_event",
        lambda event: (True, "Event is valid"),
    )
    monkeypatch.setattr(
        simulator,
        "load_product_references_for_containers",
        lambda containers: {},
    )

    with pytest.raises(RuntimeError, match="Kafka publishing failed"):
        simulator.main()

    assert close_calls == [True]


def test_simulator_passes_correct_product_reference(monkeypatch):
    apple_reference = object()
    banana_reference = object()

    loader_calls = []
    event_calls = []

    class FakeProducer:
        def send_event(self, event):
            return SimpleNamespace(
                topic="container_sensor_telemetry",
                partition=0,
                offset=1,
            )

        def close(self):
            pass

    def fake_loader(containers):
        loader_calls.append(list(containers))
        return {
            "CONT001": apple_reference,
            "CONT002": banana_reference,
        }

    def fake_build_event(
        container_id,
        product_reference=None,
        fault_injector=None,
    ):
        event_calls.append((container_id, product_reference))
        return {"container_id": container_id}

    # This test checks metadata forwarding, not fault injection.
    monkeypatch.setattr(
        simulator,
        "TEMPERATURE_FAULT_ENABLED",
        False,
    )
    monkeypatch.setattr(simulator, "MAX_EVENTS", 2)
    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001", "CONT002"],
    )
    monkeypatch.setattr(
        simulator,
        "load_product_references_for_containers",
        fake_loader,
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(
        simulator,
        "build_sensor_event",
        fake_build_event,
    )
    monkeypatch.setattr(simulator, "event_to_dict", lambda event: event)
    monkeypatch.setattr(
        simulator,
        "validate_event",
        lambda event: (True, "Event is valid"),
    )

    simulator.main()

    assert loader_calls == [["CONT001", "CONT002"]]

    assert event_calls == [
        ("CONT001", apple_reference),
        ("CONT002", banana_reference),
    ]


def test_metadata_failure_prevents_kafka_connection(monkeypatch):
    producer_attempts = []

    class FakeProducer:
        def __init__(self):
            producer_attempts.append(True)

    def failing_loader(containers):
        raise FileNotFoundError("Metadata configuration incomplete")

    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001"],
    )
    monkeypatch.setattr(
        simulator,
        "load_product_references_for_containers",
        failing_loader,
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)

    with pytest.raises(
        FileNotFoundError,
        match="Metadata configuration incomplete",
    ):
        simulator.main()

    assert producer_attempts == []
