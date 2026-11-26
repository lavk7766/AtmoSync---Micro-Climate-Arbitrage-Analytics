import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

METADATA = ROOT / "data/reference/container_metadata.csv"
SCENARIOS = ROOT / "data/scenarios/shipment_scenarios.csv"
PRICES = ROOT / "data/processed/synthetic_market_prices/synthetic_local_market_prices.csv"

OUTPUT = ROOT / "data/processed/arbitrage/market_opportunity_screen.csv"

FIELDS = [
    "screen_date",
    "scenario_id",
    "container_id",
    "product_name",
    "quantity_kg",
    "origin",
    "planned_destination",
    "candidate_market",
    "planned_price_inr_per_kg",
    "candidate_price_inr_per_kg",
    "price_difference_inr_per_kg",
    "gross_sales_value_difference_inr",
    "max_additional_transport_cost_before_quality_adjustment_inr",
    "price_source_type",
    "alternative_distance_km",
    "alternative_travel_hours",
    "alternative_transport_cost_inr",
    "route_source_type",
    "transport_cost_source",
    "evaluation_status",
]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"No records found in {path}")

    return rows


def main():
    shipments = read_csv(METADATA)
    scenarios = read_csv(SCENARIOS)
    prices = read_csv(PRICES)

    dates = {row["simulated_as_of_date"] for row in prices}

    if len(dates) != 1:
        raise ValueError("Expected exactly one synthetic price date.")

    screen_date = next(iter(dates))

    price_lookup = {}

    for row in prices:
        if (
            row["currency"] != "INR"
            or row["quantity_unit"] != "kg"
            or row["price_source_type"] != "synthetic_simulated"
        ):
            raise ValueError("Unexpected currency, unit or price source.")

        key = (
            row["product_name"].strip().casefold(),
            row["market_name"].strip().casefold(),
            row["simulated_as_of_date"],
        )

        if key in price_lookup:
            raise ValueError(f"Duplicate market price: {key}")

        price = float(row["price_per_kg"])

        if price <= 0:
            raise ValueError(f"Invalid market price: {key}")

        price_lookup[key] = (price, row["price_source_type"])

    scenario_lookup = {}

    for row in scenarios:
        container_id = row["container_id"]

        if container_id in scenario_lookup:
            raise ValueError(f"Duplicate shipment scenario: {container_id}")

        scenario_lookup[container_id] = row

    markets = sorted({row["market_name"] for row in prices})
    output = []

    for shipment in shipments:
        container_id = shipment["container_id"]

        if container_id not in scenario_lookup:
            raise ValueError(f"Missing scenario for {container_id}")

        scenario = scenario_lookup[container_id]
        product = shipment["product_name"].strip()
        origin = shipment["origin"].strip()
        destination = shipment["destination"].strip()

        if (
            scenario["origin"].casefold() != origin.casefold()
            or scenario["destination"].casefold() != destination.casefold()
            or scenario["product_name"].casefold() != product.casefold()
        ):
            raise ValueError(f"Metadata/scenario mismatch: {container_id}")

        quantity = float(shipment["quantity"])
        unit = shipment["quantity_unit"].strip().lower()

        if unit == "kg":
            quantity_kg = quantity
        elif unit == "tonne":
            quantity_kg = quantity * 1000
        else:
            raise ValueError(f"Unsupported quantity unit: {unit}")

        if quantity_kg <= 0:
            raise ValueError(f"Invalid shipment quantity: {container_id}")

        planned_key = (
            product.casefold(),
            destination.casefold(),
            screen_date,
        )

        if planned_key not in price_lookup:
            raise ValueError(f"Missing planned price: {planned_key}")

        planned_price, source_type = price_lookup[planned_key]

        for market in markets:
            if market.casefold() in {
                origin.casefold(),
                destination.casefold(),
            }:
                continue

            candidate_key = (
                product.casefold(),
                market.casefold(),
                screen_date,
            )

            if candidate_key not in price_lookup:
                raise ValueError(f"Missing candidate price: {candidate_key}")

            candidate_price, candidate_source = price_lookup[candidate_key]

            if candidate_source != source_type:
                raise ValueError("Inconsistent price-source types.")

            difference_per_kg = candidate_price - planned_price
            gross_difference = difference_per_kg * quantity_kg

            output.append({
                "screen_date": screen_date,
                "scenario_id": scenario["scenario_id"],
                "container_id": container_id,
                "product_name": product,
                "quantity_kg": f"{quantity_kg:.2f}",
                "origin": origin,
                "planned_destination": destination,
                "candidate_market": market,
                "planned_price_inr_per_kg": f"{planned_price:.2f}",
                "candidate_price_inr_per_kg": f"{candidate_price:.2f}",
                "price_difference_inr_per_kg": f"{difference_per_kg:.2f}",
                "gross_sales_value_difference_inr": f"{gross_difference:.2f}",
                "max_additional_transport_cost_before_quality_adjustment_inr": (
                    f"{gross_difference:.2f}" if gross_difference > 0 else ""
                ),
                "price_source_type": source_type,
                "alternative_distance_km": "",
                "alternative_travel_hours": "",
                "alternative_transport_cost_inr": "",
                "route_source_type": "",
                "transport_cost_source": "",
                "evaluation_status": (
                    "POSITIVE_PRICE_CANDIDATE_ROUTE_COST_QUALITY_PENDING"
                    if gross_difference > 0
                    else "NO_POSITIVE_PRICE_DIFFERENCE"
                ),
            })

    output.sort(
        key=lambda row: (
            row["container_id"],
            -float(row["gross_sales_value_difference_inr"]),
        )
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)

    positive = [
        row for row in output
        if float(row["gross_sales_value_difference_inr"]) > 0
    ]

    print("\n========== MARKET OPPORTUNITY SCREEN ==========")
    print("Shipments:", len(shipments))
    print("Comparisons:", len(output))
    print("Positive price candidates:", len(positive))
    print("No positive price difference:", len(output) - len(positive))
    print("Output:", OUTPUT)

    print("\nTop five candidates:")

    for row in sorted(
        positive,
        key=lambda item: float(
            item["gross_sales_value_difference_inr"]
        ),
        reverse=True,
    )[:5]:
        print(
            row["container_id"],
            row["product_name"],
            "->",
            row["candidate_market"],
            "INR",
            row["gross_sales_value_difference_inr"],
        )

    print("\nAll route and cost fields remain blank until verified inputs are supplied.")
    print("No operational rerouting recommendations have been generated.")


if __name__ == "__main__":
    main()
