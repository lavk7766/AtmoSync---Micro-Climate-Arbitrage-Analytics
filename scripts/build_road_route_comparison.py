"""Compare OSRM alternative routes against OSRM planned baselines.

All calculations are preliminary screening metrics. OSRM driving
estimates are not truck-specific freight routes or actual cost quotes.
"""

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_FILE = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_candidate_routes.csv"
)

BASELINE_FILE = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_planned_baselines.csv"
)

OUTPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_route_comparison.csv"
)

FIELDS = [
    "container_id",
    "product_name",
    "origin",
    "planned_destination",
    "candidate_market",
    "gross_sales_value_difference_inr",
    "original_planned_route_quality",
    "original_planned_distance_km",
    "original_planned_duration_hours",
    "planned_osrm_distance_km",
    "candidate_osrm_distance_km",
    "additional_distance_km",
    "additional_distance_pct",
    "planned_osrm_duration_hours",
    "candidate_osrm_duration_hours",
    "additional_travel_hours",
    "gross_uplift_budget_before_quality_and_other_costs_inr",
    "theoretical_break_even_incremental_transport_cost_per_extra_km_inr",
    "planned_osrm_route_status",
    "candidate_osrm_route_status",
    "routing_profile",
    "route_limitation",
    "planned_route_retrieved_at_utc",
    "candidate_route_retrieved_at_utc",
]


def read_csv(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"No records found: {path}")

    return rows


def finite_number(value, label):
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid numeric value for {label}") from exc

    if not math.isfinite(number):
        raise ValueError(f"Non-finite numeric value for {label}")

    return number


