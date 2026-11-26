import pytest

from simulator.arbitrage_engine import (
    evaluate_reroute_option,
    load_market_price_records,
)


SHIPMENT = {
    "container_id": "CONT001",
    "product_name": "Apple",
    "quantity": 1000,
    "quantity_unit": "kg",
    "origin": "Delhi",
}

PLANNED_ROUTE = {
    "origin": "Delhi",
    "destination": "Lucknow",
    "distance_km": 500.0,
    "estimated_travel_hours": 2.0,
    "transport_cost": 1000.0,
    "currency": "INR",
    "source_type": "synthetic_simulated",
}

ALTERNATIVE_ROUTE = {
    "origin": "Delhi",
    "destination": "Bengaluru",
    "distance_km": 600.0,
    "estimated_travel_hours": 1.0,
    "transport_cost": 500.0,
    "currency": "INR",
    "source_type": "synthetic_simulated",
}

PRICES = [
    {
        "product_name": "Apple",
        "market_name": "Lucknow",
        "simulated_as_of_date": "2026-11-25",
        "price_per_kg": "150.00",
        "currency": "INR",
        "quantity_unit": "kg",
        "price_source_type": "synthetic_simulated",
    },
    {
        "product_name": "Apple",
        "market_name": "Bengaluru",
        "simulated_as_of_date": "2026-11-25",
        "price_per_kg": "180.00",
        "currency": "INR",
        "quantity_unit": "kg",
        "price_source_type": "synthetic_simulated",
    },
]


def evaluate(**overrides):
    arguments = {
        "shipment": SHIPMENT,
        "planned_route": PLANNED_ROUTE,
        "alternative_route": ALTERNATIVE_ROUTE,
        "price_records": PRICES,
        "as_of_date": "2026-11-25",
        "remaining_shelf_life_hours": 24.0,
        "initial_shelf_life_hours": 96.0,
        "expected_aging_factor": 1.0,
        "risk_level": "HIGH_RISK",
        "sensor_data_sufficient": True,
    }
    arguments.update(overrides)
    return evaluate_reroute_option(**arguments)


def test_high_risk_higher_alternative_value_recommends_reroute():
    result = evaluate()

    assert result.status == "REROUTE_RECOMMENDED"
    assert result.alternative_value_after_transport_inr > (
        result.planned_value_after_transport_inr
    )


def test_non_high_risk_keeps_planned_route():
    result = evaluate(risk_level="NORMAL")

    assert result.status == "KEEP_PLANNED_ROUTE"
    assert result.alternative_value_difference_inr > 0


def test_insufficient_sensor_data_blocks_decision():
    result = evaluate(sensor_data_sufficient=False)

    assert result.status == "INSUFFICIENT_DATA"
    assert result.planned_value_after_transport_inr is None


def test_missing_alternative_price_returns_insufficient_data():
    result = evaluate(price_records=PRICES[:1])

    assert result.status == "INSUFFICIENT_DATA"
    assert "No price found" in result.reason


def test_wrong_currency_returns_insufficient_data():
    records = [
        dict(record)
        for record in PRICES
    ]
    records[1]["currency"] = "USD"

    result = evaluate(price_records=records)

    assert result.status == "INSUFFICIENT_DATA"
    assert "INR" in result.reason


def test_wrong_price_unit_returns_insufficient_data():
    records = [
        dict(record)
        for record in PRICES
    ]
    records[1]["quantity_unit"] = "tonne"

    result = evaluate(price_records=records)

    assert result.status == "INSUFFICIENT_DATA"
    assert "per kg" in result.reason


def test_duplicate_market_price_returns_insufficient_data():
    records = PRICES + [dict(PRICES[1])]

    result = evaluate(price_records=records)

    assert result.status == "INSUFFICIENT_DATA"
    assert "Multiple matching prices" in result.reason


def test_expired_alternative_route_does_not_recommend_reroute():
    result = evaluate(
        remaining_shelf_life_hours=1.0,
    )

    assert result.status == "KEEP_PLANNED_ROUTE"
    assert result.alternative_remaining_at_arrival_hours == 0.0


def test_alternative_with_lower_value_keeps_planned_route():
    records = [
        dict(record)
        for record in PRICES
    ]
    records[1]["price_per_kg"] = "100.00"

    expensive_alternative = dict(ALTERNATIVE_ROUTE)
    expensive_alternative["transport_cost"] = 10000.0

    result = evaluate(
        price_records=records,
        alternative_route=expensive_alternative,
    )

    assert result.status == "KEEP_PLANNED_ROUTE"
    assert result.alternative_value_difference_inr < 0


def test_tonne_shipment_quantity_is_converted_to_kg():
    shipment = dict(SHIPMENT)
    shipment["quantity"] = 1
    shipment["quantity_unit"] = "tonne"

    result = evaluate(shipment=shipment)

    assert result.quantity_kg == 1000.0


def test_price_date_must_match_requested_date():
    result = evaluate(as_of_date="2026-11-26")

    assert result.status == "INSUFFICIENT_DATA"
    assert "No price found" in result.reason


def test_invalid_alternative_route_origin_is_rejected():
    route = dict(ALTERNATIVE_ROUTE)
    route["origin"] = "Mumbai"

    with pytest.raises(ValueError, match="origin"):
        evaluate(alternative_route=route)


def test_route_cost_currency_must_be_inr():
    route = dict(ALTERNATIVE_ROUTE)
    route["currency"] = "USD"

    with pytest.raises(ValueError, match="INR"):
        evaluate(alternative_route=route)


def test_route_cost_cannot_be_negative():
    route = dict(ALTERNATIVE_ROUTE)
    route["transport_cost"] = -100.0

    with pytest.raises(ValueError, match="cannot be negative"):
        evaluate(alternative_route=route)


def test_unsupported_shipment_unit_is_rejected():
    shipment = dict(SHIPMENT)
    shipment["quantity_unit"] = "crate"

    with pytest.raises(ValueError, match="Unsupported"):
        evaluate(shipment=shipment)


def test_project_price_csv_can_be_loaded():
    records = load_market_price_records()

    assert len(records) == 45
    assert all(
        record["price_source_type"] == "synthetic_simulated"
        for record in records
    )

def test_csv_string_shipment_quantity_is_converted_to_kg():
    shipment = dict(SHIPMENT)
    shipment["quantity"] = "1000"

    result = evaluate(shipment=shipment)

    assert result.quantity_kg == 1000.0
