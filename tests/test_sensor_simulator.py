
from types import SimpleNamespace

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
        simulator, "create_containers",
        lambda: ["CONT001", "CONT002"]
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(
        simulator, "build_sensor_event",
        lambda container_id: {"container_id": container_id}
    )
    monkeypatch.setattr(
        simulator, "event_to_dict",
        lambda event: event
    )
    monkeypatch.setattr(
        simulator, "validate_event",
        lambda event: (True, "Event is valid")
    )
    monkeypatch.setattr(simulator.time, "sleep", lambda seconds: None)

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

    def generate_event(container_id):
        nonlocal build_calls
        build_calls += 1

        if build_calls > 1:
            raise KeyboardInterrupt

        return {"container_id": container_id}

    monkeypatch.setattr(simulator, "MAX_EVENTS", None)
    monkeypatch.setattr(
        simulator, "create_containers",
        lambda: ["CONT001"]
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(simulator, "build_sensor_event", generate_event)
    monkeypatch.setattr(
        simulator, "event_to_dict",
        lambda event: event
    )
    monkeypatch.setattr(
        simulator, "validate_event",
        lambda event: (True, "Event is valid")
    )
    monkeypatch.setattr(simulator.time, "sleep", lambda seconds: None)

    simulator.main()

    output = capsys.readouterr().out

    assert len(published_events) == 1
    assert "AtmoSync Simulator Stopped." in output
    assert "Total events generated: 1" in output
    assert "Total events published: 1" in output
