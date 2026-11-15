from datetime import datetime, timedelta, timezone

from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)
import pytest
from simulator.sensor_generator import generate_sensor_readings
from simulator.config import (
    TEMPERATURE_RANGE,
    HUMIDITY_RANGE,
    VIBRATION_RANGE,
)
from simulator.product_reference import ProductReference
from simulator.sensor_generator import (
    generate_temperature,
    generate_humidity,
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


def test_product_temperature_stays_within_reference_range():
    reference = create_apple_reference()

    for _ in range(1000):
        temperature = generate_temperature(reference)

        assert reference.recommended_temp_min_c <= temperature
        assert temperature <= reference.recommended_temp_max_c


def test_product_humidity_stays_within_reference_range():
    reference = create_apple_reference()

    for _ in range(1000):
        humidity = generate_humidity(reference)

        assert reference.humidity_min_pct <= humidity
        assert humidity <= reference.humidity_max_pct


def test_product_sensor_readings_use_reference_ranges():
    reference = create_apple_reference()

    for _ in range(100):
        readings = generate_sensor_readings(reference)

        assert -1.0 <= readings["temperature_c"] <= 4.0
        assert 90.0 <= readings["humidity_pct"] <= 95.0
        assert isinstance(readings["vibration_g"], float)


def test_zero_width_temperature_range_returns_exact_value():
    reference = ProductReference(
        product_name="Strawberry",
        product_stage_or_variety="Fresh strawberries",
        recommended_temp_min_c=0.0,
        recommended_temp_max_c=0.0,
        best_temp_c=0.0,
        humidity_min_pct=90.0,
        humidity_max_pct=95.0,
        shelf_life_min_hours=120.0,
        shelf_life_max_hours=168.0,
        data_source="FAO",
    )

    assert generate_temperature(reference) == 0.0


def test_invalid_product_reference_type_raises_error():
    with pytest.raises(TypeError):
        generate_sensor_readings("Apple")

FAULT_START = datetime(
    2026, 11, 15, 10, 0, tzinfo=timezone.utc
)

FAULT_END = FAULT_START + timedelta(minutes=10)


def create_test_fault_injector():
    window = TemperatureFaultWindow(
        start_at=FAULT_START,
        end_at=FAULT_END,
        temperature_c=8.0,
        label="warning_test",
    )

    return TemperatureFaultInjector({
        "CONT001": [window]
    })


def test_active_temperature_fault_overrides_product_reading():
    reference = create_apple_reference()
    injector = create_test_fault_injector()

    readings = generate_sensor_readings(
        reference,
        container_id="CONT001",
        timestamp=FAULT_START + timedelta(minutes=5),
        fault_injector=injector,
    )

    assert readings["temperature_c"] == 8.0
    assert 90.0 <= readings["humidity_pct"] <= 95.0


def test_inactive_fault_preserves_product_temperature_range():
    reference = create_apple_reference()
    injector = create_test_fault_injector()

    readings = generate_sensor_readings(
        reference,
        container_id="CONT001",
        timestamp=FAULT_END,
        fault_injector=injector,
    )

    assert -1.0 <= readings["temperature_c"] <= 4.0


def test_fault_injection_requires_container_id():
    reference = create_apple_reference()
    injector = create_test_fault_injector()

    with pytest.raises(ValueError, match="container_id"):
        generate_sensor_readings(
            reference,
            timestamp=FAULT_START + timedelta(minutes=5),
            fault_injector=injector,
        )


def test_fault_injection_requires_timestamp():
    reference = create_apple_reference()
    injector = create_test_fault_injector()

    with pytest.raises(ValueError, match="timestamp"):
        generate_sensor_readings(
            reference,
            container_id="CONT001",
            fault_injector=injector,
        )


def test_fault_injection_requires_correct_injector_type():
    reference = create_apple_reference()

    with pytest.raises(TypeError, match="TemperatureFaultInjector"):
        generate_sensor_readings(
            reference,
            container_id="CONT001",
            timestamp=FAULT_START,
            fault_injector="invalid",
        )
