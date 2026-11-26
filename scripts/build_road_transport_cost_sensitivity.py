"""Road transport-cost sensitivity analysis for AtmoSync.

Rates are hypothetical test parameters, not real freight quotations.
The model applies a linear cost to signed additional network distance.
It excludes spoilage, acquisition, tolls, handling and other costs.
"""

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_route_comparison.csv"
)

OUTPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "road_transport_cost_sensitivity.csv"
)

# Configurable sensitivity inputs only; not observed freight tariffs.
COST_RATES_INR_PER_KM = [
    5.0, 10.0, 15.0, 20.0, 25.0,
    30.0, 40.0, 50.0, 60.0, 75.0,
]

FIELDS = [
    "container_id",
    "product_name",
    "origin",
    "planned_destination",
    "candidate_market",
    "gross_sales_value_difference_inr",
    "planned_osrm_distance_km",
    "candidate_osrm_distance_km",
    "additional_distance_km",
    "additional_travel_hours",
    "theoretical_break_even_cost_per_extra_km_inr",
    "hypothetical_incremental_cost_rate_inr_per_km",
    "hypothetical_incremental_distance_cost_inr",
    "residual_gross_uplift_after_distance_cost_inr",
    "screening_status",
    "cost_model_type",
    "cost_assumption_note",
    "excluded_factors",
]


def read_comparisons(path=INPUT_FILE):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("Road route comparison file is empty.")

    return rows


def finite_number(value, name):
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc

    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")

    return number


def calculate_sensitivity(comparisons, rates=COST_RATES_INR_PER_KM):
    if not comparisons:
        raise ValueError("At least one comparison is required.")

    rates = list(rates)

    if not rates:
        raise ValueError("At least one cost rate is required.")

    normalized_rates = []

    for rate in rates:
        rate = finite_number(rate, "cost rate")

        if rate < 0:
            raise ValueError("Cost rates cannot be negative.")

        normalized_rates.append(rate)

    if len(normalized_rates) != len(set(normalized_rates)):
        raise ValueError("Cost rates must be unique.")

    output = []
    seen = set()

    for row in comparisons:
        if row.get("route_comparison_status") != "COMPARISON_COMPLETE":
            raise ValueError(
                "Sensitivity requires completed route comparisons."
            )

        container_id = row["container_id"]
        candidate_market = row["candidate_market"]

        pair = (container_id, candidate_market.casefold())

        if pair in seen:
            raise ValueError(f"Duplicate candidate: {pair}")

        seen.add(pair)

        gross_uplift = finite_number(
            row["gross_sales_value_difference_inr"],
            "gross price uplift",
        )

        planned_distance = finite_number(
            row["planned_osrm_distance_km"],
            "planned distance",
        )

        candidate_distance = finite_number(
            row["candidate_osrm_distance_km"],
            "candidate distance",
        )

        additional_distance = finite_number(
            row["additional_distance_km"],
            "additional distance",
        )

        additional_time = finite_number(
            row["additional_travel_hours"],
            "additional travel time",
        )

        recalculated_delta = candidate_distance - planned_distance

        if not math.isclose(
            additional_distance,
            recalculated_delta,
            rel_tol=0,
            abs_tol=0.002,
        ):
            raise ValueError(
                f"Distance delta mismatch for {container_id}/{candidate_market}"
            )

        if additional_distance > 0:
            break_even = gross_uplift / additional_distance
        else:
            break_even = None

        for rate in normalized_rates:
            # Signed difference: a shorter alternative route produces
            # a negative incremental distance cost under this model.
            incremental_cost = additional_distance * rate

            residual = gross_uplift - incremental_cost

            if residual > 0:
                status = "POSITIVE_BEFORE_QUALITY_AND_OTHER_COSTS"
            else:
                status = "UPLIFT_CONSUMED_OR_NEGATIVE"

            output.append({
                "container_id": container_id,
                "product_name": row["product_name"],
                "origin": row["origin"],
                "planned_destination": row["planned_destination"],
                "candidate_market": candidate_market,
                "gross_sales_value_difference_inr": f"{gross_uplift:.2f}",
                "planned_osrm_distance_km": f"{planned_distance:.3f}",
                "candidate_osrm_distance_km": f"{candidate_distance:.3f}",
                "additional_distance_km": f"{additional_distance:.3f}",
                "additional_travel_hours": f"{additional_time:.3f}",
                "theoretical_break_even_cost_per_extra_km_inr": (
                    f"{break_even:.4f}" if break_even is not None else ""
                ),
                "hypothetical_incremental_cost_rate_inr_per_km": (
                    f"{rate:.2f}"
                ),
                "hypothetical_incremental_distance_cost_inr": (
                    f"{incremental_cost:.2f}"
                ),
                "residual_gross_uplift_after_distance_cost_inr": (
                    f"{residual:.2f}"
                ),
                "screening_status": status,
                "cost_model_type": "linear_incremental_distance_sensitivity",
                "cost_assumption_note": (
                    "Hypothetical test parameter only; not an actual "
                    "freight tariff or provider quotation."
                ),
                "excluded_factors": (
                    "Spoilage, quality deterioration, acquisition cost, "
                    "tolls, loading, unloading, handling, return load, "
                    "vehicle type, fixed charges and time-based costs."
                ),
            })

    return output


def main():
    comparisons = read_comparisons()
    results = calculate_sensitivity(comparisons)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    print("\n========== ROAD COST SENSITIVITY ==========")
    print("Road candidates:", len(comparisons))
    print("Hypothetical cost rates:", COST_RATES_INR_PER_KM)
    print("Cost scenarios:", len(COST_RATES_INR_PER_KM))
    print("Total sensitivity records:", len(results))

    print("\n========== RESULTS BY COST RATE ==========")

    for rate in COST_RATES_INR_PER_KM:
        rows = [
            row for row in results
            if float(
                row["hypothetical_incremental_cost_rate_inr_per_km"]
            ) == rate
        ]

        positive = sum(
            row["screening_status"]
            == "POSITIVE_BEFORE_QUALITY_AND_OTHER_COSTS"
            for row in rows
        )

        print(
            f"INR {rate:.2f}/extra km: "
            f"{positive}/{len(rows)} candidates retain positive "
            "gross uplift before quality and other costs"
        )

    print("\n========== TOP CANDIDATES AT INR 10/KM ==========")

    rate_rows = [
        row for row in results
        if float(
            row["hypothetical_incremental_cost_rate_inr_per_km"]
        ) == 10.0
    ]

    rate_rows.sort(
        key=lambda row: float(
            row["residual_gross_uplift_after_distance_cost_inr"]
        ),
        reverse=True,
    )

    for row in rate_rows[:5]:
        print(
            row["container_id"],
            row["origin"],
            "->",
            row["candidate_market"],
            "| Residual gross uplift INR",
            row["residual_gross_uplift_after_distance_cost_inr"],
        )

    print("\nOutput:", OUTPUT_FILE)
    print("No route has been approved for operational rerouting.")


if __name__ == "__main__":
    main()
