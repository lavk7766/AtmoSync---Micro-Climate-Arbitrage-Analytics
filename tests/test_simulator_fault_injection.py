from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import simulator.sensor_simulator as simulator
from simulator.product_reference import ProductReference
from simulator.temperature_fault_injector import TemperatureFaultInjector


START = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)


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


def test_fault_schedule_uses_product_reference_and_run_start():
    reference = apple_reference()

    injector, details, status = (
        simulator.create_temperature_fault_injector(
            ["CONT001", "CONT002"],
            {"CONT001": reference},
            START,
        )
    )

    assert status == "active"
    assert isinstance(injector, TemperatureFaultInjector)

    assert details["container_id"] == "CONT001"
    assert details["start_at"] == START + timedelta(seconds=5)
    assert details["end_at"] == START + timedelta(seconds=35)
    assert details["temperature_c"] == 9.0
    assert details["recommended_max_c"] == 4.0

    # The temperature is overridden inside the scheduled window.
    assert injector.get_temperature_override(
        "CONT001",
        START + timedelta(seconds=10),
        reference,
    ) == 9.0

    # Normal generation resumes at the end of the window.
    assert injector.get_temperature_override(
        "CONT001",
        START + timedelta(seconds=35),
        reference,
    ) is None


def test_fault_schedule_is_inactive_without_product_reference():
    injector, details, status = (
        simulator.create_temperature_fault_injector(
            ["CONT001"],
            {},
            START,
        )
    )

    assert injector is None
    assert details is None
    assert "no product reference" in status


def test_fault_schedule_respects_disabled_configuration(monkeypatch):
    monkeypatch.setattr(
        simulator,
        "TEMPERATURE_FAULT_ENABLED",
        False,
    )

    injector, details, status = (
        simulator.create_temperature_fault_injector(
            ["CONT001"],
            {"CONT001": apple_reference()},
            START,
        )
    )

    assert injector is None
    assert details is None
    assert "disabled" in status


def test_main_passes_active_fault_injector_to_event_builder(monkeypatch):
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
    ):
        captured.append(
            (container_id, product_reference, fault_injector)
        )
        return {"container_id": container_id}

    monkeypatch.setattr(simulator, "MAX_EVENTS", 1)
    monkeypatch.setattr(
        simulator,
        "create_containers",
        lambda: ["CONT001"],
    )
    monkeypatch.setattr(
        simulator,
        "load_product_references_for_containers",
        lambda containers: {"CONT001": reference},
    )
    monkeypatch.setattr(
        simulator,
        "TEMPERATURE_FAULT_ENABLED",
        True,
    )
    monkeypatch.setattr(
        simulator,
        "TEMPERATURE_FAULT_START_DELAY_SECONDS",
        0.0,
    )
    monkeypatch.setattr(
        simulator,
        "TEMPERATURE_FAULT_DURATION_SECONDS",
        60.0,
    )
    monkeypatch.setattr(
        simulator.simulation_clock,
        "now",
        lambda: START,
    )
    monkeypatch.setattr(
        simulator,
        "TelemetryProducer",
        FakeProducer,
    )
    monkeypatch.setattr(
        simulator,
        "build_sensor_event",
        fake_build_event,
    )
    monkeypatch.setattr(
        simulator,
        "event_to_dict",
        lambda event: event,
    )
    monkeypatch.setattr(
        simulator,
        "validate_event",
        lambda event: (True, "Event is valid"),
    )

    simulator.main()

    assert len(captured) == 1

    container_id, received_reference, injector = captured[0]

    assert container_id == "CONT001"
    assert received_reference is reference
    assert isinstance(injector, TemperatureFaultInjector)

    # The main simulator's injector produces the expected excursion.
    assert injector.get_temperature_override(
        "CONT001",
        START,
        reference,
    ) == 9.0