from datetime import datetime, timedelta, timezone

import pytest

import simulator.event_builder as event_builder
from simulator.data_validator import validate_event
from simulator.event_builder import event_to_dict
from simulator.humidity_fault_injector import (
    HumidityFaultInjector,
    HumidityFaultWindow,
)
from simulator.product_reference import ProductReference


START = datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)


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
        data_source="FAO",
    )


def create_window(start=None, end=None, humidity=75.0):
    return HumidityFaultWindow(
        start_at=start or START,
        end_at=end or START + timedelta(minutes=10),
        humidity_pct=humidity,
    )


def test_active_humidity_fault_returns_override():
    injector = HumidityFaultInjector({"CONT001": [create_window()]})
    assert injector.get_humidity_override(
        "CONT001", START + timedelta(minutes=2), apple_reference()
    ) == 75.0


def test_humidity_fault_start_is_inclusive():
    injector = HumidityFaultInjector({"CONT001": [create_window()]})
    assert injector.get_humidity_override(
        "CONT001", START, apple_reference()
    ) == 75.0


def test_humidity_fault_end_is_exclusive():
    end = START + timedelta(minutes=10)
    injector = HumidityFaultInjector({
        "CONT001": [create_window(end=end)]
    })
    assert injector.get_humidity_override(
        "CONT001", end, apple_reference()
    ) is None


def test_humidity_fault_is_container_specific():
    injector = HumidityFaultInjector({"CONT001": [create_window()]})
    assert injector.get_humidity_override(
        "CONT002", START + timedelta(minutes=2), apple_reference()
    ) is None


def test_container_id_is_normalized():
    injector = HumidityFaultInjector({"CONT001": [create_window()]})
    assert injector.get_humidity_override(
        " cont001 ", START + timedelta(minutes=2), apple_reference()
    ) == 75.0


def test_active_humidity_fault_requires_product_reference():
    injector = HumidityFaultInjector({"CONT001": [create_window()]})
    with pytest.raises(TypeError, match="ProductReference"):
        injector.get_humidity_override(
            "CONT001", START + timedelta(minutes=2), None
        )


def test_humidity_inside_product_range_is_rejected():
    injector = HumidityFaultInjector({
        "CONT001": [create_window(humidity=92.0)]
    })
    with pytest.raises(ValueError, match="outside"):
        injector.get_humidity_override(
            "CONT001", START + timedelta(minutes=2), apple_reference()
        )


@pytest.mark.parametrize(
    "humidity, message",
    [
        (float("nan"), "finite number"),
        (float("inf"), "finite number"),
        (float("-inf"), "finite number"),
        (True, "finite number"),
        (-1.0, "between 0 and 100"),
        (101.0, "between 0 and 100"),
    ],
)
def test_invalid_humidity_fault_value_is_rejected(humidity, message):
    with pytest.raises(ValueError, match=message):
        create_window(humidity=humidity)


def test_naive_humidity_fault_timestamp_is_rejected():
    injector = HumidityFaultInjector({"CONT001": [create_window()]})
    with pytest.raises(ValueError, match="timezone-aware"):
        injector.get_humidity_override(
            "CONT001", datetime(2026, 11, 23, 10, 2), apple_reference()
        )


def test_overlapping_humidity_fault_windows_are_rejected():
    first = create_window(
        start=START, end=START + timedelta(minutes=10)
    )
    second = create_window(
        start=START + timedelta(minutes=5),
        end=START + timedelta(minutes=15),
        humidity=80.0,
    )
    with pytest.raises(ValueError, match="Overlapping"):
        HumidityFaultInjector({"CONT001": [first, second]})


def test_duplicate_normalized_container_schedules_are_rejected():
    with pytest.raises(ValueError, match="Duplicate container"):
        HumidityFaultInjector({
            "CONT001": [create_window()],
            "cont001": [create_window()],
        })


def test_event_builder_emits_humidity_excursion_and_recovers(monkeypatch):
    fault_end = START + timedelta(seconds=10)

    window = HumidityFaultWindow(
        start_at=START + timedelta(seconds=5),
        end_at=fault_end,
        humidity_pct=75.0,
        label="sustained_low_humidity_test",
    )
    injector = HumidityFaultInjector({"CONT001": [window]})

    timestamps = iter([
        START,
        START + timedelta(seconds=5),
        fault_end,
    ])

    monkeypatch.setattr(
        event_builder.simulation_clock,
        "now",
        lambda: next(timestamps),
    )
    monkeypatch.setattr(
        event_builder.location_simulator,
        "get_current_location",
        lambda container_id: (28.61393, 77.20877),
    )

    reference = apple_reference()

    events = [
        event_builder.build_sensor_event(
            "CONT001",
            product_reference=reference,
            humidity_fault_injector=injector,
        )
        for _ in range(3)
    ]

    assert 90.0 <= events[0].humidity_pct <= 95.0
    assert events[1].humidity_pct == 75.0
    assert 90.0 <= events[2].humidity_pct <= 95.0
    assert -1.0 <= events[1].temperature_c <= 4.0

    for event in events:
        is_valid, message = validate_event(event_to_dict(event))
        assert is_valid, message
