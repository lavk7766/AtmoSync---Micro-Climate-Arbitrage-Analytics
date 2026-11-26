"""Shelf-life-adjusted opportunity sensitivity for AtmoSync.

This is a prototype sensitivity model, not a food-safety or profit model.

The quality proxy is inherited from arbitrage_validation.py:
remaining shelf life at arrival / initial shelf life.

Shelf-life references, remaining-life fractions, aging factors and
distance-cost rates are scenario assumptions, not measured shipment state.
"""

import csv
import math
from pathlib import Path

from simulator.arbitrage_validation import calculate_market_value


ROOT = Path(__file__).resolve().parents[1]

ROUTES = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_route_comparison.csv"
)

PRICES = (
    ROOT / "data/processed/synthetic_market_prices/"
    "synthetic_local_market_prices.csv"
)

PRODUCTS = (
    ROOT / "data/reference/product_spoilage_reference.csv"
)

OUTPUT = (
    ROOT / "data/processed/arbitrage/"
    "shelf_life_adjusted_opportunity_sensitivity.csv"
)

REMAINING_LIFE_FRACTIONS = [0.25, 0.50, 0.75, 1.00]
AGING_FACTORS = [1.0, 1.5]
COST_RATES = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"No records in {path}")

    return rows


def number(value, label):
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid numeric value: {label}") from exc

    if not math.isfinite(result):
        raise ValueError(f"Non-finite numeric value: {label}")

    return result


def load_price_lookup():
    rows = read_csv(PRICES)
    lookup = {}

    for row in rows:
        if (
            row["currency"] != "INR"
            or row["quantity_unit"] != "kg"
            or row["price_source_type"] != "synthetic_simulated"
        ):
            raise ValueError("Unexpected price currency, unit or source.")

        key = (
            row["product_name"].strip().casefold(),
            row["market_name"].strip().casefold(),
            row["simulated_as_of_date"],
        )

        if key in lookup:
            raise ValueError(f"Duplicate market price: {key}")

        lookup[key] = number(row["price_per_kg"], "market price")

    return lookup


def load_shelf_life_reference():
    rows = read_csv(PRODUCTS)
    lookup = {}

    for row in rows:
        product = row["product_name"].strip().casefold()

        if product in lookup:
            raise ValueError(f"Duplicate product reference: {product}")

        minimum = number(
            row["shelf_life_min_hours"],
            f"{product} minimum shelf life",
        )

        maximum = number(
            row["shelf_life_max_hours"],
            f"{product} maximum shelf life",
        )

        if minimum <= 0 or maximum < minimum:
            raise ValueError(f"Invalid shelf-life range: {product}")

        lookup[product] = {
            "minimum": minimum,
            "maximum": maximum,
            "source": row["data_source"],
        }

    return lookup


def evaluate_quality_adjusted_scenario(
    *,
    planned_price,
    alternative_price,
    quantity_kg,
    planned_hours,
    alternative_hours,
    initial_shelf_life,
    remaining_fraction,
    aging_factor,
    additional_distance_km,
    cost_rate,
):
    """Compare two arrival values after applying the prototype quality proxy."""

    if not 0 < remaining_fraction <= 1:
        raise ValueError("remaining_fraction must be in (0, 1].")

    remaining_at_evaluation = (
        initial_shelf_life * remaining_fraction
    )

    planned = calculate_market_value(
        price_per_kg=planned_price,
        quantity_kg=quantity_kg,
        remaining_shelf_life_hours=remaining_at_evaluation,
        initial_shelf_life_hours=initial_shelf_life,
        travel_hours=planned_hours,
        expected_aging_factor=aging_factor,
        transport_cost=0.0,
    )

    alternative = calculate_market_value(
        price_per_kg=alternative_price,
        quantity_kg=quantity_kg,
        remaining_shelf_life_hours=remaining_at_evaluation,
        initial_shelf_life_hours=initial_shelf_life,
        travel_hours=alternative_hours,
        expected_aging_factor=aging_factor,
        transport_cost=0.0,
    )

    incremental_distance_cost = additional_distance_km * cost_rate

    quality_adjusted_difference = (
        alternative.expected_net_value
        - planned.expected_net_value
    )

    residual = (
        quality_adjusted_difference
        - incremental_distance_cost
    )

    if residual > 0:
        status = "POSITIVE_AFTER_QUALITY_PROXY_AND_DISTANCE_COST"
    else:
        status = "NOT_POSITIVE_AFTER_QUALITY_PROXY_AND_DISTANCE_COST"

    return {
        "remaining_at_evaluation_hours": remaining_at_evaluation,
        "planned_remaining_at_arrival_hours": (
            planned.remaining_at_arrival_hours
        ),
        "alternative_remaining_at_arrival_hours": (
            alternative.remaining_at_arrival_hours
        ),
        "planned_quality_proxy": planned.quality_at_arrival,
        "alternative_quality_proxy": alternative.quality_at_arrival,
        "planned_value_after_transport_inr": (
            planned.expected_net_value
        ),
        "alternative_value_after_transport_inr": (
            alternative.expected_net_value
        ),
        "quality_adjusted_value_difference_inr": (
            quality_adjusted_difference
        ),
        "hypothetical_incremental_distance_cost_inr": (
            incremental_distance_cost
        ),
        "residual_value_difference_inr": residual,
        "screening_status": status,
    }


