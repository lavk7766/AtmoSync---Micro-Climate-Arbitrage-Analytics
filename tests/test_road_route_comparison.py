from scripts.build_road_route_comparison import (
    build_road_route_comparison_matrix,
)


def test_all_eleven_road_candidates_are_compared():
    assert len(build_road_route_comparison_matrix()) == 11


def test_all_comparisons_have_matching_origins():
    rows = build_road_route_comparison_matrix()

    for row in rows:
        assert row["origin"]
        assert row["planned_destination"]
        assert row["candidate_market"]


def test_all_route_comparisons_use_same_osrm_profile():
    rows = build_road_route_comparison_matrix()

    for row in rows:
        assert row["routing_profile"] == "driving"


def test_network_distance_deltas_are_correct():
    rows = build_road_route_comparison_matrix()

    row = next(
        item for item in rows
        if item["container_id"] == "CONT001"
        and item["candidate_market"] == "Bengaluru"
    )

    assert float(row["additional_distance_km"]) == 1534.490
    assert row["route_comparison_status"] == "COMPARISON_COMPLETE"


def test_cont003_solapur_compares_against_osrm_baseline():
    rows = build_road_route_comparison_matrix()

    row = next(
        item for item in rows
        if item["container_id"] == "CONT003"
        and item["candidate_market"] == "Solapur"
    )

    assert float(row["additional_distance_km"]) == 261.945


def test_gross_uplift_budget_is_not_called_actual_profit():
    rows = build_road_route_comparison_matrix()

    for row in rows:
        assert row["gross_uplift_budget_before_quality_and_other_costs_inr"]
        assert "quality deterioration" in row["route_limitation"]


def test_break_even_cost_per_km_is_only_populated_for_longer_routes():
    rows = build_road_route_comparison_matrix()

    for row in rows:
        delta = float(row["additional_distance_km"])
        amount = row[
            "theoretical_break_even_incremental_transport_cost_per_extra_km_inr"
        ]

        if delta > 0:
            assert amount != ""
            assert float(amount) >= 0
        else:
            assert amount == ""


def test_original_route_quality_is_preserved():
    rows = build_road_route_comparison_matrix()

    cont001 = next(
        row for row in rows if row["container_id"] == "CONT001"
    )
    cont003 = next(
        row for row in rows if row["container_id"] == "CONT003"
    )

    assert cont001["original_planned_route_quality"] == (
        "network_route_geometry"
    )
    assert cont003["original_planned_route_quality"] == (
        "illustrative_waypoints"
    )


def test_no_operational_transport_cost_is_invented():
    rows = build_road_route_comparison_matrix()

    for row in rows:
        assert "transport_cost_inr" not in row
        assert "not truck-specific" in row["route_limitation"]


def test_all_successful_routes_are_marked_complete():
    rows = build_road_route_comparison_matrix()

    assert all(
        row["route_comparison_status"] == "COMPARISON_COMPLETE"
        for row in rows
    )
