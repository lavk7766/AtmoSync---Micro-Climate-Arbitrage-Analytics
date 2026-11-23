from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import simulator.sensor_simulator as simulator
from simulator.humidity_fault_injector import HumidityFaultInjector
from simulator.product_reference import ProductReference


START = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)


def apple_reference():
    return ProductReference(
        product_name="Apple",
        product_stage_or_variety="General fresh apples",
        recommended_temp_min_c=-1.0,
        recommended_temp_max_c=4.0,
        best_temp_c=1.5,
        humidity_min_pct=90.0,
        humidity_max_pct=95.0,
        shelf_life_min_hours=720.0,
        shelf_life_max_hours=8640.0,
        data_source="test_reference",
    )


def configure_active_schedule(monkeypatch):
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_ENABLED", True)
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_CONTAINER_ID", "CONT001")
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_START_DELAY_SECONDS", 10.0)
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_DURATION_SECONDS", 30.0)
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_VALUE_PCT", 75.0)


def test_humidity_schedule_uses_product_reference_and_start_time(monkeypatch):
    configure_active_schedule(monkeypatch)
    reference = apple_reference()

    injector, details, status = simulator.create_humidity_fault_injector(
        ["CONT001", "CONT002"],
        {"CONT001": reference},
        START,
    )

    assert status == "active"
    assert isinstance(injector, HumidityFaultInjector)
    assert details["container_id"] == "CONT001"
    assert details["start_at"] == START + timedelta(seconds=10)
    assert details["end_at"] == START + timedelta(seconds=40)
    assert details["humidity_pct"] == 75.0
    assert details["recommended_min_pct"] == 90.0
    assert details["recommended_max_pct"] == 95.0

    assert injector.get_humidity_override(
        "CONT001", START + timedelta(seconds=10), reference
    ) == 75.0

    assert injector.get_humidity_override(
        "CONT001", START + timedelta(seconds=40), reference
    ) is None


def test_humidity_schedule_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_ENABLED", False)

    injector, details, status = simulator.create_humidity_fault_injector(
        ["CONT001"], {"CONT001": apple_reference()}, START
    )

    assert injector is None
    assert details is None
    assert "disabled" in status


def test_humidity_schedule_is_inactive_without_product_reference(monkeypatch):
    configure_active_schedule(monkeypatch)

    injector, details, status = simulator.create_humidity_fault_injector(
        ["CONT001"], {}, START
    )

    assert injector is None
    assert details is None
    assert "no product reference" in status


def test_humidity_schedule_is_inactive_when_target_is_absent(monkeypatch):
    configure_active_schedule(monkeypatch)

    injector, details, status = simulator.create_humidity_fault_injector(
        ["CONT002"], {"CONT001": apple_reference()}, START
    )

    assert injector is None
    assert details is None
    assert "not in this run" in status


def test_humidity_inside_product_range_is_rejected(monkeypatch):
    configure_active_schedule(monkeypatch)
    monkeypatch.setattr(simulator, "HUMIDITY_FAULT_VALUE_PCT", 92.0)

    with pytest.raises(ValueError, match="inside"):
        simulator.create_humidity_fault_injector(
            ["CONT001"], {"CONT001": apple_reference()}, START
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("HUMIDITY_FAULT_START_DELAY_SECONDS", -1.0),
        ("HUMIDITY_FAULT_DURATION_SECONDS", 0.0),
        ("HUMIDITY_FAULT_VALUE_PCT", 101.0),
        ("HUMIDITY_FAULT_VALUE_PCT", float("nan")),
    ],
)
def test_invalid_humidity_schedule_settings_are_rejected(
    monkeypatch, field, value
):
    configure_active_schedule(monkeypatch)
    monkeypatch.setattr(simulator, field, value)

    with pytest.raises(ValueError):
        simulator.create_humidity_fault_injector(
            ["CONT001"], {"CONT001": apple_reference()}, START
        )


def test_main_passes_humidity_injector_to_event_builder(monkeypatch):
    reference = apple_reference()
    captured = []

    class FakeProducer:
        def send_event(self, event):
            return SimpleNamespace(
                topic="container_sensor_telemetry",
                partition=0,
                offset=1,
            )

        def close(self):
            pass

    def fake_build_event(
        container_id,
        product_reference=None,
        fault_injector=None,
        humidity_fault_injector=None,
    ):
        captured.append(
            (
                container_id,
                product_reference,
                fault_injector,
                humidity_fault_injector,
            )
        )
        return {"container_id": container_id}

    configure_active_schedule(monkeypatch)

    monkeypatch.setattr(simulator, "TEMPERATURE_FAULT_ENABLED", False)
    monkeypatch.setattr(simulator, "MAX_EVENTS", 1)
    monkeypatch.setattr(simulator, "create_containers", lambda: ["CONT001"])
    monkeypatch.setattr(
        simulator,
        "load_product_references_for_containers",
        lambda containers: {"CONT001": reference},
    )
    monkeypatch.setattr(
        simulator.simulation_clock, "now", lambda: START
    )
    monkeypatch.setattr(simulator, "TelemetryProducer", FakeProducer)
    monkeypatch.setattr(simulator, "build_sensor_event", fake_build_event)
    monkeypatch.setattr(simulator, "event_to_dict", lambda event: event)
    monkeypatch.setattr(
        simulator, "validate_event", lambda event: (True, "Event is valid")
    )

    simulator.main()

    assert len(captured) == 1

    container_id, received_reference, temp_injector, humidity_injector = captured[0]

    assert container_id == "CONT001"
    assert received_reference is reference
    assert temp_injector is None
    assert isinstance(humidity_injector, HumidityFaultInjector)

    assert humidity_injector.get_humidity_override(
        "CONT001", START + timedelta(seconds=10), reference
    ) == 75.0
