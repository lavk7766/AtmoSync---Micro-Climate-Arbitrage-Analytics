"""Retrieve alternative road routes for positive-price AtmoSync candidates.

Uses the public OSRM demonstration server:
- Maximum request rate: one request per second.
- Driving profile, not a truck-specific freight profile.
- Coordinates are city-level project proxies.
- No traffic or freight-operational guarantee.
"""

import csv
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

MATRIX_FILE = (
    ROOT / "data/processed/arbitrage/"
    "alternative_route_input_matrix.csv"
)

SCENARIO_FILE = (
    ROOT / "data/scenarios/shipment_scenarios.csv"
)

LOCATION_FILE = (
    ROOT / "data/processed/market_reference/"
    "market_location_reference.csv"
)

OUTPUT_FILE = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_candidate_routes.csv"
)

OSRM_BASE_URL = "https://router.project-osrm.org"
REQUEST_INTERVAL_SECONDS = 1.1
REQUEST_TIMEOUT_SECONDS = 40

ATTRIBUTION = "© OpenStreetMap contributors"

FIELDS = [
    "container_id",
    "product_name",
    "origin",
    "candidate_market",
    "gross_sales_value_difference_inr",
    "routing_profile",
    "route_status",
    "http_status",
    "osrm_code",
    "network_distance_km",
    "estimated_duration_hours",
    "origin_snap_distance_m",
    "destination_snap_distance_m",
    "origin_snapped_latitude",
    "origin_snapped_longitude",
    "destination_snapped_latitude",
    "destination_snapped_longitude",
    "origin_coordinate_source_type",
    "destination_coordinate_source_type",
    "requested_origin_latitude",
    "requested_origin_longitude",
    "requested_destination_latitude",
    "requested_destination_longitude",
    "retrieved_at_utc",
    "routing_engine",
    "routing_service",
    "map_attribution",
    "route_limitation",
    "error_message",
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


def load_road_candidate_inputs(
    matrix_path=MATRIX_FILE,
    scenario_path=SCENARIO_FILE,
    location_path=LOCATION_FILE,
):
    """Load positive-price candidates belonging to road shipments."""

    matrix = read_csv(matrix_path)
    scenarios = read_csv(scenario_path)
    locations = read_csv(location_path)

    scenario_lookup = {}

    for row in scenarios:
        container_id = row["container_id"]

        if container_id in scenario_lookup:
            raise ValueError(f"Duplicate scenario: {container_id}")

        scenario_lookup[container_id] = row

    location_lookup = {}

    for row in locations:
        key = row["market_name"].strip().casefold()

        if key in location_lookup:
            raise ValueError(
                f"Duplicate market coordinate: {row['market_name']}"
            )

        latitude = float(row["latitude"])
        longitude = float(row["longitude"])

        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90 <= latitude <= 90
            or not -180 <= longitude <= 180
        ):
            raise ValueError(
                f"Invalid coordinates: {row['market_name']}"
            )

        location_lookup[key] = row

    candidates = []

    for row in matrix:
        if row["price_candidate_status"] != "POSITIVE_PRICE_CANDIDATE":
            continue

        container_id = row["container_id"]
        scenario = scenario_lookup.get(container_id)

        if scenario is None:
            raise ValueError(
                f"Missing shipment scenario: {container_id}"
            )

        # Only the existing road shipments are selected.
        if scenario["transport_mode"].strip().lower() != "road":
            continue

        origin = row["origin"].strip()
        destination = row["candidate_market"].strip()

        origin_location = location_lookup.get(origin.casefold())
        destination_location = location_lookup.get(
            destination.casefold()
        )

        if origin_location is None or destination_location is None:
            raise ValueError(
                f"Missing coordinate reference: {origin} -> {destination}"
            )

        candidates.append({
            "container_id": container_id,
            "product_name": row["product_name"],
            "origin": origin,
            "candidate_market": destination,
            "gross_sales_value_difference_inr": (
                row["gross_sales_value_difference_inr"]
            ),
            "origin_latitude": float(origin_location["latitude"]),
            "origin_longitude": float(origin_location["longitude"]),
            "destination_latitude": float(
                destination_location["latitude"]
            ),
            "destination_longitude": float(
                destination_location["longitude"]
            ),
            "origin_coordinate_source_type": (
                origin_location["coordinate_source_type"]
            ),
            "destination_coordinate_source_type": (
                destination_location["coordinate_source_type"]
            ),
        })

    candidates.sort(
        key=lambda row: (
            row["container_id"],
            row["candidate_market"].casefold(),
        )
    )

    keys = [
        (row["container_id"], row["candidate_market"].casefold())
        for row in candidates
    ]

    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate road candidate pairs found.")

    return candidates


