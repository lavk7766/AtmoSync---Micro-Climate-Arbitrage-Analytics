"""Integrate route, transport-cost and shelf-life sensitivity outputs.

This produces scenario-level analytical outputs, not verified commercial profits.
All price, shelf-life and transport assumptions retain their source labels.
"""

from __future__ import annotations

import csv
import itertools
import math
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

ROUTE_FILE = (
    ROOT / "data/processed/arbitrage/market_opportunity_route_enriched.csv"
)
TRANSPORT_FILE = (
    ROOT / "data/processed/arbitrage/road_transport_cost_sensitivity.csv"
)
SHELF_LIFE_FILE = (
    ROOT / "data/processed/arbitrage/"
    "shelf_life_adjusted_opportunity_sensitivity.csv"
)

OUTPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "integrated_economic_opportunity_analysis.csv"
)
COVERAGE_OUTPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "integrated_economic_opportunity_coverage.csv"
)

ROUTE_KEY_FIELDS = (
    "container_id",
    "product_name",
    "planned_destination",
    "candidate_market",
)

SHELF_DIMENSIONS = (
    "shelf_life_scenario",
    "remaining_life_fraction",
    "aging_factor",
    "cost_rate_inr_per_extra_km",
)

NUMERIC_TOLERANCE = 0.03


class IntegrationError(ValueError):
    """Raised when source datasets cannot be safely integrated."""


