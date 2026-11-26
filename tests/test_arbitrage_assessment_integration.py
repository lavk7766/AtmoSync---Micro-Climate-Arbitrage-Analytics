from datetime import datetime, timezone

import pytest

from simulator.arbitrage_assessment_integration import (
    evaluate_with_spoilage_assessment,
)
from simulator.spoilage_assessment_adapter import (
    validate_spoilage_assessment,
)


EVALUATION_TIME = datetime(
    2026, 11, 26, 10, 0, tzinfo=timezone.utc
)

CONTAINER_PRODUCTS = {
    "CONT001": "Apple",
    "CONT002": "Banana",
}

PRODUCTS = {"apple", "banana"}

SHIPMENT = {
    "container_id": "CONT001",
    "product_name": "Apple",
    "quantity": "1000",
    "quantity_unit": "kg",
    "origin": "Delhi",
}

PLANNED_ROUTE = {
    "origin": "Delhi",
    "destination": "Lucknow",
    "distance_km": 500,
    "estimated_travel_hours": 2,
    "transport_cost": 1000,
    "currency": "INR",
    "source_type": "synthetic_simulated",
}

ALTERNATIVE_ROUTE = {
    "origin": "Delhi",
    "destination": "Bengaluru",
    "distance_km": 600,
    "estimated_travel_hours": 1,
    "transport_cost": 500,
    "currency": "INR",
    "source_type": "synthetic_simulated",
}

PRICES = [
    {
        "product_name": "Apple",
        "market_name": "Lucknow",
        "simulated_as_of_date": "2026-11-25",
        "price_per_kg": "150",
        "currency": "INR",
        "quantity_unit": "kg",
        "price_source_type": "synthetic_simulated",
    },
    {
        "product_name": "Apple",
        "market_name": "Bengaluru",
        "simulated_as_of_date": "2026-11-25",
        "price_per_kg": "180",
        "currency": "INR",
        "quantity_unit": "kg",
        "price_source_type": "synthetic_simulated",
    },
]


def make_assessment(**overrides):
    record = {
        "container_id": "CONT001",
        "product_name": "Apple",
        "latest_temperature_c": 3,
        "latest_humidity_pct": 92,
        "initial_shelf_life_hours": 720,
        "cumulative_aged_hours": 100,
        "remaining_shelf_life_hours": 24,
        "risk_level": "HIGH_RISK",
        "unknown_exposure_hours": 0,
        "reading_count": 10,
        "data_quality_status": "OBSERVED",
        "latitude": 28.61393,
        "longitude": 77.20877,
        "last_reading_at": "2026-11-26T09:50:00Z",
        "is_assumption_based": True,
        "source_reading_count": 10,
        "missing_temperature_reading_count": 0,
        "missing_humidity_reading_count": 0,
        "missing_temperature_interval_count": 0,
        "missing_temperature_interval_hours": 0,
        "sensor_data_sufficient": True,
        "assessment_updated_at": "2026-11-26T09:55:00Z",
    }

    record.update(overrides)

    return validate_spoilage_assessment(
        record,
        evaluation_time_utc=EVALUATION_TIME,
        max_sensor_age_hours=1,
        max_assessment_age_hours=2,
        valid_container_products=CONTAINER_PRODUCTS,
        valid_products=PRODUCTS,
    )


def run_integration(assessment, **overrides):
    arguments = {
        "shipment": SHIPMENT,
        "assessment": assessment,
        "planned_route": PLANNED_ROUTE,
        "alternative_route": ALTERNATIVE_ROUTE,
        "price_records": PRICES,
        "as_of_date": "2026-11-25",
    }

    arguments.update(overrides)

    return evaluate_with_spoilage_assessment(**arguments)


def test_valid_high_risk_assessment_reaches_arbitrage_engine():
    result = run_integration(make_assessment())

    assert result.status == "EVALUATED_PROTOTYPE"
    assert result.decision is not None
    assert result.decision.status == "REROUTE_RECOMMENDED"


def test_arbitrage_uses_remaining_shelf_life_from_assessment():
    result = run_integration(
        make_assessment(remaining_shelf_life_hours=1)
    )

    assert result.status == "EVALUATED_PROTOTYPE"
    assert result.decision.alternative_remaining_at_arrival_hours == 0