def build_osrm_request_url(candidate):
    """OSRM requires longitude,latitude coordinate ordering."""

    coordinates = (
        f'{candidate["origin_longitude"]},'
        f'{candidate["origin_latitude"]};'
        f'{candidate["destination_longitude"]},'
        f'{candidate["destination_latitude"]}'
    )

    params = urlencode({
        "overview": "false",
        "alternatives": "false",
        "steps": "false",
    })

    return (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{coordinates}?{params}"
    )


def extract_route_metrics(data):
    """Convert a successful OSRM response into auditable metrics."""

    if not isinstance(data, dict) or data.get("code") != "Ok":
        return None

    routes = data.get("routes") or []
    waypoints = data.get("waypoints") or []

    if not routes or len(waypoints) != 2:
        return None

    route = routes[0]
    distance_m = float(route["distance"])
    duration_s = float(route["duration"])

    values = [distance_m, duration_s]

    if not all(math.isfinite(value) and value > 0 for value in values):
        raise ValueError("OSRM returned invalid distance or duration.")

    snapped = [
        waypoint["location"]
        for waypoint in waypoints
    ]

    if any(len(location) != 2 for location in snapped):
        raise ValueError("OSRM returned invalid snapped coordinates.")

    return {
        "network_distance_km": distance_m / 1000.0,
        "estimated_duration_hours": duration_s / 3600.0,
        "origin_snap_distance_m": float(
            waypoints[0]["distance"]
        ),
        "destination_snap_distance_m": float(
            waypoints[1]["distance"]
        ),
        "origin_snapped_longitude": float(snapped[0][0]),
        "origin_snapped_latitude": float(snapped[0][1]),
        "destination_snapped_longitude": float(snapped[1][0]),
        "destination_snapped_latitude": float(snapped[1][1]),
    }


def make_result(candidate):
    return {
        "container_id": candidate["container_id"],
        "product_name": candidate["product_name"],
        "origin": candidate["origin"],
        "candidate_market": candidate["candidate_market"],
        "gross_sales_value_difference_inr": (
            candidate["gross_sales_value_difference_inr"]
        ),
        "routing_profile": "driving",
        "route_status": "",
        "http_status": "",
        "osrm_code": "",
        "network_distance_km": "",
        "estimated_duration_hours": "",
        "origin_snap_distance_m": "",
        "destination_snap_distance_m": "",
        "origin_snapped_latitude": "",
        "origin_snapped_longitude": "",
        "destination_snapped_latitude": "",
        "destination_snapped_longitude": "",
        "origin_coordinate_source_type": (
            candidate["origin_coordinate_source_type"]
        ),
        "destination_coordinate_source_type": (
            candidate["destination_coordinate_source_type"]
        ),
        "requested_origin_latitude": candidate["origin_latitude"],
        "requested_origin_longitude": candidate["origin_longitude"],
        "requested_destination_latitude": candidate["destination_latitude"],
        "requested_destination_longitude": candidate["destination_longitude"],
        "retrieved_at_utc": "",
        "routing_engine": "OSRM",
        "routing_service": OSRM_BASE_URL,
        "map_attribution": ATTRIBUTION,
        "route_limitation": (
            "Public OSRM driving profile; not truck-specific, "
            "not live traffic, and endpoints are city-level proxies."
        ),
        "error_message": "",
    }


