"""Build a preliminary alternative-route input matrix.

Distances are Haversine distances between project coordinate proxies.
They are NOT road, rail or maritime network distances.
"""

import csv
import math
from pathlib import Path

from simulator.arbitrage_validation import haversine_distance_km


ROOT = Path(__file__).resolve().parents[1]

OPPORTUNITY_FILE = (
    ROOT / "data/processed/arbitrage/market_opportunity_screen.csv"
)

LOCATION_FILE = (
    ROOT / "data/processed/market_reference/"
    "market_location_reference.csv"
)

OUTPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "alternative_route_input_matrix.csv"
)

DISTANCE_METHOD = (
    "Haversine straight-line between project market-coordinate proxies; "
    "not network routing"
)

FIELDS = [
    "screen_date",
    "scenario_id",
    "container_id",
    "product_name",
    "quantity_kg",
    "origin",
    "planned_destination",
    "candidate_market",
    "gross_sales_value_difference_inr",
    "origin_latitude",
    "origin_longitude",
    "candidate_latitude",
    "candidate_longitude",
    "origin_coordinate_source_type",
    "candidate_coordinate_source_type",
    "straight_line_distance_km",
    "distance_method",
    "price_candidate_status",
    "route_status",
    "transport_mode",
    "network_route_distance_km",
    "estimated_travel_hours",
    "transport_cost_inr",
    "transport_cost_currency",
    "route_source_type",
]


def read_csv(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        records = list(csv.DictReader(file))

    if not records:
        raise ValueError(f"No records found in {path}")

    return records


def build_alternative_route_matrix(
    opportunity_path=OPPORTUNITY_FILE,
    location_path=LOCATION_FILE,
):
    opportunities = read_csv(opportunity_path)
    locations = read_csv(location_path)

    location_lookup = {}

    for row in locations:
        market = row.get("market_name", "").strip()

        if not market:
            raise ValueError("A market location has an empty market name.")

        key = market.casefold()

        if key in location_lookup:
            raise ValueError(f"Duplicate location record: {market}")

        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            raise ValueError(f"Invalid coordinates for {market}")

        location_lookup[key] = row

    output = []
    seen_pairs = set()

    for opportunity in opportunities:
        container_id = opportunity["container_id"]
        origin = opportunity["origin"].strip()
        planned = opportunity["planned_destination"].strip()
        candidate = opportunity["candidate_market"].strip()
        product = opportunity["product_name"].strip()

        pair = (container_id, candidate.casefold())

        if pair in seen_pairs:
            raise ValueError(
                f"Duplicate candidate market for {container_id}: {candidate}"
            )

        seen_pairs.add(pair)

        if candidate.casefold() in {
            origin.casefold(),
            planned.casefold(),
        }:
            raise ValueError(
                f"Invalid candidate for {container_id}: {candidate}"
            )

        origin_location = location_lookup.get(origin.casefold())
        candidate_location = location_lookup.get(candidate.casefold())

        if origin_location is None:
            raise ValueError(f"Missing origin coordinates: {origin}")

        if candidate_location is None:
            raise ValueError(
                f"Missing candidate coordinates: {candidate}"
            )

        origin_point = (
            float(origin_location["latitude"]),
            float(origin_location["longitude"]),
        )

        candidate_point = (
            float(candidate_location["latitude"]),
            float(candidate_location["longitude"]),
        )

        straight_line_distance = haversine_distance_km(
            origin_point,
            candidate_point,
        )

        gross_difference = float(
            opportunity["gross_sales_value_difference_inr"]
        )

        if gross_difference > 0:
            candidate_status = "POSITIVE_PRICE_CANDIDATE"
            route_status = "ROUTE_AND_COST_VERIFICATION_PENDING"
        else:
            candidate_status = "NO_POSITIVE_PRICE_DIFFERENCE"
            route_status = "NOT_PRIORITIZED_NO_PRICE_PREMIUM"

        output.append({
            "screen_date": opportunity["screen_date"],
            "scenario_id": opportunity["scenario_id"],
            "container_id": container_id,
            "product_name": product,
            "quantity_kg": opportunity["quantity_kg"],
            "origin": origin,
            "planned_destination": planned,
            "candidate_market": candidate,
            "gross_sales_value_difference_inr": (
                f"{gross_difference:.2f}"
            ),
            "origin_latitude": origin_location["latitude"],
            "origin_longitude": origin_location["longitude"],
            "candidate_latitude": candidate_location["latitude"],
            "candidate_longitude": candidate_location["longitude"],
            "origin_coordinate_source_type": (
                origin_location["coordinate_source_type"]
            ),
            "candidate_coordinate_source_type": (
                candidate_location["coordinate_source_type"]
            ),
            "straight_line_distance_km": (
                f"{straight_line_distance:.3f}"
            ),
            "distance_method": DISTANCE_METHOD,
            "price_candidate_status": candidate_status,
            "route_status": route_status,
            "transport_mode": "",
            "network_route_distance_km": "",
            "estimated_travel_hours": "",
            "transport_cost_inr": "",
            "transport_cost_currency": "",
            "route_source_type": "",
        })

    return output


def main():
    records = build_alternative_route_matrix()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    positive = [
        row for row in records
        if row["price_candidate_status"] == "POSITIVE_PRICE_CANDIDATE"
    ]

    distances = [
        float(row["straight_line_distance_km"])
        for row in records
    ]

    print("\n========== ALTERNATIVE ROUTE INPUT MATRIX ==========")
    print("Total comparisons:", len(records))
    print("Positive price candidates:", len(positive))
    print("Other comparisons:", len(records) - len(positive))
    print("Unique containers:", len({
        row["container_id"] for row in records
    }))
    print("Markets with coordinate references:", len({
        row["candidate_market"] for row in records
    } | {row["origin"] for row in records}))

    print(
        "Straight-line distance range:",
        f"{min(distances):.3f} to {max(distances):.3f} km"
    )

    print("Transport modes populated:", sum(
        bool(row["transport_mode"]) for row in records
    ))
    print("Network distances populated:", sum(
        bool(row["network_route_distance_km"]) for row in records
    ))
    print("Travel times populated:", sum(
        bool(row["estimated_travel_hours"]) for row in records
    ))
    print("Transport costs populated:", sum(
        bool(row["transport_cost_inr"]) for row in records
    ))

    print("Output:", OUTPUT_FILE)
    print("\nAll straight-line distances are preliminary coordinate proxies.")
    print("No network routes, travel times or operational costs were invented.")


if __name__ == "__main__":
    main()