def build_road_route_comparison_matrix(
    candidate_path=CANDIDATE_FILE,
    baseline_path=BASELINE_FILE,
):
    candidates = read_csv(candidate_path)
    baselines = read_csv(baseline_path)

    baseline_lookup = {}

    for row in baselines:
        container_id = row["container_id"]

        if container_id in baseline_lookup:
            raise ValueError(
                f"Duplicate planned baseline: {container_id}"
            )

        baseline_lookup[container_id] = row

    seen_pairs = set()
    output = []

    for candidate in candidates:
        container_id = candidate["container_id"]
        market = candidate["candidate_market"]

        pair = (container_id, market.casefold())

        if pair in seen_pairs:
            raise ValueError(f"Duplicate candidate route: {pair}")

        seen_pairs.add(pair)

        baseline = baseline_lookup.get(container_id)

        if baseline is None:
            raise ValueError(
                f"Missing planned OSRM baseline: {container_id}"
            )

        if (
            candidate["origin"].casefold()
            != baseline["origin"].casefold()
        ):
            raise ValueError(
                f"Candidate and baseline origins differ: {container_id}"
            )

        row = {
            "container_id": container_id,
            "product_name": candidate["product_name"],
            "origin": candidate["origin"],
            "planned_destination": baseline["planned_destination"],
            "candidate_market": market,
            "gross_sales_value_difference_inr": candidate[
                "gross_sales_value_difference_inr"
            ],
            "original_planned_route_quality": baseline[
                "original_route_quality"
            ],
            "original_planned_distance_km": baseline[
                "original_distance_km"
            ],
            "original_planned_duration_hours": baseline[
                "original_duration_hours"
            ],
            "planned_osrm_distance_km": "",
            "candidate_osrm_distance_km": "",
            "additional_distance_km": "",
            "additional_distance_pct": "",
            "planned_osrm_duration_hours": "",
            "candidate_osrm_duration_hours": "",
            "additional_travel_hours": "",
            "gross_uplift_budget_before_quality_and_other_costs_inr": "",
            "theoretical_break_even_incremental_transport_cost_per_extra_km_inr": "",
            "planned_osrm_route_status": baseline["route_status"],
            "candidate_osrm_route_status": candidate["route_status"],
            "routing_profile": "driving",
            "route_limitation": (
                "OSRM public driving profile; city-level coordinate proxies; "
                "not truck-specific and not live traffic. Gross uplift ignores "
                "quality deterioration and other costs."
            ),
            "planned_route_retrieved_at_utc": baseline.get(
                "retrieved_at_utc", ""
            ),
            "candidate_route_retrieved_at_utc": candidate.get(
                "retrieved_at_utc", ""
            ),
        }

        if (
            baseline["route_status"] != "ROUTE_OK"
            or candidate["route_status"] != "ROUTE_OK"
        ):
            row["route_comparison_status"] = "ROUTE_DATA_PENDING"
            output.append(row)
            continue

        planned_distance = finite_number(
            baseline["network_distance_km"],
            "planned OSRM distance",
        )

        candidate_distance = finite_number(
            candidate["network_distance_km"],
            "candidate OSRM distance",
        )

        planned_duration = finite_number(
            baseline["estimated_duration_hours"],
            "planned OSRM duration",
        )

        candidate_duration = finite_number(
            candidate["estimated_duration_hours"],
            "candidate OSRM duration",
        )

        gross_uplift = finite_number(
            candidate["gross_sales_value_difference_inr"],
            "gross price uplift",
        )

        if min(
            planned_distance,
            candidate_distance,
            planned_duration,
            candidate_duration,
        ) <= 0:
            raise ValueError(
                f"Route distance and duration must be positive: {pair}"
            )

        additional_distance = candidate_distance - planned_distance

        additional_distance_pct = (
            additional_distance / planned_distance * 100
        )

        additional_hours = candidate_duration - planned_duration

        if gross_uplift > 0:
            gross_budget = gross_uplift
        else:
            gross_budget = 0.0

        # Only defined for longer alternative routes.
        # This is a theoretical ceiling, not a quoted transport rate.
        if additional_distance > 0:
            break_even_per_km = gross_budget / additional_distance
        else:
            break_even_per_km = None

        row.update({
            "planned_osrm_distance_km": f"{planned_distance:.3f}",
            "candidate_osrm_distance_km": f"{candidate_distance:.3f}",
            "additional_distance_km": f"{additional_distance:.3f}",
            "additional_distance_pct": f"{additional_distance_pct:.2f}",
            "planned_osrm_duration_hours": f"{planned_duration:.3f}",
            "candidate_osrm_duration_hours": f"{candidate_duration:.3f}",
            "additional_travel_hours": f"{additional_hours:.3f}",
            "gross_uplift_budget_before_quality_and_other_costs_inr": (
                f"{gross_budget:.2f}"
            ),
            "theoretical_break_even_incremental_transport_cost_per_extra_km_inr": (
                f"{break_even_per_km:.2f}"
                if break_even_per_km is not None else ""
            ),
            "route_comparison_status": "COMPARISON_COMPLETE",
        })

        output.append(row)

    output.sort(
        key=lambda row: (
            row["container_id"],
            row["candidate_market"].casefold(),
        )
    )

    return output


def main():
    records = build_road_route_comparison_matrix()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fields = FIELDS + ["route_comparison_status"]

    with OUTPUT_FILE.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    complete = [
        row for row in records
        if row["route_comparison_status"] == "COMPARISON_COMPLETE"
    ]

    print("\n========== OSRM ROAD ROUTE COMPARISON ==========")
    print("Candidate comparisons:", len(records))
    print("Completed comparisons:", len(complete))
    print("Pending comparisons:", len(records) - len(complete))

    print("\n========== TOP ROUTE COMPARISONS ==========")

    for row in sorted(
        complete,
        key=lambda item: float(
            item["gross_sales_value_difference_inr"]
        ),
        reverse=True,
    )[:7]:
        print(
            f'{row["container_id"]}: '
            f'{row["origin"]} -> {row["candidate_market"]} | '
            f'Extra distance: {row["additional_distance_km"]} km | '
            f'Extra time: {row["additional_travel_hours"]} hours | '
            f'Gross uplift: INR '
            f'{row["gross_sales_value_difference_inr"]} | '
            f'Theoretical INR/km ceiling: '
            f'{row["theoretical_break_even_incremental_transport_cost_per_extra_km_inr"]}'
        )

    print("\nOutput:", OUTPUT_FILE)
    print(
        "Reminder: the break-even figure is not an actual transport rate, "
        "and excludes quality deterioration and all other costs."
    )


if __name__ == "__main__":
    main()
