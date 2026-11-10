
from simulator.sensor_generator import generate_sensor_readings
from simulator.config import (
    TEMPERATURE_RANGE,
    HUMIDITY_RANGE,
    VIBRATION_RANGE,
)


def test_sensor_readings_are_numeric():
    readings = generate_sensor_readings()

    assert isinstance(readings["temperature_c"], float)
    assert isinstance(readings["humidity_pct"], float)
    assert isinstance(readings["vibration_g"], float)


def test_sensor_readings_are_within_configured_ranges():
    readings = generate_sensor_readings()

    assert TEMPERATURE_RANGE[0] <= readings["temperature_c"] <= TEMPERATURE_RANGE[1]
    assert HUMIDITY_RANGE[0] <= readings["humidity_pct"] <= HUMIDITY_RANGE[1]
    assert VIBRATION_RANGE[0] <= readings["vibration_g"] <= VIBRATION_RANGE[1]
