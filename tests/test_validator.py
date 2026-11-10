from simulator.event_builder import build_sensor_event, event_to_dict
from simulator.container_generator import create_containers
from simulator.data_validator import validate_event


def test_valid_event_passes_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))

    is_valid, message = validate_event(event)

    assert is_valid is True


def test_invalid_humidity_fails_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))
    event["humidity_pct"] = 150

    is_valid, message = validate_event(event)

    assert is_valid is False
    assert "Humidity" in message


def test_missing_event_id_fails_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))
    del event["event_id"]

    is_valid, message = validate_event(event)

    assert is_valid is False


def test_missing_coordinates_fail_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))
    del event["latitude"]

    is_valid, message = validate_event(event)

    assert is_valid is False
    assert "latitude" in message


def test_invalid_latitude_fails_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))
    event["latitude"] = 95.0

    is_valid, message = validate_event(event)

    assert is_valid is False
    assert "Latitude" in message


def test_invalid_longitude_fails_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))
    event["longitude"] = 200.0

    is_valid, message = validate_event(event)

    assert is_valid is False
    assert "Longitude" in message


def test_non_numeric_coordinates_fail_validation():
    event = event_to_dict(build_sensor_event(create_containers()[0]))
    event["latitude"] = "28.61394"

    is_valid, message = validate_event(event)

    assert is_valid is False
    assert "latitude" in message