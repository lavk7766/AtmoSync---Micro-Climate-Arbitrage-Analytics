import pytest

from scripts.integrate_osrm_routes_into_market_opportunities import build_enriched_opportunities


def make_opportunity(container, candidate, scenario="S1"):
    return {
        "screen_date": "2026-11-25",
        "scenario_id": scenario,
        "container_id": container,
        "product_name": "Apple",
        "origin": "Delhi" if container != "CONT002" else "Mumbai",
        "planned_destination": "Lucknow",
        "candidate_market": candidate,
        "gross_sales_value_difference_inr": "10000.00",
        "evaluation_status": "POSITIVE_PRICE_CANDIDATE_ROUTE_COST_QUALITY_PENDING",
    }


def make_matrix_row(opportunity, price_status="POSITIVE_PRICE_CANDIDATE"):
    return {**opportunity, "price_candidate_status": price_status}


def test_enriches_road_route_and_keeps_nonroad_and_no_premium_rows():
    road = make_opportunity("CONT001", "Bengaluru")
    rail = make_opportunity("CONT002", "Kolkata", "S2")
    no_premium = make_opportunity("CONT001", "Patna", "S3")
    opportunities = [road, rail, no_premium]

    scenarios = [
        {"container_id": "CONT001", "transport_mode": "road"},
        {"container_id": "CONT002", "transport_mode": "rail"},
    ]
    candidate_routes = [{
        "container_id": "CONT001", "product_name": "Apple", "origin": "Delhi",
        "candidate_market": "Bengaluru", "route_status": "ROUTE_OK",
    }]
    baselines = [{"container_id": "CONT001", "route_status": "ROUTE_OK"}]
    comparisons = [{
        "container_id": "CONT001", "product_name": "Apple", "origin": "Delhi",
        "candidate_market": "Bengaluru", "route_comparison_status": "COMPARISON_COMPLETE",
        "planned_osrm_route_status": "ROUTE_OK", "candidate_osrm_route_status": "ROUTE_OK",
        "planned_osrm_distance_km": "500.000", "candidate_osrm_distance_km": "2000.000",
        "additional_distance_km": "1500.000", "additional_distance_pct": "300.00",
        "planned_osrm_duration_hours": "8.000", "candidate_osrm_duration_hours": "30.000",
        "additional_travel_hours": "22.000",
        "gross_uplift_budget_before_quality_and_other_costs_inr": "10000.00",
        "theoretical_break_even_incremental_transport_cost_per_extra_km_inr": "6.67",
        "routing_profile": "driving", "route_limitation": "Not truck-specific",
        "planned_route_retrieved_at_utc": "2026-11-25T07:00:00+00:00",
        "candidate_route_retrieved_at_utc": "2026-11-25T07:01:00+00:00",
    }]

    matrix = [
        make_matrix_row(road),
        make_matrix_row(rail),
        make_matrix_row(no_premium, "NO_POSITIVE_PRICE_DIFFERENCE"),
    ]

    result = build_enriched_opportunities(
        opportunities, matrix, scenarios, candidate_routes, baselines, comparisons
    )

    assert len(result) == 3
    assert result[0]["route_evaluation_status"] == "ROUTE_COMPARISON_COMPLETE"
    assert result[0]["candidate_osrm_distance_km"] == "2000.000"
    assert result[0]["route_source_type"] == "OSRM_PUBLIC_DRIVING"
    assert result[0]["transport_cost_status"] == "NO_VERIFIED_FREIGHT_RATE"
    assert result[0]["verified_transport_cost_inr"] == ""

    assert result[1]["route_evaluation_status"] == "NOT_ROUTED_NON_ROAD_MODE"
    assert result[1]["route_source_type"] == "NOT_APPLICABLE_OSRM_DRIVING_PROFILE"

    assert result[2]["route_evaluation_status"] == "NOT_PRIORITIZED_NO_PRICE_PREMIUM"


def test_road_candidate_without_route_result_is_explicitly_unavailable():
    road = make_opportunity("CONT001", "Bengaluru")
    matrix = [make_matrix_row(road)]
    result = build_enriched_opportunities(
        [road], matrix,
        [{"container_id": "CONT001", "transport_mode": "road"}],
        [],
        [{"container_id": "CONT001", "route_status": "ROUTE_OK"}],
        [],
    )
    assert result[0]["route_evaluation_status"] == "ROAD_CANDIDATE_ROUTE_RESULT_MISSING"


def test_rejects_opportunity_matrix_key_mismatch():
    road = make_opportunity("CONT001", "Bengaluru")
    wrong_matrix_row = make_matrix_row(make_opportunity("CONT001", "Kolkata"))
    with pytest.raises(ValueError, match="keys do not match"):
        build_enriched_opportunities(
            [road], [wrong_matrix_row],
            [{"container_id": "CONT001", "transport_mode": "road"}],
            [], [], [],
        )


def test_rejects_duplicate_candidate_route_keys():
    road = make_opportunity("CONT001", "Bengaluru")
    candidate = {
        "container_id": "CONT001", "product_name": "Apple", "origin": "Delhi",
        "candidate_market": "Bengaluru", "route_status": "ROUTE_OK",
    }
    with pytest.raises(ValueError, match="Duplicate candidate route"):
        build_enriched_opportunities(
            [road], [make_matrix_row(road)],
            [{"container_id": "CONT001", "transport_mode": "road"}],
            [candidate, candidate],
            [{"container_id": "CONT001", "route_status": "ROUTE_OK"}],
            [],
        )
