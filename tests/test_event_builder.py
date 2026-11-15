
from datetime import datetime, timedelta, timezone

import simulator.event_builder as event_builder

from simulator.container_generator import create_containers
from simulator.event_builder import build_sensor_event, event_to_dict
from simulator.product_reference import ProductReference
from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)


EXPECTED_FIELDS = {
    "event_id",
    "container_id",
    "timestamp",
    "temperature_c",
    "humidity_pct",
    "vibration_g",
    "latitude",
    "longitude",
    "source_type",
}


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


def test_event_contains_required_fields():
    containers = create_containers()

    event = build_sensor_event(containers[0])
    event_data = event_to_dict(event)

    assert set(event_data.keys()) == EXPECTED_FIELDS


def test_each_event_has_unique_id():
    container = create_containers()[0]

    event1 = build_sensor_event(container)
    event2 = build_sensor_event(container)

    assert event1.event_id != event2.event_id


def test_event_contains_valid_coordinates():
    container = create_containers()[0]

    event = build_sensor_event(container)
    event_data = event_to_dict(event)

    assert isinstance(event_data["latitude"], float)
    assert isinstance(event_data["longitude"], float)

    assert -90 <= event_data["latitude"] <= 90
    assert -180 <= event_data["longitude"] <= 180

    assert round(event_data["latitude"], 5) == event_data["latitude"]
    assert round(event_data["longitude"], 5) == event_data["longitude"]


def test_event_uses_product_specific_readings():
    reference = create_apple_reference()

    event = build_sensor_event(
        "CONT001",
        product_reference=reference,
    )

    assert -1.0 <= event.temperature_c <= 4.0
    assert 90.0 <= event.humidity_pct <= 95.0


def test_event_uses_active_temperature_fault(monkeypatch):
    reference = create_apple_reference()

    timestamp = datetime(
        2026, 11, 15, 10, 0, tzinfo=timezone.utc
    )

    monkeypatch.setattr(
        event_builder.simulation_clock,
        "now",
        lambda: timestamp,
    )

    window = TemperatureFaultWindow(
        start_at=timestamp - timedelta(seconds=1),
        end_at=timestamp + timedelta(minutes=10),
        temperature_c=8.0,
        label="event_builder_test",
    )

    injector = TemperatureFaultInjector({
        "CONT001": [window]
    })

    event = build_sensor_event(
        "CONT001",
        product_reference=reference,
        fault_injector=injector,
    )

    assert event.timestamp == timestamp
    assert event.temperature_c == 8.0

    # The Kafka event must retain exactly nine fields.
    assert set(event_to_dict(event)) == EXPECTED_FIELDS


def test_event_uses_normal_readings_after_fault_window(monkeypatch):
    reference = create_apple_reference()

    timestamp = datetime(
        2026, 11, 15, 10, 0, tzinfo=timezone.utc
    )

    monkeypatch.setattr(
        event_builder.simulation_clock,
        "now",
        lambda: timestamp,
    )

    window = TemperatureFaultWindow(
        start_at=timestamp - timedelta(minutes=20),
        end_at=timestamp - timedelta(minutes=1),
        temperature_c=8.0,
        label="completed_fault",
    )

    injector = TemperatureFaultInjector({
        "CONT001": [window]
    })

    event = build_sensor_event(
        "CONT001",
        product_reference=reference,
        fault_injector=injector,
    )

    assert -1.0 <= event.temperature_c <= 4.0
