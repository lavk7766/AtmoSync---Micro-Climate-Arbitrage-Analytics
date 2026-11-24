import pytest

from simulator.arbitrage_validation import (
    calculate_market_value,
    estimate_travel_hours,
    haversine_distance_km,
    is_reroute_recommended,
)


def test_haversine_distance_between_same_point_is_zero():
    distance = haversine_distance_km(
        (28.61393, 77.20877),
        (28.61393, 77.20877),
    )

    assert distance == pytest.approx(0.0)


def test_haversine_one_degree_at_equator_is_about_111_km():
    distance = haversine_distance_km(
        (0.0, 0.0),
        (0.0, 1.0),
    )

    assert distance == pytest.approx(111.195, abs=0.1)


def test_haversine_distance_is_symmetric():
    first = (28.61393, 77.20877)
    second = (27.17667, 78.00807)

    assert haversine_distance_km(first, second) == pytest.approx(
        haversine_distance_km(second, first)
    )


@pytest.mark.parametrize(
    "invalid_coordinate",
    [
        (91.0, 0.0),
        (0.0, 181.0),
        (float("nan"), 0.0),
        (True, 0.0),
    ],
)
def test_haversine_rejects_invalid_coordinates(invalid_coordinate):
    with pytest.raises(ValueError):
        haversine_distance_km(invalid_coordinate, (0.0, 0.0))


def test_estimate_travel_hours_uses_distance_divided_by_speed():
    assert estimate_travel_hours(120.0, 60.0) == pytest.approx(2.0)


@pytest.mark.parametrize(
    "distance, speed",
    [
        (-1.0, 60.0),
        (120.0, 0.0),
        (120.0, -5.0),
        (float("inf"), 60.0),
    ],
)
def test_estimate_travel_hours_rejects_invalid_inputs(distance, speed):
    with pytest.raises(ValueError):
        estimate_travel_hours(distance, speed)


def test_market_value_matches_documented_example_formula():
    result = calculate_market_value(
        price_per_kg=30.0,
        quantity_kg=1000.0,
        remaining_shelf_life_hours=4.0,
        initial_shelf_life_hours=96.0,
        travel_hours=2.0,
        expected_aging_factor=1.0,
        transport_cost=200.0,
    )

    assert result.remaining_at_arrival_hours == pytest.approx(2.0)
    assert result.quality_at_arrival == pytest.approx(2.0 / 96.0)
    assert result.expected_net_value == pytest.approx(425.0)


def test_market_value_is_zero_quality_when_arrival_exceeds_shelf_life():
    result = calculate_market_value(
        price_per_kg=30.0,
        quantity_kg=1000.0,
        remaining_shelf_life_hours=4.0,
        initial_shelf_life_hours=96.0,
        travel_hours=6.0,
        expected_aging_factor=1.0,
        transport_cost=200.0,
    )

    assert result.remaining_at_arrival_hours == pytest.approx(0.0)
    assert result.quality_at_arrival == pytest.approx(0.0)
    assert result.expected_net_value == pytest.approx(-200.0)


def test_market_value_accounts_for_expected_aging_factor():
    result = calculate_market_value(
        price_per_kg=30.0,
        quantity_kg=1000.0,
        remaining_shelf_life_hours=4.0,
        initial_shelf_life_hours=96.0,
        travel_hours=2.0,
        expected_aging_factor=2.0,
        transport_cost=200.0,
    )

    assert result.remaining_at_arrival_hours == pytest.approx(0.0)
    assert result.expected_net_value == pytest.approx(-200.0)


def test_market_value_rejects_missing_price():
    with pytest.raises(ValueError):
        calculate_market_value(
            price_per_kg=None,
            quantity_kg=1000.0,
            remaining_shelf_life_hours=4.0,
            initial_shelf_life_hours=96.0,
            travel_hours=2.0,
            expected_aging_factor=1.0,
            transport_cost=200.0,
        )


def test_market_value_rejects_remaining_life_above_initial_life():
    with pytest.raises(ValueError):
        calculate_market_value(
            price_per_kg=30.0,
            quantity_kg=1000.0,
            remaining_shelf_life_hours=100.0,
            initial_shelf_life_hours=96.0,
            travel_hours=2.0,
            expected_aging_factor=1.0,
            transport_cost=200.0,
        )


def test_reroute_is_recommended_when_all_draft_conditions_pass():
    assert is_reroute_recommended(
        risk_level="HIGH_RISK",
        alternative_remaining_at_arrival_hours=2.0,
        alternative_net_value=900.0,
        planned_destination_net_value=-150.0,
        sensor_data_sufficient=True,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"risk_level": "NORMAL"},
        {"risk_level": "WARNING"},
        {"alternative_remaining_at_arrival_hours": 0.0},
        {"alternative_net_value": 800.0},
        {"sensor_data_sufficient": False},
    ],
)
def test_reroute_is_not_recommended_when_a_condition_fails(overrides):
    arguments = {
        "risk_level": "HIGH_RISK",
        "alternative_remaining_at_arrival_hours": 2.0,
        "alternative_net_value": 900.0,
        "planned_destination_net_value": 800.0,
        "sensor_data_sufficient": True,
    }
    arguments.update(overrides)

    assert not is_reroute_recommended(**arguments)


def test_reroute_rejects_undefined_sensor_quality_flag():
    with pytest.raises(ValueError):
        is_reroute_recommended(
            risk_level="HIGH_RISK",
            alternative_remaining_at_arrival_hours=2.0,
            alternative_net_value=900.0,
            planned_destination_net_value=800.0,
            sensor_data_sufficient=None,
        )
