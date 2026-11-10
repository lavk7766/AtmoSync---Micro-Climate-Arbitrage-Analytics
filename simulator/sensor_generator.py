
import random

from simulator.config import (
    TEMPERATURE_RANGE,
    HUMIDITY_RANGE,
    VIBRATION_RANGE,
)


def generate_temperature():
    return round(random.uniform(*TEMPERATURE_RANGE), 2)


def generate_humidity():
    return round(random.uniform(*HUMIDITY_RANGE), 2)


def generate_vibration():
    return round(random.uniform(*VIBRATION_RANGE), 3)


def generate_sensor_readings():
    return {
        "temperature_c": generate_temperature(),
        "humidity_pct": generate_humidity(),
        "vibration_g": generate_vibration(),
    }