def build_sensitivity_matrix():
    routes = read_csv(ROUTES)
    prices = load_price_lookup()
    shelf_lives = load_shelf_life_reference()

    output = []

    for route in routes:
        if route["route_comparison_status"] != "COMPARISON_COMPLETE":
            raise ValueError("Incomplete OSRM route comparison.")

        product = route["product_name"]
        product_key = product.casefold()

        if product_key not in shelf_lives:
            raise ValueError(f"No shelf-life reference for {product}")

        reference = shelf_lives[product_key]

        product_scenarios = {
            "CONSERVATIVE_MINIMUM": reference["minimum"],
            "REFERENCE_MAXIMUM": reference["maximum"],
        }

        as_of_date = route["planned_route_retrieved_at_utc"][:10]

        # Use the market-price screen date from its source dataset.
        price_dates = {
            key[2] for key in prices
            if key[0] == product_key
        }

        if len(price_dates) != 1:
            raise ValueError(
                f"Expected one price date for {product}: {price_dates}"
            )

        as_of_date = next(iter(price_dates))

        planned_key = (
            product_key,
            route["planned_destination"].casefold(),
            as_of_date,
        )

        alternative_key = (
            product_key,
            route["candidate_market"].casefold(),
            as_of_date,
        )

        if planned_key not in prices or alternative_key not in prices:
            raise ValueError(
                f"Missing price for {route['container_id']} "
                f"at {route['candidate_market']}"
            )

        planned_price = prices[planned_key]
        alternative_price = prices[alternative_key]

        quantity = number(
            route["gross_sales_value_difference_inr"],
            "gross price uplift",
        )

        # Quantity is reconstructed from the gross sales difference.
        # Using the screen quantity is preferable and is loaded below.
        opportunity_rows = read_csv(
            ROOT / "data/processed/arbitrage/"
            "market_opportunity_screen.csv"
        )

        matching = [
            row for row in opportunity_rows
            if row["container_id"] == route["container_id"]
            and row["candidate_market"].casefold()
            == route["candidate_market"].casefold()
        ]

        if len(matching) != 1:
            raise ValueError("Could not uniquely match opportunity quantity.")

        quantity = number(matching[0]["quantity_kg"], "quantity_kg")

        planned_hours = number(
            route["planned_osrm_duration_hours"],
            "planned duration",
        )

        alternative_hours = number(
            route["candidate_osrm_duration_hours"],
            "alternative duration",
        )

        additional_distance = number(
            route["additional_distance_km"],
            "additional distance",
        )

        for shelf_life_label, initial_life in product_scenarios.items():
            for remaining_fraction in REMAINING_LIFE_FRACTIONS:
                for aging_factor in AGING_FACTORS:
                    for cost_rate in COST_RATES:

                        result = evaluate_quality_adjusted_scenario(
                            planned_price=planned_price,
                            alternative_price=alternative_price,
                            quantity_kg=quantity,
                            planned_hours=planned_hours,
                            alternative_hours=alternative_hours,
                            initial_shelf_life=initial_life,
                            remaining_fraction=remaining_fraction,
                            aging_factor=aging_factor,
                            additional_distance_km=additional_distance,
                            cost_rate=cost_rate,
                        )

                        output.append({
                            "container_id": route["container_id"],
                            "product_name": product,
                            "planned_destination": route["planned_destination"],
                            "candidate_market": route["candidate_market"],
                            "quantity_kg": f"{quantity:.2f}",
                            "screen_date": as_of_date,
                            "shelf_life_reference_source": reference["source"],
                            "shelf_life_scenario": shelf_life_label,
                            "initial_shelf_life_hours": f"{initial_life:.2f}",
                            "remaining_life_fraction": f"{remaining_fraction:.2f}",
                            "aging_factor": f"{aging_factor:.2f}",
                            "cost_rate_inr_per_extra_km": f"{cost_rate:.2f}",
                            "planned_price_inr_per_kg": f"{planned_price:.2f}",
                            "alternative_price_inr_per_kg": f"{alternative_price:.2f}",
                            "planned_osrm_duration_hours": f"{planned_hours:.3f}",
                            "alternative_osrm_duration_hours": f"{alternative_hours:.3f}",
                            "additional_distance_km": f"{additional_distance:.3f}",
                            **{
                                key: (
                                    f"{value:.6f}"
                                    if isinstance(value, float)
                                    else value
                                )
                                for key, value in result.items()
                            },
                            "assumption_note": (
                                "Illustrative shelf-life fraction and aging factor; "
                                "not measured container condition. Quality proxy "
                                "is not validated saleable-product percentage."
                            ),
                        })

    return output


def main():
    results = build_sensitivity_matrix()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys()),
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n========== SHELF-LIFE-ADJUSTED SENSITIVITY ==========")
    print("Scenario comparisons:", len(results))
    print("Road candidates:", len({
        (row["container_id"], row["candidate_market"])
        for row in results
    }))
    print("Shelf-life reference scenarios: 2 per product")
    print("Remaining-life fractions:", REMAINING_LIFE_FRACTIONS)
    print("Aging factors:", AGING_FACTORS)
    print("Hypothetical cost rates:", COST_RATES)

    print("\n========== RESULTS AT INR 10/KM ==========")

    for aging in AGING_FACTORS:
        selected = [
            row for row in results
            if float(row["cost_rate_inr_per_extra_km"]) == 10.0
            and float(row["aging_factor"]) == aging
            and row["shelf_life_scenario"] == "CONSERVATIVE_MINIMUM"
            and float(row["remaining_life_fraction"]) == 1.0
        ]

        positive = sum(
            row["screening_status"]
            == "POSITIVE_AFTER_QUALITY_PROXY_AND_DISTANCE_COST"
            for row in selected
        )

        print(
            f"Aging factor {aging:.1f}, full reference life remaining: "
            f"{positive}/{len(selected)} positive comparisons"
        )

    print("\n========== OUTPUT ==========")
    print(OUTPUT)
    print(
        "This remains a scenario sensitivity model, not a live "
        "spoilage or rerouting decision engine."
    )


if __name__ == "__main__":
    main()
