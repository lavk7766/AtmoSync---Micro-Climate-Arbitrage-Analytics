"""Enrich market opportunities with available OSRM route comparisons.

This script deliberately preserves the original opportunity rows and does not
invent freight prices. OSRM driving results are attached only to eligible road
shipments. Rail/sea shipments and non-positive price candidates receive explicit
statuses instead of being misrepresented as failed or completed road routes.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ARBITRAGE_DIR = DATA_DIR / "processed" / "arbitrage"

OPPORTUNITY_FILE = ARBITRAGE_DIR / "market_opportunity_screen.csv"
MATRIX_FILE = ARBITRAGE_DIR / "alternative_route_input_matrix.csv"
SCENARIO_FILE = DATA_DIR / "scenarios" / "shipment_scenarios.csv"
CANDIDATE_ROUTE_FILE = ARBITRAGE_DIR / "osrm_road_candidate_routes.csv"
PLANNED_BASELINE_FILE = ARBITRAGE_DIR / "osrm_road_planned_baselines.csv"
ROUTE_COMPARISON_FILE = ARBITRAGE_DIR / "osrm_road_route_comparison.csv"
OUTPUT_FILE = ARBITRAGE_DIR / "market_opportunity_route_enriched.csv"

OPPORTUNITY_KEY_FIELDS = (
    "screen_date",
    "scenario_id",
    "container_id",
    "product_name",
    "origin",
    "planned_destination",
    "candidate_market",
)
ROUTE_KEY_FIELDS = (
    "container_id",
    "product_name",
    "origin",
    "candidate_market",
)

EXTRA_FIELDS = [
    "shipment_transport_mode",
    "route_evaluation_status",
    "candidate_route_status",
    "planned_route_status",
    "route_comparison_status",
    "planned_osrm_distance_km",
    "candidate_osrm_distance_km",
    "additional_distance_km",
    "additional_distance_pct",
    "planned_osrm_duration_hours",
    "candidate_osrm_duration_hours",
    "additional_travel_hours",
    "gross_uplift_budget_before_quality_and_other_costs_inr",
    "theoretical_break_even_incremental_transport_cost_per_extra_km_inr",
    "routing_profile",
    "route_source_type",
    "route_limitation",
    "planned_route_retrieved_at_utc",
    "candidate_route_retrieved_at_utc",
    "verified_transport_cost_inr",
    "verified_transport_cost_currency",
    "verified_transport_cost_source",
    "transport_cost_status",
]

COMPARISON_COPY_FIELDS = (
    "planned_osrm_distance_km",
    "candidate_osrm_distance_km",
    "additional_distance_km",
    "additional_distance_pct",
    "planned_osrm_duration_hours",
    "candidate_osrm_duration_hours",
    "additional_travel_hours",
    "gross_uplift_budget_before_quality_and_other_costs_inr",
    "theoretical_break_even_incremental_transport_cost_per_extra_km_inr",
    "routing_profile",
    "route_limitation",
    "planned_route_retrieved_at_utc",
    "candidate_route_retrieved_at_utc",
    "route_comparison_status",
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a non-empty CSV and return its header and records."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
        return list(reader.fieldnames), rows


def normalized(value: object) -> str:
    return str(value or "").strip().casefold()


def composite_key(row: dict[str, str], fields: Iterable[str]) -> tuple[str, ...]:
    return tuple(normalized(row.get(field, "")) for field in fields)


def unique_lookup(
    rows: list[dict[str, str]],
    key_function: Callable[[dict[str, str]], tuple[str, ...]],
    label: str,
) -> dict[tuple[str, ...], dict[str, str]]:
    lookup: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = key_function(row)
        if key in lookup:
            raise ValueError(f"Duplicate {label} key: {key}")
        lookup[key] = row
    return lookup


def require_fields(
    rows: list[dict[str, str]],
    fields: Iterable[str],
    label: str,
) -> None:
    if not rows:
        return
    available = set(rows[0])
    missing = sorted(set(fields) - available)
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def classify_route(
    *,
    price_status: str,
    transport_mode: str,
    comparison: dict[str, str] | None,
    candidate_route: dict[str, str] | None,
    baseline: dict[str, str] | None,
) -> str:
    """Return a transparent reason/status for each opportunity row."""
    if normalized(price_status) != "positive_price_candidate":
        return "NOT_PRIORITIZED_NO_PRICE_PREMIUM"

    if normalized(transport_mode) != "road":
        return "NOT_ROUTED_NON_ROAD_MODE"

    if comparison and normalized(comparison.get("route_comparison_status")) == "comparison_complete":
        if (
            normalized(comparison.get("planned_osrm_route_status")) == "route_ok"
            and normalized(comparison.get("candidate_osrm_route_status")) == "route_ok"
        ):
            return "ROUTE_COMPARISON_COMPLETE"

    if candidate_route is None:
        return "ROAD_CANDIDATE_ROUTE_RESULT_MISSING"

    if normalized(candidate_route.get("route_status")) != "route_ok":
        return "CANDIDATE_ROUTE_UNAVAILABLE"

    if baseline is None:
        return "PLANNED_BASELINE_MISSING"

    if normalized(baseline.get("route_status")) != "route_ok":
        return "PLANNED_BASELINE_UNAVAILABLE"

    return "ROUTE_COMPARISON_NOT_COMPLETED"


def build_enriched_opportunities(
    opportunities: list[dict[str, str]],
    matrix: list[dict[str, str]],
    scenarios: list[dict[str, str]],
    candidate_routes: list[dict[str, str]],
    baselines: list[dict[str, str]],
    comparisons: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Join route evidence to all market opportunities without losing rows."""
    require_fields(opportunities, OPPORTUNITY_KEY_FIELDS, "Market opportunity screen")
    require_fields(matrix, (*OPPORTUNITY_KEY_FIELDS, "price_candidate_status"), "Alternative route matrix")
    require_fields(scenarios, ("container_id", "transport_mode"), "Shipment scenarios")
    require_fields(candidate_routes, (*ROUTE_KEY_FIELDS, "route_status"), "OSRM candidate routes")
    require_fields(baselines, ("container_id", "route_status"), "OSRM planned baselines")
    require_fields(comparisons, (*ROUTE_KEY_FIELDS, "route_comparison_status"), "OSRM route comparisons")

    opportunity_lookup = unique_lookup(
        opportunities,
        lambda row: composite_key(row, OPPORTUNITY_KEY_FIELDS),
        "market opportunity",
    )
    matrix_lookup = unique_lookup(
        matrix,
        lambda row: composite_key(row, OPPORTUNITY_KEY_FIELDS),
        "alternative matrix",
    )

    if set(opportunity_lookup) != set(matrix_lookup):
        missing_matrix = sorted(set(opportunity_lookup) - set(matrix_lookup))
        missing_opportunity = sorted(set(matrix_lookup) - set(opportunity_lookup))
        raise ValueError(
            "Opportunity/matrix keys do not match. "
            f"Missing from matrix={missing_matrix[:5]}; "
            f"missing from opportunity screen={missing_opportunity[:5]}"
        )

    scenario_lookup = unique_lookup(
        scenarios,
        lambda row: (normalized(row.get("container_id")),),
        "shipment scenario container",
    )
    candidate_lookup = unique_lookup(
        candidate_routes,
        lambda row: composite_key(row, ROUTE_KEY_FIELDS),
        "candidate route",
    )
    baseline_lookup = unique_lookup(
        baselines,
        lambda row: (normalized(row.get("container_id")),),
        "planned baseline container",
    )
    comparison_lookup = unique_lookup(
        comparisons,
        lambda row: composite_key(row, ROUTE_KEY_FIELDS),
        "route comparison",
    )

    output: list[dict[str, str]] = []

    for opportunity in opportunities:
        opportunity_key = composite_key(opportunity, OPPORTUNITY_KEY_FIELDS)
        matrix_row = matrix_lookup[opportunity_key]
        container_key = (normalized(opportunity.get("container_id")),)
        scenario = scenario_lookup.get(container_key)
        if scenario is None:
            raise ValueError(
                f"Missing shipment scenario for container {opportunity.get('container_id')}"
            )

        route_key = composite_key(opportunity, ROUTE_KEY_FIELDS)
        candidate_route = candidate_lookup.get(route_key)
        baseline = baseline_lookup.get(container_key)
        comparison = comparison_lookup.get(route_key)
        transport_mode = scenario.get("transport_mode", "").strip()
        route_status = classify_route(
            price_status=matrix_row.get("price_candidate_status", ""),
            transport_mode=transport_mode,
            comparison=comparison,
            candidate_route=candidate_route,
            baseline=baseline,
        )

        row = dict(opportunity)
        row.update({field: "" for field in EXTRA_FIELDS})
        row["shipment_transport_mode"] = transport_mode
        row["route_evaluation_status"] = route_status
        row["candidate_route_status"] = (
            candidate_route.get("route_status", "") if candidate_route else "NOT_REQUESTED"
        )
        row["planned_route_status"] = (
            baseline.get("route_status", "") if baseline else "NOT_AVAILABLE"
        )

        if comparison:
            for field in COMPARISON_COPY_FIELDS:
                row[field] = comparison.get(field, "")

        if route_status == "ROUTE_COMPARISON_COMPLETE":
            row["route_source_type"] = "OSRM_PUBLIC_DRIVING"
            row["transport_cost_status"] = "NO_VERIFIED_FREIGHT_RATE"
        elif route_status == "NOT_ROUTED_NON_ROAD_MODE":
            row["route_source_type"] = "NOT_APPLICABLE_OSRM_DRIVING_PROFILE"
            row["transport_cost_status"] = "NOT_MODELED_FOR_NON_ROAD_MODE"
        elif route_status == "NOT_PRIORITIZED_NO_PRICE_PREMIUM":
            row["route_source_type"] = "NOT_REQUESTED_NO_PRICE_PREMIUM"
            row["transport_cost_status"] = "NOT_APPLICABLE_NO_PRICE_PREMIUM"
        else:
            row["route_source_type"] = "ROAD_ROUTE_NOT_VERIFIED"
            row["transport_cost_status"] = "UNAVAILABLE_PENDING_ROUTE_OR_RATE_VALIDATION"

        # No verified freight tariff is present in the supplied route files.
        # Keep these fields blank rather than importing hypothetical sensitivity rates.
        row["verified_transport_cost_inr"] = ""
        row["verified_transport_cost_currency"] = ""
        row["verified_transport_cost_source"] = ""
        output.append(row)

    return output


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    opportunity_fields, opportunities = read_csv(OPPORTUNITY_FILE)
    _, matrix = read_csv(MATRIX_FILE)
    _, scenarios = read_csv(SCENARIO_FILE)
    _, candidate_routes = read_csv(CANDIDATE_ROUTE_FILE)
    _, baselines = read_csv(PLANNED_BASELINE_FILE)
    _, comparisons = read_csv(ROUTE_COMPARISON_FILE)

    enriched = build_enriched_opportunities(
        opportunities=opportunities,
        matrix=matrix,
        scenarios=scenarios,
        candidate_routes=candidate_routes,
        baselines=baselines,
        comparisons=comparisons,
    )

    fields = opportunity_fields + [field for field in EXTRA_FIELDS if field not in opportunity_fields]
    write_csv(OUTPUT_FILE, fields, enriched)

    print("\n========== ROUTE-ENRICHED OPPORTUNITY OUTPUT ==========")
    print("Input market opportunities:", len(opportunities))
    print("Output market opportunities:", len(enriched))
    print("Rows preserved:", len(opportunities) == len(enriched))

    counts: dict[str, int] = {}
    for row in enriched:
        status = row["route_evaluation_status"]
        counts[status] = counts.get(status, 0) + 1

    print("\nRoute evaluation status:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    complete = counts.get("ROUTE_COMPARISON_COMPLETE", 0)
    non_road = counts.get("NOT_ROUTED_NON_ROAD_MODE", 0)
    no_premium = counts.get("NOT_PRIORITIZED_NO_PRICE_PREMIUM", 0)
    print("\nCompleted OSRM comparisons:", complete)
    print("Positive candidates intentionally not routed by OSRM:", non_road)
    print("Candidates not prioritized due to price:", no_premium)
    print("Verified freight costs populated:", sum(bool(row["verified_transport_cost_inr"]) for row in enriched))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
