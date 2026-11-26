"""Fetch planned road baselines using the same OSRM profile as alternatives."""

import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from scripts.fetch_osrm_road_candidate_routes import (
    build_osrm_request_url,
    extract_route_metrics,
)

ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = ROOT / "data/scenarios/shipment_scenarios.csv"
LOCATIONS = ROOT / "data/processed/market_reference/market_location_reference.csv"

OUTPUT = (
    ROOT / "data/processed/arbitrage/"
    "osrm_road_planned_baselines.csv"
)

FIELDS = [
    "container_id",
    "product_name",
    "origin",
    "planned_destination",
    "original_route_quality",
    "original_distance_km",
    "original_duration_hours",
    "original_distance_method",
    "routing_profile",
    "route_status",
    "http_status",
    "osrm_code",
    "network_distance_km",
    "estimated_duration_hours",
    "origin_snap_distance_m",
    "destination_snap_distance_m",
    "origin_coordinate_source_type",
    "destination_coordinate_source_type",
    "retrieved_at_utc",
    "routing_engine",
    "routing_service",
    "map_attribution",
    "route_limitation",
    "error_message",
]

INTERVAL_SECONDS = 1.1


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def load_planned_baseline_inputs():
    scenarios = read_csv(SCENARIOS)
    locations = read_csv(LOCATIONS)

    location_lookup = {
        row["market_name"].strip().casefold(): row
        for row in locations
    }

    results = []

    for scenario in scenarios:
        if scenario["transport_mode"].strip().lower() != "road":
            continue

        origin = scenario["origin"].strip()
        destination = scenario["destination"].strip()

        origin_location = location_lookup.get(origin.casefold())
        destination_location = location_lookup.get(destination.casefold())

        if not origin_location or not destination_location:
            raise ValueError(
                f"Missing coordinates for {origin} -> {destination}"
            )

        results.append({
            "container_id": scenario["container_id"],
            "product_name": scenario["product_name"],
            "origin": origin,
            "planned_destination": destination,
            "original_route_quality": scenario["route_quality"],
            "original_distance_km": scenario["distance_km"],
            "original_duration_hours": scenario["simulated_duration_hours"],
            "original_distance_method": scenario["distance_method"],
            "origin_latitude": float(origin_location["latitude"]),
            "origin_longitude": float(origin_location["longitude"]),
            "destination_latitude": float(destination_location["latitude"]),
            "destination_longitude": float(destination_location["longitude"]),
            "origin_coordinate_source_type": (
                origin_location["coordinate_source_type"]
            ),
            "destination_coordinate_source_type": (
                destination_location["coordinate_source_type"]
            ),
        })

    results.sort(key=lambda row: row["container_id"])

    if not results:
        raise ValueError("No planned road baselines found.")

    return results


def fetch_baselines(inputs):
    results = []
    last_request_start = None

    for index, item in enumerate(inputs):
        if last_request_start is not None:
            elapsed = time.monotonic() - last_request_start
            wait = INTERVAL_SECONDS - elapsed

            if wait > 0:
                time.sleep(wait)

        candidate = {
            "origin_longitude": item["origin_longitude"],
            "origin_latitude": item["origin_latitude"],
            "destination_longitude": item["destination_longitude"],
            "destination_latitude": item["destination_latitude"],
        }

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

        output = {field: "" for field in FIELDS}

        for field in (
            "container_id",
            "product_name",
            "origin",
            "planned_destination",
            "original_route_quality",
            "original_distance_km",
            "original_duration_hours",
            "original_distance_method",
            "origin_coordinate_source_type",
            "destination_coordinate_source_type",
        ):
            output[field] = item[field]

        output.update({
            "routing_profile": "driving",
            "routing_engine": "OSRM",
            "routing_service": "https://router.project-osrm.org",
            "map_attribution": "© OpenStreetMap contributors",
            "route_limitation": (
                "Public OSRM driving profile; not truck-specific, "
                "not live traffic; city-level coordinate proxies."
            ),
            "retrieved_at_utc": datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds"),
        })

        print(
            f'[{index + 1}/{len(inputs)}] '
            f'{item["container_id"]}: '
            f'{item["origin"]} -> {item["planned_destination"]}',
            flush=True,
        )

        last_request_start = time.monotonic()

        try:
            with urlopen(request, timeout=40) as response:
                output["http_status"] = response.status
                import json
                data = json.loads(response.read().decode("utf-8"))

            output["osrm_code"] = data.get("code", "")
            metrics = extract_route_metrics(data)

            if metrics is None:
                output["route_status"] = "NO_ROUTE"
                output["error_message"] = str(data.get("code", "unknown"))
            else:
                output["route_status"] = "ROUTE_OK"

                for field in (
                    "network_distance_km",
                    "estimated_duration_hours",
                    "origin_snap_distance_m",
                    "destination_snap_distance_m",
                ):
                    output[field] = f"{metrics[field]:.6f}"

        except HTTPError as error:
            output["http_status"] = error.code
            output["route_status"] = (
                "RATE_LIMITED" if error.code == 429 else "HTTP_ERROR"
            )
            output["error_message"] = str(error)[:300]

        except (URLError, TimeoutError, OSError, ValueError) as error:
            output["route_status"] = "REQUEST_OR_RESPONSE_ERROR"
            output["error_message"] = str(error)[:300]

        results.append(output)

    return results


def main():
    inputs = load_planned_baseline_inputs()

    print("\n========== PLANNED ROAD BASELINE ROUTING ==========")
    print("Planned road baselines:", len(inputs))
    print("Profile: OSRM driving")
    print("Request interval:", INTERVAL_SECONDS, "seconds")

    results = fetch_baselines(inputs)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)

    successful = [
        row for row in results if row["route_status"] == "ROUTE_OK"
    ]

    print("\n========== BASELINE SUMMARY ==========")
    print("Total baselines:", len(results))
    print("Successful:", len(successful))
    print("Unresolved:", len(results) - len(successful))

    for row in results:
        print(
            row["container_id"],
            row["origin"],
            "->",
            row["planned_destination"],
            "| original:",
            row["original_distance_km"],
            "km | OSRM:",
            row["network_distance_km"],
            "km |",
            row["route_status"],
        )

    print("\nOutput:", OUTPUT)


if __name__ == "__main__":
    main()
