
import random

from simulator.config import (
    TEMPERATURE_RANGE,
    HUMIDITY_RANGE,
    VIBRATION_RANGE,
)
from simulator.product_reference import ProductReference
from simulator.temperature_fault_injector import TemperatureFaultInjector


def _round_within_range(value, minimum, maximum, decimals=2):
    """Round a reading without allowing it outside its reference range."""
    rounded = round(value, decimals)
    return float(max(minimum, min(maximum, rounded)))


def generate_temperature(product_reference=None):
    """
    Generate a temperature reading.

    Without a product reference, use the existing development range.
    With a reference, favour the product's best temperature.
    """
    if product_reference is None:
        return round(random.uniform(*TEMPERATURE_RANGE), 2)

    if not isinstance(product_reference, ProductReference):
        raise TypeError("product_reference must be a ProductReference")

    minimum = product_reference.recommended_temp_min_c
    maximum = product_reference.recommended_temp_max_c
    best = product_reference.best_temp_c

    if minimum == maximum:
        return float(minimum)

    reading = random.triangular(minimum, maximum, best)

    return _round_within_range(reading, minimum, maximum)


def generate_humidity(product_reference=None):
    """Generate humidity using existing or product-specific limits."""
    if product_reference is None:
        return round(random.uniform(*HUMIDITY_RANGE), 2)

    if not isinstance(product_reference, ProductReference):
        raise TypeError("product_reference must be a ProductReference")

    minimum = product_reference.humidity_min_pct
    maximum = product_reference.humidity_max_pct

    reading = random.uniform(minimum, maximum)

    return _round_within_range(reading, minimum, maximum)


def generate_vibration():
    """Generate vibration using the existing configuration."""
    return round(random.uniform(*VIBRATION_RANGE), 3)


def generate_sensor_readings(
    product_reference=None,
    *,
    container_id=None,
    timestamp=None,
    fault_injector=None,
):
    """
    Generate sensor readings with optional product references
    and scheduled temperature fault injection.

    Existing generate_sensor_readings() calls remain compatible.
    """
    temperature = generate_temperature(product_reference)
    humidity = generate_humidity(product_reference)

    if fault_injector is not None:
        if not isinstance(fault_injector, TemperatureFaultInjector):
            raise TypeError(
                "fault_injector must be a TemperatureFaultInjector"
            )

        if container_id is None:
            raise ValueError(
                "container_id is required when fault injection is enabled"
            )

        if timestamp is None:
            raise ValueError(
                "timestamp is required when fault injection is enabled"
            )

        override = fault_injector.get_temperature_override(
            container_id,
            timestamp,
            product_reference,
        )

        if override is not None:
            temperature = override

    return {
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "vibration_g": generate_vibration(),
    }
