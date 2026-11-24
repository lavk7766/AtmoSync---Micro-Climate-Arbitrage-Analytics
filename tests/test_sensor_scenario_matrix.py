from datetime import datetime, timedelta, timezone

import simulator.event_builder as event_builder

from simulator.data_validator import validate_event
from simulator.event_builder import event_to_dict
from simulator.humidity_fault_injector import (
    HumidityFaultInjector,
    HumidityFaultWindow,
)
from simulator.product_reference import ProductReference
from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)


START = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)


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


def test_combined_sensor_scenario_matrix(monkeypatch):
    reference = apple_reference()

    # Temperature fault: START + 5 seconds to +20 seconds.
    temperature_window = TemperatureFaultWindow(
        start_at=START + timedelta(seconds=5),
        end_at=START + timedelta(seconds=20),
        temperature_c=9.0,
        label="sustained_high_temperature",
    )

    temperature_injector = TemperatureFaultInjector({
        "CONT001": [temperature_window]
    })

    # Humidity fault: START + 10 seconds to +25 seconds.
    humidity_window = HumidityFaultWindow(
        start_at=START + timedelta(seconds=10),
        end_at=START + timedelta(seconds=25),
        humidity_pct=75.0,
        label="sustained_low_humidity",
    )

    humidity_injector = HumidityFaultInjector({
        "CONT001": [humidity_window]
    })

    # Six deterministic sampling timestamps.
    timestamps = [
        START + timedelta(seconds=offset)
        for offset in (0, 5, 10, 15, 20, 25)
    ]

    timestamp_sequence = iter(timestamps)

    monkeypatch.setattr(
        event_builder.simulation_clock,
        "now",
        lambda: next(timestamp_sequence),
    )

    monkeypatch.setattr(
        event_builder.location_simulator,
        "get_current_location",
        lambda container_id: (28.61393, 77.20877),
    )

    events = []

    for _ in timestamps:
        event = event_builder.build_sensor_event(
            "CONT001",
            product_reference=reference,
            fault_injector=temperature_injector,
            humidity_fault_injector=humidity_injector,
        )

        events.append(event)

    # Confirm all six events were generated.
    assert len(events) == 6

    # Every event must pass the general sensor-event validator.
    for event in events:
        valid, reason = validate_event(event_to_dict(event))
        assert valid, reason

    # NORMAL: both readings within product recommendations.
    assert -1.0 <= events[0].temperature_c <= 4.0
    assert 90.0 <= events[0].humidity_pct <= 95.0

    # TEMPERATURE EXCURSION: three consecutive samples.
    for event in events[1:4]:
        assert event.temperature_c == 9.0

    # Humidity remains normal during the first temperature fault.
    assert 90.0 <= events[1].humidity_pct <= 95.0

    # BOTH FAULTS: two overlapping samples.
    for event in events[2:4]:
        assert event.temperature_c == 9.0
        assert event.humidity_pct == 75.0

    # TEMPERATURE RECOVERY: humidity fault remains active.
    assert -1.0 <= events[4].temperature_c <= 4.0
    assert events[4].humidity_pct == 75.0

    # FULL RECOVERY: both readings return to normal ranges.
    assert -1.0 <= events[5].temperature_c <= 4.0
    assert 90.0 <= events[5].humidity_pct <= 95.0

    # Every generated event must have a unique ID.
    event_ids = [event.event_id for event in events]
    assert len(set(event_ids)) == 6