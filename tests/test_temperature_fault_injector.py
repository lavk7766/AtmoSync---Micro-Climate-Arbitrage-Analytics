
from datetime import datetime, timedelta, timezone

import pytest

from simulator.product_reference import ProductReference
from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)


START = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
END = START + timedelta(minutes=30)


def create_apple_reference():
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


def create_window(start=None, end=None, temperature=8.0):
    return TemperatureFaultWindow(
        start_at=start or START,
        end_at=end or END,
        temperature_c=temperature,
    )


def test_active_fault_returns_temperature_override():
    window = create_window()
    injector = TemperatureFaultInjector({"CONT001": [window]})

    result = injector.get_temperature_override(
        "CONT001",
        START + timedelta(minutes=10),
        create_apple_reference(),
    )

    assert result == 8.0


@pytest.mark.parametrize(
    "timestamp,expected",
    [
        (START, 8.0),
        (END - timedelta(microseconds=1), 8.0),
        (END, None),
        (START - timedelta(microseconds=1), None),
    ],
)
def test_fault_window_boundaries(timestamp, expected):
    injector = TemperatureFaultInjector(
        {"CONT001": [create_window()]}
    )

    result = injector.get_temperature_override(
        "CONT001",
        timestamp,
        create_apple_reference(),
    )

    assert result == expected


def test_fault_is_specific_to_its_container():
    injector = TemperatureFaultInjector(
        {"CONT001": [create_window()]}
    )

    result = injector.get_temperature_override(
        "CONT002",
        START + timedelta(minutes=10),
        create_apple_reference(),
    )

    assert result is None


def test_container_id_is_normalized():
    injector = TemperatureFaultInjector(
        {"CONT001": [create_window()]}
    )

    result = injector.get_temperature_override(
        " cont001 ",
        START + timedelta(minutes=10),
        create_apple_reference(),
    )

    assert result == 8.0


def test_active_fault_requires_product_reference():
    injector = TemperatureFaultInjector(
        {"CONT001": [create_window()]}
    )

    with pytest.raises(TypeError, match="ProductReference"):
        injector.get_temperature_override(
            "CONT001",
            START + timedelta(minutes=10),
            None,
        )


def test_fault_inside_product_range_is_rejected():
    # 2°C is inside the Apple reference range of -1°C to 4°C.
    window = create_window(temperature=2.0)
    injector = TemperatureFaultInjector(
        {"CONT001": [window]}
    )

    with pytest.raises(ValueError, match="outside"):
        injector.get_temperature_override(
            "CONT001",
            START + timedelta(minutes=10),
            create_apple_reference(),
        )


def test_naive_timestamp_is_rejected():
    injector = TemperatureFaultInjector(
        {"CONT001": [create_window()]}
    )

    naive_timestamp = datetime(2026, 11, 15, 10, 10)

    with pytest.raises(ValueError, match="timezone-aware"):
        injector.get_temperature_override(
            "CONT001",
            naive_timestamp,
            create_apple_reference(),
        )


@pytest.mark.parametrize("field", ["start", "end"])
def test_naive_fault_window_datetime_is_rejected(field):
    naive_time = datetime(2026, 11, 15, 10, 0)

    start = naive_time if field == "start" else START
    end = naive_time if field == "end" else END

    with pytest.raises(ValueError, match="timezone-aware"):
        TemperatureFaultWindow(
            start_at=start,
            end_at=end,
            temperature_c=8.0,
        )


@pytest.mark.parametrize(
    "start,end",
    [
        (START, START),
        (END, START),
    ],
)
def test_invalid_fault_window_order_is_rejected(start, end):
    with pytest.raises(ValueError, match="follow"):
        TemperatureFaultWindow(
            start_at=start,
            end_at=end,
            temperature_c=8.0,
        )


@pytest.mark.parametrize(
    "temperature",
    [float("nan"), float("inf"), float("-inf"), True],
)
def test_invalid_fault_temperature_is_rejected(temperature):
    with pytest.raises(ValueError, match="finite number"):
        create_window(temperature=temperature)


def test_empty_fault_label_is_rejected():
    with pytest.raises(ValueError, match="label"):
        TemperatureFaultWindow(
            start_at=START,
            end_at=END,
            temperature_c=8.0,
            label=" ",
        )


def test_overlapping_fault_windows_are_rejected():
    first = create_window(
        start=START,
        end=START + timedelta(minutes=20),
    )
    second = create_window(
        start=START + timedelta(minutes=10),
        end=END,
    )

    with pytest.raises(ValueError, match="Overlapping"):
        TemperatureFaultInjector(
            {"CONT001": [first, second]}
        )


def test_adjacent_fault_windows_are_allowed():
    first = create_window(
        start=START,
        end=START + timedelta(minutes=15),
        temperature=8.0,
    )
    second = create_window(
        start=START + timedelta(minutes=15),
        end=END,
        temperature=9.0,
    )

    injector = TemperatureFaultInjector(
        {"CONT001": [first, second]}
    )

    result = injector.get_temperature_override(
        "CONT001",
        START + timedelta(minutes=15),
        create_apple_reference(),
    )

    assert result == 9.0


def test_duplicate_normalized_container_schedules_are_rejected():
    with pytest.raises(ValueError, match="Duplicate container"):
        TemperatureFaultInjector({
            "CONT001": [create_window()],
            "cont001": [create_window()],
        })


def test_invalid_schedule_mapping_is_rejected():
    with pytest.raises(TypeError, match="mapping"):
        TemperatureFaultInjector([create_window()])


def test_invalid_window_entry_is_rejected():
    with pytest.raises(TypeError, match="TemperatureFaultWindow"):
        TemperatureFaultInjector(
            {"CONT001": [object()]}
        )