def test_normal_risk_does_not_trigger_draft_reroute_rule():
    result = run_integration(
        make_assessment(risk_level="NORMAL")
    )

    assert result.status == "EVALUATED_PROTOTYPE"
    assert result.decision.status == "KEEP_PLANNED_ROUTE"


def test_missing_humidity_blocks_arbitrage_calculation():
    result = run_integration(
        make_assessment(missing_humidity_reading_count=1)
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.decision is None
    assert "MISSING_HUMIDITY_READINGS" in result.reason_codes
def test_unknown_exposure_blocks_arbitrage_calculation():
    result = run_integration(
        make_assessment(unknown_exposure_hours=0.5)
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.decision is None


@pytest.mark.parametrize(
    ("container_id", "reading_count"),
    [
        ("TEST_MISSING_HUM_001", 4),
        ("TEST_MISSING_TEMP_001", 3),
    ],
)
def test_current_snowflake_mart_rows_are_blocked(
    container_id,
    reading_count,
):
    # Represents the existing Snowflake mart schema.
    # Values isolate the schema-compatibility check.
    current_mart_row = {
        "container_id": container_id,
        "product_name": "Apple",
        "latest_temperature_c": 3.0,
        "latest_humidity_pct": 90.0,
        "initial_shelf_life_hours": 720.0,
        "cumulative_aged_hours": 0.004167,
        "remaining_shelf_life_hours": 719.995833,
        "remaining_shelf_life_pct": 99.9994,
        "risk_level": "NORMAL",
        "unknown_exposure_hours": 0.0,
        "reading_count": reading_count,
        "data_quality_status": "OBSERVED",
        "latitude": 28.61393,
        "longitude": 77.20877,
        "last_reading_at": "2026-11-26T09:50:00Z",
        "is_assumption_based": True,
    }

    assessment = validate_spoilage_assessment(
        current_mart_row,
        evaluation_time_utc=EVALUATION_TIME,
        max_sensor_age_hours=1,
        max_assessment_age_hours=2,
        valid_container_products=CONTAINER_PRODUCTS,
        valid_products=PRODUCTS,
    )

    assert assessment.status == "INSUFFICIENT_DATA"

    required_missing_fields = [
        "source_reading_count",
        "missing_temperature_reading_count",
        "missing_humidity_reading_count",
        "missing_temperature_interval_count",
        "missing_temperature_interval_hours",
        "sensor_data_sufficient",
        "assessment_updated_at",
    ]

    for field in required_missing_fields:
        assert (
            f"MISSING_REQUIRED_FIELD:{field}"
            in assessment.reason_codes
        )

    result = run_integration(assessment)

    assert result.status == "INSUFFICIENT_DATA"
    assert result.decision is None

def test_assessment_container_mismatch_blocks_evaluation():
    assessment = make_assessment(
        container_id="CONT002",
        product_name="Banana",
    )

    result = run_integration(assessment)

    assert result.status == "INSUFFICIENT_DATA"
    assert "ASSESSMENT_SHIPMENT_CONTAINER_MISMATCH" in result.reason_codes


def test_assessment_product_mismatch_blocks_evaluation():
    assessment = make_assessment(
        container_id="CONT001",
        product_name="Banana",
    )

    result = run_integration(assessment)

    assert result.status == "INSUFFICIENT_DATA"
    assert "CONTAINER_PRODUCT_MISMATCH" in result.reason_codes


def test_missing_price_still_blocks_with_insufficient_data():
    result = run_integration(
        make_assessment(),
        price_records=PRICES[:1],
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.decision is not None
    assert result.decision.status == "INSUFFICIENT_DATA"
    assert "No price found" in result.decision.reason
def test_prototype_qualification_is_preserved():
    result = run_integration(make_assessment())

    assert result.prototype_only is True
    assert result.decision.status == "REROUTE_RECOMMENDED"


def test_non_assessment_object_is_rejected():
    with pytest.raises(ValueError, match="SpoilageAssessmentResult"):
        run_integration({"container_id": "CONT001"})


def test_invalid_route_input_is_not_silently_accepted():
    route = dict(ALTERNATIVE_ROUTE)
    route["currency"] = "USD"

    with pytest.raises(ValueError, match="INR"):
        run_integration(
            make_assessment(),
            alternative_route=route,
        )
