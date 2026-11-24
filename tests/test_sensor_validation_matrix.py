import pytest

from simulator.container_generator import create_containers
from simulator.data_validator import validate_event
from simulator.event_builder import build_sensor_event, event_to_dict


NUMERIC_FIELDS = [
    "temperature_c",
    "humidity_pct",
    "vibration_g",
    "latitude",
    "longitude",
]


def create_valid_event():
    return event_to_dict(
        build_sensor_event(create_containers()[0])
    )


@pytest.mark.parametrize(
    "field",
    ["temperature_c", "humidity_pct", "vibration_g"],
)
def test_missing_sensor_reading_is_rejected(field):
    event = create_valid_event()
    del event[field]

    valid, message = validate_event(event)

    assert valid is False
    assert field in message


@pytest.mark.parametrize(
    "field",
    ["temperature_c", "humidity_pct", "vibration_g"],
)
def test_null_sensor_reading_is_rejected(field):
    event = create_valid_event()
    event[field] = None

    valid, message = validate_event(event)

    assert valid is False
    assert field in message


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
)
def test_non_finite_sensor_values_are_rejected(field, value):
    event = create_valid_event()
    event[field] = value

    valid, message = validate_event(event)

    assert valid is False
    assert "finite number" in message


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize(
    "value",
    [True, "not-a-number"],
)
def test_non_numeric_sensor_values_are_rejected(field, value):
    event = create_valid_event()
    event[field] = value

    valid, message = validate_event(event)

    assert valid is False
    assert "numeric" in message


@pytest.mark.parametrize(
    "field,value,expected_message",
    [
        ("humidity_pct", -0.1, "Humidity"),
        ("humidity_pct", 100.1, "Humidity"),
        ("latitude", -90.1, "Latitude"),
        ("latitude", 90.1, "Latitude"),
        ("longitude", -180.1, "Longitude"),
        ("longitude", 180.1, "Longitude"),
    ],
)
def test_physical_boundary_violations_are_rejected(
    field, value, expected_message
):
    event = create_valid_event()
    event[field] = value

    valid, message = validate_event(event)

    assert valid is False
    assert expected_message in message


@pytest.mark.parametrize(
    "field,value",
    [
        ("humidity_pct", 0.0),
        ("humidity_pct", 100.0),
        ("latitude", -90.0),
        ("latitude", 90.0),
        ("longitude", -180.0),
        ("longitude", 180.0),
    ],
)
def test_physical_boundary_values_are_accepted(field, value):
    event = create_valid_event()
    event[field] = value

    valid, message = validate_event(event)

    assert valid is True, message