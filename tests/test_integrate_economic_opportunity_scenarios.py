import pytest

from scripts.integrate_economic_opportunity_scenarios import (
    IntegrationError,
    build_coverage_register,
    build_integrated_analysis,
)


def route_row(**overrides):
    row = {
        "screen_date": "2026-11-25",
        "scenario_id": "SHIP-CONT001-BASELINE",
        "container_id": "CONT001",
        "product_name": "Apple",
        "quantity_kg": "1000",
        "origin": "Delhi",
        "planned_destination": "Lucknow",
        "candidate_market": "Bengaluru",
        "planned_price_inr_per_kg": "150",
        "candidate_price_inr_per_kg": "186.35",
        "price_source_type": "synthetic_simulated",
        "gross_sales_value_difference_inr": "36350",
        "route_evaluation_status": "ROUTE_COMPARISON_COMPLETE",
        "route_comparison_status": "COMPARISON_COMPLETE",
        "planned_osrm_distance_km": "534.0",
        "candidate_osrm_distance_km": "2150.0",
        "additional_distance_km": "1616.0",
        "additional_distance_pct": "302.62",
        "planned_osrm_duration_hours": "8.9",
        "candidate_osrm_duration_hours": "35.0",
        "additional_travel_hours": "26.1",
        "routing_profile": "driving",
        "route_limitation": "City-level proxies; not truck-specific or live traffic.",
        "planned_route_retrieved_at_utc": "2026-11-25T07:29:56+00:00",
        "candidate_route_retrieved_at_utc": "2026-11-25T07:23:47+00:00",
        "verified_transport_cost_inr": "",
        "transport_cost_status": "NOT_AVAILABLE",
    }
    row.update(overrides)
    return row


def transport_row(**overrides):
    row = {
        "container_id": "CONT001",
        "product_name": "Apple",
        "origin": "Delhi",
        "planned_destination": "Lucknow",
        "candidate_market": "Bengaluru",
        "gross_sales_value_difference_inr": "36350.00",
        "planned_osrm_distance_km": "534.000",
        "candidate_osrm_distance_km": "2150.000",
        "additional_distance_km": "1616.000",
        "additional_travel_hours": "26.100",
        "hypothetical_incremental_cost_rate_inr_per_km": "5.00",
        "hypothetical_incremental_distance_cost_inr": "8080.00",
        "residual_gross_uplift_after_distance_cost_inr": "28270.00",
        "screening_status": "POSITIVE_BEFORE_QUALITY_AND_OTHER_COSTS",
        "cost_model_type": "linear_incremental_distance_sensitivity",
        "cost_assumption_note": "Hypothetical only.",
        "excluded_factors": "Spoilage, tolls and handling.",
    }
    row.update(overrides)
    return row


def shelf_row(**overrides):
    row = {
        "container_id": "CONT001",
        "product_name": "Apple",
        "planned_destination": "Lucknow",
        "candidate_market": "Bengaluru",
        "quantity_kg": "1000",
        "shelf_life_reference_source": "Product reference dataset",
        "shelf_life_scenario": "CONSERVATIVE_MINIMUM",
        "initial_shelf_life_hours": "720",
        "remaining_life_fraction": "1.0",
        "aging_factor": "1.0",
        "cost_rate_inr_per_extra_km": "5.0",
        "planned_osrm_duration_hours": "8.9",
        "alternative_osrm_duration_hours": "35.0",
        "additional_distance_km": "1616.0",
        "remaining_at_evaluation_hours": "720",
        "planned_remaining_at_arrival_hours": "711.1",
        "alternative_remaining_at_arrival_hours": "685.0",
        "planned_quality_proxy": "0.9876",
        "alternative_quality_proxy": "0.9514",
        "planned_value_after_transport_inr": "148140.00",
        "alternative_value_after_transport_inr": "177410.00",
        "quality_adjusted_value_difference_inr": "29270.00",
        "hypothetical_incremental_distance_cost_inr": "8080.00",
        "residual_value_difference_inr": "21190.00",
        "screening_status": "POSITIVE_AFTER_QUALITY_PROXY_AND_DISTANCE_COST",
        "assumption_note": "Illustrative shelf-life and quality proxy assumptions.",
    }
    row.update(overrides)
    return row


