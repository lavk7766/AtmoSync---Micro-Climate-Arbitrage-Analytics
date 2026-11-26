import csv
import math
from pathlib import Path

from simulator.routes import CONTAINER_ROUTES, CONTAINER_TRANSPORT_MODES


ROOT = Path(__file__).resolve().parents[1]

PRICE_FILE = (
    ROOT / "data/processed/synthetic_market_prices/"
    "synthetic_local_market_prices.csv"
)

OUTPUT = (
    ROOT / "data/processed/market_reference/"
    "market_location_reference.csv"
)

# City references are taken from existing route endpoints.
# Coordinates are proxies, not verified wholesale-market locations.
MARKET_ENDPOINTS = {
    "Delhi": ("CONT001", 0),
    "Lucknow": ("CONT001", -1),
    "Mumbai": ("CONT002", 0),
    "Solapur": ("CONT002", -1),
    "Bengaluru": ("CONT003", 0),
    "Kurnool": ("CONT003", -1),
    "Kolkata": ("CONT004", 0),
    "Patna": ("CONT004", -1),
    "Mangaluru": ("CONT005", -1),
}

FIELDS = [
    "market_name",
    "latitude",
    "longitude",
    "coordinate_system",
    "coordinate_order",
    "coordinate_role",
    "coordinate_source_type",
    "source_route_container",
    "source_transport_mode",
    "location_precision",
    "source_note",
]


def build_market_location_records():
    records = []

    for market, (container_id, endpoint_index) in MARKET_ENDPOINTS.items():
        route = CONTAINER_ROUTES.get(container_id)

        if not route or len(route) < 2:
            raise ValueError(f"Invalid source route: {container_id}")

        latitude, longitude = route[endpoint_index]

        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            raise ValueError(f"Invalid coordinates for {market}")

        if container_id == "CONT001":
            source_type = "osm_osrm_route_endpoint"
            precision = "network_route_endpoint"
            note = (
                "Endpoint of the OSM/OSRM-derived CONT001 road route. "
                "Not a verified wholesale-market coordinate."
            )
        else:
            source_type = "project_illustrative_waypoint"
            precision = "illustrative_city_level_proxy"
            note = (
                "Project-defined illustrative route waypoint. "
                "Not a verified network or wholesale-market coordinate."
            )

        if market == "Mumbai":
            note += (
                " Uses the generic Mumbai city waypoint from CONT002. "
                "CONT005 has a separate Mumbai port-area starting point."
            )

        if market == "Mangaluru":
            note += (
                " Uses the Mangaluru port-area endpoint of CONT005."
            )

        records.append({
            "market_name": market,
            "latitude": f"{latitude:.6f}",
            "longitude": f"{longitude:.6f}",
            "coordinate_system": "WGS84",
            "coordinate_order": "latitude,longitude",
            "coordinate_role": "project_route_endpoint",
            "coordinate_source_type": source_type,
            "source_route_container": container_id,
            "source_transport_mode": CONTAINER_TRANSPORT_MODES[container_id],
            "location_precision": precision,
            "source_note": note,
        })

    return records


def main():
    if not PRICE_FILE.exists():
        raise FileNotFoundError(PRICE_FILE)

    with PRICE_FILE.open(encoding="utf-8-sig", newline="") as file:
        price_rows = list(csv.DictReader(file))

    expected_markets = {
        row["market_name"].strip()
        for row in price_rows
    }

    records = build_market_location_records()

    actual_markets = {
        row["market_name"]
        for row in records
    }

    if actual_markets != expected_markets:
        raise ValueError(
            f"Market coverage mismatch. "
            f"Missing: {expected_markets - actual_markets}; "
            f"Unexpected: {actual_markets - expected_markets}"
        )

    if len(records) != len(actual_markets):
        raise ValueError("Duplicate market location records detected.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print("\n========== MARKET LOCATION REFERENCE ==========")
    print("Markets:", len(records))
    print("Unique markets:", len(actual_markets))
    print("Coordinate system: WGS84")
    print("Verified network route endpoints: 2")
    print("Illustrative project waypoints: 7")
    print("Output:", OUTPUT)

    print("\n========== LOCATION RECORDS ==========")

    for row in records:
        print(
            f'{row["market_name"]}: '
            f'({row["latitude"]}, {row["longitude"]}) | '
            f'{row["coordinate_source_type"]}'
        )

    print("\nLocation reference generated successfully.")
    print("Coordinates must not be treated as verified wholesale-market locations.")


if __name__ == "__main__":
    main()
