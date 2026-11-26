import pytest

from scripts.build_shelf_life_adjusted_opportunity_sensitivity import (
    build_sensitivity_matrix,
    evaluate_quality_adjusted_scenario,
)


def test_quality_adjusted_scenario_matrix_has_1760_rows():
    rows = build_sensitivity_matrix()
    assert len(rows) == 1760


def test_matrix_covers_eleven_road_candidates():
    rows = build_sensitivity_matrix()

    pairs = {
        (row["container_id"], row["candidate_market"])
        for row in rows
    }

    assert len(pairs) == 11


def test_all_rows_use_synthetic_inr_price_inputs():
    rows = build_sensitivity_matrix()

    for row in rows:
        assert float(row["planned_price_inr_per_kg"]) > 0
        assert float(row["alternative_price_inr_per_kg"]) > 0


def test_aging_reduces_remaining_life_at_arrival():
    result = evaluate_quality_adjusted_scenario(
        planned_price=100,
        alternative_price=120,
        quantity_kg=100,
        planned_hours=10,
        alternative_hours=20,
        initial_shelf_life=100,
        remaining_fraction=1.0,
        aging_factor=1.0,
        additional_distance_km=100,
        cost_rate=5,
    )

    assert result["planned_remaining_at_arrival_hours"] == 90
    assert result["alternative_remaining_at_arrival_hours"] == 80


def test_higher_aging_factor_reduces_remaining_life():
    first = evaluate_quality_adjusted_scenario(
        planned_price=100,
        alternative_price=120,
        quantity_kg=100,
        planned_hours=10,
        alternative_hours=20,
        initial_shelf_life=100,
        remaining_fraction=1.0,
        aging_factor=1.0,
        additional_distance_km=100,
        cost_rate=5,
    )

    second = evaluate_quality_adjusted_scenario(
        planned_price=100,
        alternative_price=120,
        quantity_kg=100,
        planned_hours=10,
        alternative_hours=20,
        initial_shelf_life=100,
        remaining_fraction=1.0,
        aging_factor=1.5,
        additional_distance_km=100,
        cost_rate=5,
    )

    assert (
        second["alternative_remaining_at_arrival_hours"]
        < first["alternative_remaining_at_arrival_hours"]
    )


def test_no_remaining_shelf_life_means_zero_quality_proxy():
    result = evaluate_quality_adjusted_scenario(
        planned_price=100,
        alternative_price=120,
        quantity_kg=100,
        planned_hours=20,
        alternative_hours=30,
        initial_shelf_life=100,
        remaining_fraction=0.10,
        aging_factor=1.0,
        additional_distance_km=100,
        cost_rate=5,
    )

    assert result["planned_quality_proxy"] == 0
    assert result["alternative_quality_proxy"] == 0


def test_incremental_transport_cost_is_applied_to_distance_delta():
    result = evaluate_quality_adjusted_scenario(
        planned_price=100,
        alternative_price=120,
        quantity_kg=100,
        planned_hours=10,
        alternative_hours=20,
        initial_shelf_life=100,
        remaining_fraction=1.0,
        aging_factor=1.0,
        additional_distance_km=100,
        cost_rate=5,
    )

    assert result["hypothetical_incremental_distance_cost_inr"] == 500


def test_shorter_alternative_route_can_represent_distance_savings():
    result = evaluate_quality_adjusted_scenario(
        planned_price=100,
        alternative_price=100,
        quantity_kg=100,
        planned_hours=20,
        alternative_hours=10,
        initial_shelf_life=100,
        remaining_fraction=1.0,
        aging_factor=1.0,
        additional_distance_km=-100,
        cost_rate=5,
    )

    assert result["hypothetical_incremental_distance_cost_inr"] == -500


def test_invalid_remaining_life_fraction_is_rejected():
    with pytest.raises(ValueError):
        evaluate_quality_adjusted_scenario(
            planned_price=100,
            alternative_price=120,
            quantity_kg=100,
            planned_hours=10,
            alternative_hours=20,
            initial_shelf_life=100,
            remaining_fraction=1.2,
            aging_factor=1.0,
            additional_distance_km=100,
            cost_rate=5,
        )


def test_aging_factor_stress_is_retained_in_output():
    rows = build_sensitivity_matrix()

    assert {row["aging_factor"] for row in rows} == {"1.00", "1.50"}


def test_results_disclose_quality_proxy_assumption():
    rows = build_sensitivity_matrix()

    assert all(
        "not measured container condition" in row["assumption_note"]
        for row in rows
    )
