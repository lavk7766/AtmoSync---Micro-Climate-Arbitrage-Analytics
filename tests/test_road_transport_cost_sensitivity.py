import pytest

from scripts.build_road_transport_cost_sensitivity import (
    COST_RATES_INR_PER_KM,
    calculate_sensitivity,
    read_comparisons,
)


def test_ten_cost_scenarios_are_configured():
    assert len(COST_RATES_INR_PER_KM) == 10


def test_sensitivity_creates_110_records():
    comparisons = read_comparisons()
    results = calculate_sensitivity(comparisons)

    assert len(comparisons) == 11
    assert len(results) == 110


def test_candidate_pairs_are_repeated_only_across_cost_scenarios():
    results = calculate_sensitivity(read_comparisons())

    pairs = {
        (row["container_id"], row["candidate_market"])
        for row in results
    }

    assert len(pairs) == 11


def test_cost_sensitivity_uses_signed_additional_distance():
    comparison = read_comparisons()
    results = calculate_sensitivity(comparison, rates=[10.0])

    row = next(
        item for item in results
        if item["container_id"] == "CONT001"
        and item["candidate_market"] == "Bengaluru"
    )

    assert float(
        row["hypothetical_incremental_distance_cost_inr"]
    ) == pytest.approx(15344.90, abs=0.02)

    assert float(
        row["residual_gross_uplift_after_distance_cost_inr"]
    ) == pytest.approx(21005.10, abs=0.02)


def test_break_even_ceiling_matches_gross_uplift_over_extra_distance():
    results = calculate_sensitivity(read_comparisons(), rates=[10.0])

    row = next(
        item for item in results
        if item["container_id"] == "CONT001"
        and item["candidate_market"] == "Bengaluru"
    )

    expected = 36350.0 / 1534.490

    assert float(
        row["theoretical_break_even_cost_per_extra_km_inr"]
    ) == pytest.approx(expected, abs=0.0001)


def test_hypothetical_rates_are_not_labelled_actual_tariffs():
    results = calculate_sensitivity(read_comparisons(), rates=[10.0])

    for row in results:
        assert "not an actual" in row["cost_assumption_note"]
        assert row["cost_model_type"] == (
            "linear_incremental_distance_sensitivity"
        )


def test_negative_rate_is_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_sensitivity(read_comparisons(), rates=[-1.0])


def test_duplicate_rates_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        calculate_sensitivity(read_comparisons(), rates=[10.0, 10.0])


def test_failed_route_comparison_is_rejected():
    rows = read_comparisons()
    rows[0]["route_comparison_status"] = "ROUTE_DATA_PENDING"

    with pytest.raises(ValueError, match="completed"):
        calculate_sensitivity(rows)


def test_distance_delta_is_revalidated():
    rows = read_comparisons()
    rows[0]["additional_distance_km"] = "999999"

    with pytest.raises(ValueError, match="delta mismatch"):
        calculate_sensitivity(rows)