def minimal_sources():
    return [route_row()], [transport_row()], [shelf_row()]


def test_builds_integrated_economic_scenario_with_provenance_flags():
    routes, costs, shelf = minimal_sources()
    result = build_integrated_analysis(routes, costs, shelf)

    assert len(result) == 1
    row = result[0]
    assert row["economic_scenario_status"] == "POSITIVE_UNDER_HYPOTHETICAL_ASSUMPTIONS"
    assert row["commercial_profitability_verified"] == "NO"
    assert row["verified_freight_cost_status"] == "NOT_AVAILABLE"
    assert row["evidence_classification"].startswith("SYNTHETIC_MARKET_PRICES")


def test_rejects_missing_cost_scenario():
    routes, costs, shelf = minimal_sources()
    with pytest.raises(IntegrationError, match="transport-cost sensitivity has no rows"):
        build_integrated_analysis(routes, [], shelf)


def test_rejects_duplicate_shelf_life_scenario():
    routes, costs, shelf = minimal_sources()
    with pytest.raises(IntegrationError, match="Duplicate shelf-life scenario"):
        build_integrated_analysis(routes, costs, shelf + shelf)


def test_rejects_mismatched_incremental_cost_between_models():
    routes, costs, shelf = minimal_sources()
    shelf[0]["hypothetical_incremental_distance_cost_inr"] = "9000"
    with pytest.raises(IntegrationError, match="hypothetical incremental distance cost"):
        build_integrated_analysis(routes, costs, shelf)


def test_rejects_incomplete_scenario_grid_across_routes():
    routes, costs, shelf = minimal_sources()
    second_route = route_row(
        container_id="CONT003",
        scenario_id="SHIP-CONT003-BASELINE",
        origin="Bengaluru",
        planned_destination="Kurnool",
        candidate_market="Patna",
    )
    # Only route and transport inputs for the second key; shelf dimensions
    # remain absent, so full scenario coverage must fail closed.
    second_cost = transport_row(
        container_id="CONT003",
        origin="Bengaluru",
        planned_destination="Kurnool",
        candidate_market="Patna",
    )
    with pytest.raises(IntegrationError, match="Shelf-life route coverage mismatch"):
        build_integrated_analysis(routes + [second_route], costs + [second_cost], shelf)


def test_coverage_register_preserves_nonroad_and_nonprioritized_opportunities():
    routes, costs, shelf = minimal_sources()
    integrated = build_integrated_analysis(routes, costs, shelf)
    opportunities = routes + [
        route_row(
            container_id="CONT002",
            scenario_id="SHIP-CONT002",
            origin="Mumbai",
            planned_destination="Pune",
            candidate_market="Bengaluru",
            route_evaluation_status="NOT_ROUTED_NON_ROAD_MODE",
            route_comparison_status="",
        ),
        route_row(
            container_id="CONT004",
            scenario_id="SHIP-CONT004",
            origin="Mumbai",
            planned_destination="Pune",
            candidate_market="Kolkata",
            route_evaluation_status="NOT_PRIORITIZED_NO_PRICE_PREMIUM",
            route_comparison_status="",
        ),
    ]
    coverage = build_coverage_register(opportunities, integrated)

    assert len(coverage) == 3
    assert coverage[0]["economic_scenario_rows_generated"] == 1
    assert coverage[1]["economic_coverage_status"] == "NON_ROAD_MODE_REQUIRES_MODE_SPECIFIC_ROUTING"
    assert coverage[2]["economic_coverage_status"] == "NOT_EVALUATED_NO_POSITIVE_PRICE_PREMIUM"
