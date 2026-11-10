from simulator.container_generator import create_containers
from simulator.event_builder import build_sensor_event, event_to_dict


def test_event_contains_required_fields():
    containers = create_containers()
    event = build_sensor_event(containers[0])
    event_data = event_to_dict(event)

    expected_fields = {
        "event_id",
        "container_id",
        "timestamp",
        "temperature_c",
        "humidity_pct",
        "vibration_g",
        "latitude",
        "longitude",
        "source_type",
        "latitude",
        "longitude",
    }

    assert set(event_data.keys()) == expected_fields


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