def read_csv(path: Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise IntegrationError(f"Input file is empty: {path}")
    return rows


def normalized(value: object, field: str) -> str:
    result = str(value or "").strip().casefold()
    if not result:
        raise IntegrationError(f"Missing key field: {field}")
    return result


def route_key(row: dict[str, object]) -> tuple[str, ...]:
    return tuple(normalized(row.get(field), field) for field in ROUTE_KEY_FIELDS)


def finite_number(value: object, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise IntegrationError(f"{label} must be numeric; got {value!r}") from exc
    if not math.isfinite(result):
        raise IntegrationError(f"{label} must be finite; got {value!r}")
    return result


def close_enough(left: object, right: object, label: str) -> None:
    a = finite_number(left, f"{label} (left)")
    b = finite_number(right, f"{label} (right)")
    if not math.isclose(a, b, rel_tol=0.0, abs_tol=NUMERIC_TOLERANCE):
        raise IntegrationError(
            f"Inconsistent {label}: {a} versus {b} "
            f"(tolerance {NUMERIC_TOLERANCE})"
        )


def require_columns(
    rows: list[dict[str, str]], required: Iterable[str], label: str
) -> None:
    if not rows:
        raise IntegrationError(f"{label} has no rows")
    available = set(rows[0])
    missing = sorted(set(required) - available)
    if missing:
        raise IntegrationError(f"{label} missing required columns: {missing}")


def scenario_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        normalized(row.get("shelf_life_scenario"), "shelf_life_scenario"),
        finite_number(row.get("remaining_life_fraction"), "remaining_life_fraction"),
        finite_number(row.get("aging_factor"), "aging_factor"),
        finite_number(row.get("cost_rate_inr_per_extra_km"), "cost_rate_inr_per_extra_km"),
    )


def cost_key(row: dict[str, object]) -> tuple[tuple[str, ...], float]:
    return (
        route_key(row),
        finite_number(
            row.get("hypothetical_incremental_cost_rate_inr_per_km"),
            "hypothetical_incremental_cost_rate_inr_per_km",
        ),
    )


def build_integrated_analysis(
    opportunity_rows: list[dict[str, str]],
    transport_rows: list[dict[str, str]],
    shelf_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    """Join all scenario rows to their route and cost evidence with strict checks."""

    require_columns(
        opportunity_rows,
        [
            *ROUTE_KEY_FIELDS,
            "route_evaluation_status",
            "route_comparison_status",
            "gross_sales_value_difference_inr",
            "quantity_kg",
            "planned_osrm_distance_km",
            "candidate_osrm_distance_km",
            "additional_distance_km",
            "planned_osrm_duration_hours",
            "candidate_osrm_duration_hours",
            "additional_travel_hours",
        ],
        "route-enriched opportunities",
    )
    require_columns(
        transport_rows,
        [
            *ROUTE_KEY_FIELDS,
            "hypothetical_incremental_cost_rate_inr_per_km",
            "hypothetical_incremental_distance_cost_inr",
            "residual_gross_uplift_after_distance_cost_inr",
            "planned_osrm_distance_km",
            "candidate_osrm_distance_km",
            "additional_distance_km",
            "additional_travel_hours",
            "gross_sales_value_difference_inr",
        ],
        "transport-cost sensitivity",
    )
    require_columns(
        shelf_rows,
        [
            *ROUTE_KEY_FIELDS,
            "quantity_kg",
            *SHELF_DIMENSIONS,
            "planned_osrm_duration_hours",
            "alternative_osrm_duration_hours",
            "additional_distance_km",
            "quality_adjusted_value_difference_inr",
            "hypothetical_incremental_distance_cost_inr",
            "residual_value_difference_inr",
            "screening_status",
        ],
        "shelf-life sensitivity",
    )

    # Only completed road comparisons can enter this scenario analysis.
    route_lookup: dict[tuple[str, ...], dict[str, str]] = {}
    for row in opportunity_rows:
        if row.get("route_evaluation_status") != "ROUTE_COMPARISON_COMPLETE":
            continue
        if row.get("route_comparison_status") != "COMPARISON_COMPLETE":
            raise IntegrationError(
                f"Route marked complete but comparison is not complete: {route_key(row)}"
            )
        key = route_key(row)
        if key in route_lookup:
            raise IntegrationError(f"Duplicate completed opportunity route: {key}")
        route_lookup[key] = row

    if not route_lookup:
        raise IntegrationError("No completed route opportunities available")

    transport_lookup: dict[tuple[tuple[str, ...], float], dict[str, str]] = {}
    transport_rates_by_route: dict[tuple[str, ...], set[float]] = {}
    for row in transport_rows:
        key = cost_key(row)
        if key[0] not in route_lookup:
            raise IntegrationError(f"Transport sensitivity has unmatched route: {key[0]}")
        if key in transport_lookup:
            raise IntegrationError(f"Duplicate transport cost scenario: {key}")
        transport_lookup[key] = row
        transport_rates_by_route.setdefault(key[0], set()).add(key[1])

    shelf_lookup: dict[tuple[tuple[str, ...], tuple[object, ...]], dict[str, str]] = {}
    shelf_dimensions_by_route: dict[tuple[str, ...], set[tuple[object, ...]]] = {}
    all_dimension_values = [set() for _ in SHELF_DIMENSIONS]
    for row in shelf_rows:
        key = route_key(row)
        if key not in route_lookup:
            raise IntegrationError(f"Shelf-life sensitivity has unmatched route: {key}")
        dimensions = scenario_key(row)
        compound = (key, dimensions)
        if compound in shelf_lookup:
            raise IntegrationError(f"Duplicate shelf-life scenario: {compound}")
        shelf_lookup[compound] = row
        shelf_dimensions_by_route.setdefault(key, set()).add(dimensions)
        for index, value in enumerate(dimensions):
            all_dimension_values[index].add(value)

    expected_routes = set(route_lookup)
    if set(transport_rates_by_route) != expected_routes:
        missing = expected_routes - set(transport_rates_by_route)
        extra = set(transport_rates_by_route) - expected_routes
        raise IntegrationError(
            f"Transport route coverage mismatch; missing={missing}, extra={extra}"
        )
    if set(shelf_dimensions_by_route) != expected_routes:
        missing = expected_routes - set(shelf_dimensions_by_route)
        extra = set(shelf_dimensions_by_route) - expected_routes
        raise IntegrationError(
            f"Shelf-life route coverage mismatch; missing={missing}, extra={extra}"
        )

    # A full rectangular scenario grid is required for every routed opportunity.
    expected_dimensions = set(itertools.product(*all_dimension_values))
    if not expected_dimensions:
        raise IntegrationError("No shelf-life scenario dimensions found")

    for key in expected_routes:
        actual = shelf_dimensions_by_route[key]
        if actual != expected_dimensions:
            raise IntegrationError(
                f"Incomplete shelf-life scenario grid for {key}: "
                f"expected {len(expected_dimensions)}, got {len(actual)}"
            )
        expected_rates = {
            float(item[3]) for item in expected_dimensions
        }
        if transport_rates_by_route[key] != expected_rates:
            raise IntegrationError(
                f"Transport/shelf-life cost-rate mismatch for {key}"
            )

    expected_transport_keys = {
        (route, rate)
        for route, rates in transport_rates_by_route.items()
        for rate in rates
    }
    if set(transport_lookup) != expected_transport_keys:
        raise IntegrationError("Transport sensitivity contains unexpected or missing rate scenarios")

    results: list[dict[str, object]] = []
    for (key, dimensions), shelf in shelf_lookup.items():
        route = route_lookup[key]
        shelf_scenario, remaining_fraction, aging_factor, cost_rate = dimensions
        cost = transport_lookup.get((key, float(cost_rate)))
        if cost is None:
            raise IntegrationError(f"Missing transport-cost scenario for {key}, rate={cost_rate}")

        # Validate that all three sources describe the same physical route.
        close_enough(
            route["gross_sales_value_difference_inr"],
            cost["gross_sales_value_difference_inr"],
            "gross sales value difference",
        )
        close_enough(route["quantity_kg"], shelf["quantity_kg"], "shipment quantity")
        close_enough(route["planned_osrm_distance_km"], cost["planned_osrm_distance_km"], "planned route distance")
        close_enough(route["candidate_osrm_distance_km"], cost["candidate_osrm_distance_km"], "candidate route distance")
        close_enough(route["additional_distance_km"], cost["additional_distance_km"], "transport additional distance")
        close_enough(route["additional_distance_km"], shelf["additional_distance_km"], "shelf-life additional distance")
        close_enough(route["planned_osrm_duration_hours"], shelf["planned_osrm_duration_hours"], "planned route duration")
        close_enough(route["candidate_osrm_duration_hours"], shelf["alternative_osrm_duration_hours"], "candidate route duration")
        close_enough(route["additional_travel_hours"], cost["additional_travel_hours"], "additional route travel time")

        # The transport and shelf-life models must apply the same signed
        # incremental-distance cost at the same hypothetical rate.
        expected_incremental_cost = (
            finite_number(route["additional_distance_km"], "route additional distance")
            * float(cost_rate)
        )
        close_enough(
            cost["hypothetical_incremental_distance_cost_inr"],
            expected_incremental_cost,
            "transport sensitivity distance-cost formula",
        )
        close_enough(
            cost["hypothetical_incremental_distance_cost_inr"],
            shelf["hypothetical_incremental_distance_cost_inr"],
            "hypothetical incremental distance cost",
        )

        # Validate the price uplift against the unit price difference when
        # those fields are present in the route-enriched source.
        if route.get("planned_price_inr_per_kg") not in (None, "") and route.get("candidate_price_inr_per_kg") not in (None, ""):
            unit_price_delta = (
                finite_number(route["candidate_price_inr_per_kg"], "candidate unit price")
                - finite_number(route["planned_price_inr_per_kg"], "planned unit price")
            )
            expected_gross_uplift = (
                unit_price_delta * finite_number(route["quantity_kg"], "shipment quantity")
            )
            close_enough(
                route["gross_sales_value_difference_inr"],
                expected_gross_uplift,
                "gross uplift from market unit prices",
            )

        quality_difference = finite_number(
            shelf["quality_adjusted_value_difference_inr"],
            "quality-adjusted value difference",
        )
        incremental_cost = finite_number(
            shelf["hypothetical_incremental_distance_cost_inr"],
            "shelf-life hypothetical incremental distance cost",
        )
        residual = finite_number(
            shelf["residual_value_difference_inr"],
            "residual value difference",
        )
        close_enough(
            residual,
            quality_difference - incremental_cost,
            "shelf-life residual value difference formula",
        )

        gross_residual = finite_number(
            cost["residual_gross_uplift_after_distance_cost_inr"],
            "residual gross uplift",
        )
        expected_gross_residual = (
            finite_number(cost["gross_sales_value_difference_inr"], "gross uplift")
            - finite_number(cost["hypothetical_incremental_distance_cost_inr"], "cost sensitivity amount")
        )
        close_enough(gross_residual, expected_gross_residual, "transport sensitivity residual formula")

        if residual > 0:
            economic_status = "POSITIVE_UNDER_HYPOTHETICAL_ASSUMPTIONS"
        else:
            economic_status = "NOT_POSITIVE_UNDER_HYPOTHETICAL_ASSUMPTIONS"

        result: dict[str, object] = {
            "screen_date": route.get("screen_date", ""),
            "scenario_id": route.get("scenario_id", ""),
            "container_id": route["container_id"],
            "product_name": route["product_name"],
            "quantity_kg": route["quantity_kg"],
            "origin": route.get("origin", ""),
            "planned_destination": route["planned_destination"],
            "candidate_market": route["candidate_market"],
            "price_source_type": route.get("price_source_type", ""),
            "planned_price_inr_per_kg": route.get("planned_price_inr_per_kg", ""),
            "candidate_price_inr_per_kg": route.get("candidate_price_inr_per_kg", ""),
            "gross_sales_value_difference_inr": route["gross_sales_value_difference_inr"],
            "route_evaluation_status": route.get("route_evaluation_status", ""),
            "route_comparison_status": route.get("route_comparison_status", ""),
            "planned_osrm_distance_km": route["planned_osrm_distance_km"],
            "candidate_osrm_distance_km": route["candidate_osrm_distance_km"],
            "additional_distance_km": route["additional_distance_km"],
            "additional_distance_pct": route.get("additional_distance_pct", ""),
            "planned_osrm_duration_hours": route["planned_osrm_duration_hours"],
            "candidate_osrm_duration_hours": route["candidate_osrm_duration_hours"],
            "additional_travel_hours": route["additional_travel_hours"],
            "routing_profile": route.get("routing_profile", ""),
            "route_limitation": route.get("route_limitation", ""),
            "planned_route_retrieved_at_utc": route.get("planned_route_retrieved_at_utc", ""),
            "candidate_route_retrieved_at_utc": route.get("candidate_route_retrieved_at_utc", ""),
            "shelf_life_reference_source": shelf.get("shelf_life_reference_source", ""),
            "shelf_life_scenario": shelf_scenario,
            "initial_shelf_life_hours": shelf.get("initial_shelf_life_hours", ""),
            "remaining_life_fraction": remaining_fraction,
            "aging_factor": aging_factor,
            "remaining_at_evaluation_hours": shelf.get("remaining_at_evaluation_hours", ""),
            "planned_remaining_at_arrival_hours": shelf.get("planned_remaining_at_arrival_hours", ""),
            "alternative_remaining_at_arrival_hours": shelf.get("alternative_remaining_at_arrival_hours", ""),
            "planned_quality_proxy": shelf.get("planned_quality_proxy", ""),
            "alternative_quality_proxy": shelf.get("alternative_quality_proxy", ""),
            "planned_value_after_transport_inr": shelf.get("planned_value_after_transport_inr", ""),
            "alternative_value_after_transport_inr": shelf.get("alternative_value_after_transport_inr", ""),
            "quality_adjusted_value_difference_inr": shelf["quality_adjusted_value_difference_inr"],
            "transport_cost_model_type": cost.get("cost_model_type", ""),
            "hypothetical_incremental_cost_rate_inr_per_km": cost_rate,
            "hypothetical_incremental_distance_cost_inr": cost["hypothetical_incremental_distance_cost_inr"],
            "residual_gross_uplift_after_distance_cost_inr": cost["residual_gross_uplift_after_distance_cost_inr"],
            "residual_value_difference_inr": shelf["residual_value_difference_inr"],
            "transport_cost_sensitivity_status": cost.get("screening_status", ""),
            "shelf_life_sensitivity_status": shelf.get("screening_status", ""),
            "economic_scenario_status": economic_status,
            "verified_freight_cost_inr": route.get("verified_transport_cost_inr", ""),
            "verified_freight_cost_status": route.get("transport_cost_status", "NOT_AVAILABLE") or "NOT_AVAILABLE",
            "commercial_profitability_verified": "NO",
            "evidence_classification": "SYNTHETIC_MARKET_PRICES_AND_HYPOTHETICAL_SHELF_LIFE_AND_TRANSPORT_COST_SCENARIO",
            "assumption_note": shelf.get("assumption_note", ""),
            "transport_cost_assumption_note": cost.get("cost_assumption_note", ""),
            "excluded_transport_cost_factors": cost.get("excluded_factors", ""),
        }
        results.append(result)

    results.sort(
        key=lambda row: (
            str(row["container_id"]).casefold(),
            str(row["candidate_market"]).casefold(),
            str(row["shelf_life_scenario"]).casefold(),
            float(row["remaining_life_fraction"]),
            float(row["aging_factor"]),
            float(row["hypothetical_incremental_cost_rate_inr_per_km"]),
        )
    )

    expected_count = len(route_lookup) * len(expected_dimensions)
    if len(results) != expected_count:
        raise IntegrationError(
            f"Unexpected integrated row count: expected {expected_count}, got {len(results)}"
        )
    return results


def build_coverage_register(
    opportunity_rows: list[dict[str, str]],
    integrated_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    counts: Counter[tuple[str, ...]] = Counter(route_key(row) for row in integrated_rows)
    output: list[dict[str, object]] = []

    for row in opportunity_rows:
        status = row.get("route_evaluation_status", "")
        scenario_count = counts[route_key(row)]
        if status == "ROUTE_COMPARISON_COMPLETE":
            if scenario_count == 0:
                raise IntegrationError(f"Completed route lacks economic scenarios: {route_key(row)}")
            coverage_status = "HYPOTHETICAL_SENSITIVITY_GENERATED"
        elif status == "NOT_ROUTED_NON_ROAD_MODE":
            if scenario_count:
                raise IntegrationError(f"Non-road opportunity unexpectedly has road scenarios: {route_key(row)}")
            coverage_status = "NON_ROAD_MODE_REQUIRES_MODE_SPECIFIC_ROUTING"
        elif status == "NOT_PRIORITIZED_NO_PRICE_PREMIUM":
            if scenario_count:
                raise IntegrationError(f"Non-positive price opportunity unexpectedly has scenarios: {route_key(row)}")
            coverage_status = "NOT_EVALUATED_NO_POSITIVE_PRICE_PREMIUM"
        else:
            if scenario_count:
                raise IntegrationError(f"Pending opportunity unexpectedly has scenarios: {route_key(row)}")
            coverage_status = "NOT_EVALUATED_ROUTE_OR_DATA_PENDING"

        record: dict[str, object] = dict(row)
        record["economic_scenario_rows_generated"] = scenario_count
        record["economic_coverage_status"] = coverage_status
        record["commercial_profitability_verified"] = "NO"
        output.append(record)
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise IntegrationError(f"Refusing to write empty output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    opportunities = read_csv(ROUTE_FILE)
    transport = read_csv(TRANSPORT_FILE)
    shelf_life = read_csv(SHELF_LIFE_FILE)

    integrated = build_integrated_analysis(opportunities, transport, shelf_life)
    coverage = build_coverage_register(opportunities, integrated)

    write_csv(OUTPUT_FILE, integrated)
    write_csv(COVERAGE_OUTPUT_FILE, coverage)

    status_counts = Counter(str(row["economic_scenario_status"]) for row in integrated)
    coverage_counts = Counter(str(row["economic_coverage_status"]) for row in coverage)

    print("\n========== INTEGRATED ECONOMIC OPPORTUNITY ANALYSIS ==========")
    print("Route-enriched opportunity rows:", len(opportunities))
    print("Economic scenario rows:", len(integrated))
    print("Unique completed routes:", len({route_key(row) for row in integrated}))
    print("Scenario records per route:", len(integrated) // len({route_key(row) for row in integrated}))
    print("\nEconomic scenario status:")
    for label, count in sorted(status_counts.items()):
        print(f"  {label}: {count}")
    print("\n35-row coverage register:")
    for label, count in sorted(coverage_counts.items()):
        print(f"  {label}: {count}")
    print("\nVerified commercial freight costs: 0 (none supplied)")
    print("Commercial profitability verified: NO")
    print("Scenario output:", OUTPUT_FILE)
    print("Coverage output:", COVERAGE_OUTPUT_FILE)


if __name__ == "__main__":
    main()