def fetch_routes(candidates):
    """Fetch routes with at least 1.1 seconds between request starts."""

    results = []
    last_request_start = None
    rate_limited = False

    for index, candidate in enumerate(candidates):
        result = make_result(candidate)

        if rate_limited:
            result["route_status"] = "NOT_REQUESTED_AFTER_RATE_LIMIT"
            result["error_message"] = (
                "Previous request was rate-limited; no request attempted."
            )
            results.append(result)
            continue

        if last_request_start is not None:
            elapsed = time.monotonic() - last_request_start
            wait_seconds = REQUEST_INTERVAL_SECONDS - elapsed

            if wait_seconds > 0:
                time.sleep(wait_seconds)

        request = Request(
            build_osrm_request_url(candidate),
            headers={
                "User-Agent": "AtmoSync-MicroClimate-Analytics/0.1",
                "Referer": (
                    "https://github.com/lavk7766/"
                    "AtmoSync---Micro-Climate-Arbitrage-Analytics"
                ),
            },
        )

        last_request_start = time.monotonic()
        result["retrieved_at_utc"] = (
            datetime.now(timezone.utc).isoformat(timespec="seconds")
        )

        print(
            f'[{index + 1}/{len(candidates)}] '
            f'{candidate["container_id"]}: '
            f'{candidate["origin"]} -> '
            f'{candidate["candidate_market"]}',
            flush=True,
        )

        try:
            with urlopen(
                request,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                result["http_status"] = response.status
                data = json.loads(response.read().decode("utf-8"))

            result["osrm_code"] = data.get("code", "")

            metrics = extract_route_metrics(data)

            if metrics is None:
                result["route_status"] = "NO_ROUTE"
                result["error_message"] = (
                    f'OSRM response code: {data.get("code", "unknown")}'
                )
            else:
                result["route_status"] = "ROUTE_OK"

                for key, value in metrics.items():
                    if key in result:
                        result[key] = f"{value:.6f}"

        except HTTPError as error:
            result["http_status"] = error.code
            result["route_status"] = "HTTP_ERROR"
            result["error_message"] = str(error)[:300]

            if error.code == 429:
                rate_limited = True
                result["route_status"] = "RATE_LIMITED"
                print(
                    "Rate limit response received. "
                    "Remaining requests will be skipped.",
                    flush=True,
                )

        except (URLError, TimeoutError, OSError, ValueError) as error:
            result["route_status"] = "REQUEST_OR_RESPONSE_ERROR"
            result["error_message"] = str(error)[:300]

        results.append(result)

    return results


def write_results(results):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)


def main():
    candidates = load_road_candidate_inputs()

    if not candidates:
        raise ValueError("No positive-price road candidates found.")

    print("\n========== OSRM ROAD CANDIDATE BATCH ==========")
    print("Positive road candidates:", len(candidates))
    print("Routing profile: driving")
    print("Minimum interval between request starts:", REQUEST_INTERVAL_SECONDS)
    print("Maximum intended request rate: less than one per second")
    print("Alternative route geometry: not downloaded")

    results = fetch_routes(candidates)
    write_results(results)

    successful = [
        row for row in results
        if row["route_status"] == "ROUTE_OK"
    ]

    failed = [
        row for row in results
        if row["route_status"] not in ("ROUTE_OK",)
    ]

    print("\n========== BATCH SUMMARY ==========")
    print("Candidates:", len(candidates))
    print("Successful routes:", len(successful))
    print("Unresolved/failed:", len(failed))

    if successful:
        distances = [
            float(row["network_distance_km"])
            for row in successful
        ]
        durations = [
            float(row["estimated_duration_hours"])
            for row in successful
        ]

        print(
            "Successful network distance range:",
            f"{min(distances):.2f} to {max(distances):.2f} km",
        )
        print(
            "Successful duration range:",
            f"{min(durations):.2f} to {max(durations):.2f} hours",
        )

    for row in results:
        print(
            row["container_id"],
            row["origin"],
            "->",
            row["candidate_market"],
            "|",
            row["route_status"],
            "|",
            row["network_distance_km"],
            "km |",
            row["estimated_duration_hours"],
            "hours",
        )

    print("\nOutput:", OUTPUT_FILE)
    print("Attribution:", ATTRIBUTION)
    print(
        "All routes use city-level proxies and the driving profile; "
        "none is a confirmed freight route."
    )


if __name__ == "__main__":
    main()
