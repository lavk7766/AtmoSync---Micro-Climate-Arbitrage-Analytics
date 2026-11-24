import csv
import json
import math
from pathlib import Path

import pytest

from simulator.config import TRANSPORT_SPEED_KMH
from simulator.container_metadata import load_container_metadata
from simulator.location_simulator import LocationSimulator
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCENARIO_FILE = (
    PROJECT_ROOT / "data" / "scenarios" / "shipment_scenarios.csv"
)

ROUTE_DIRECTORY = PROJECT_ROOT / "data" / "routes"

REQUIRED_COLUMNS = {
    "scenario_id",
    "scenario_type",
    "container_id",
    "product_name",
    "quantity",
    "quantity_unit",
    "origin",
    "destination",
    "transport_mode",
    "route_quality",
    "route_source",
    "routing_engine",
    "distance_km",
    "distance_method",
    "configured_speed_kmh",
    "simulated_duration_hours",
    "duration_method",
    "source_reported_distance_km",
    "source_estimated_duration_hours",
    "source_retrieved_at",
    "source_attribution",
}


@pytest.fixture(scope="module")
def shipment_rows():
    assert SCENARIO_FILE.is_file(), (
        f"Shipment scenario CSV not found: {SCENARIO_FILE}"
    )

    with SCENARIO_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        assert reader.fieldnames is not None
        assert REQUIRED_COLUMNS.issubset(set(reader.fieldnames))

        return list(reader)


@pytest.fixture(scope="module")
def rows_by_container(shipment_rows):
    return {
        row["container_id"]: row
        for row in shipment_rows
    }


@pytest.fixture(scope="module")
def metadata():
    return load_container_metadata()


@pytest.fixture(scope="module")
def location_simulator():
    return LocationSimulator()


def route_file_for(container_id):
    mode = CONTAINER_TRANSPORT_MODES[container_id]

    return ROUTE_DIRECTORY / f"{container_id}_{mode}.json"


def test_scenario_file_contains_all_configured_containers(
    shipment_rows,
):
    actual_ids = {
        row["container_id"]
        for row in shipment_rows
    }

    assert actual_ids == set(CONTAINER_ROUTES)


def test_exactly_five_baseline_shipments_exist(shipment_rows):
    assert len(shipment_rows) == 5


def test_scenario_ids_are_unique(shipment_rows):
    scenario_ids = [
        row["scenario_id"]
        for row in shipment_rows
    ]

    assert len(scenario_ids) == len(set(scenario_ids))


def test_each_container_has_one_baseline_shipment(shipment_rows):
    container_ids = [
        row["container_id"]
        for row in shipment_rows
    ]

    assert len(container_ids) == len(set(container_ids))


def test_all_records_are_baseline_shipment_scenarios(shipment_rows):
    for row in shipment_rows:
        assert row["scenario_type"] == "baseline_shipment"
        assert row["scenario_id"] == (
            f"SHIP-{row['container_id']}-BASELINE"
        )


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_shipment_metadata_matches_canonical_records(
    container_id,
    rows_by_container,
    metadata,
):
    row = rows_by_container[container_id]
    reference = metadata[container_id]

    assert row["product_name"] == reference.product_name
    assert float(row["quantity"]) == pytest.approx(reference.quantity)
    assert row["quantity_unit"] == reference.quantity_unit
    assert row["origin"] == reference.origin
    assert row["destination"] == reference.destination


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_transport_mode_matches_route_configuration(
    container_id,
    rows_by_container,
):
    row = rows_by_container[container_id]

    expected_mode = CONTAINER_TRANSPORT_MODES[container_id]

    assert row["transport_mode"] == expected_mode
    assert expected_mode in TRANSPORT_SPEED_KMH


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_distance_matches_route_geometry(
    container_id,
    rows_by_container,
    location_simulator,
):
    row = rows_by_container[container_id]

    expected_distance = round(
        location_simulator.route_distances[container_id],
        2,
    )

    assert float(row["distance_km"]) == pytest.approx(
        expected_distance,
        abs=0.001,
    )


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_simulated_duration_matches_distance_and_speed(
    container_id,
    rows_by_container,
    location_simulator,
):
    row = rows_by_container[container_id]

    speed = TRANSPORT_SPEED_KMH[
        CONTAINER_TRANSPORT_MODES[container_id]
    ]

    expected_duration = round(
        location_simulator.route_distances[container_id] / speed,
        2,
    )

    assert float(row["configured_speed_kmh"]) == pytest.approx(speed)

    assert float(row["simulated_duration_hours"]) == pytest.approx(
        expected_duration,
        abs=0.001,
    )

    assert row["duration_method"] == (
        "distance_km_divided_by_configured_speed"
    )


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_route_provenance_is_correctly_labelled(
    container_id,
    rows_by_container,
):
    row = rows_by_container[container_id]
    route_file = route_file_for(container_id)

    if route_file.is_file():
        assert row["route_quality"] == "network_route_geometry"
        assert row["distance_method"] == (
            "haversine_sum_over_osrm_polyline"
        )

        route_data = json.loads(
            route_file.read_text(encoding="utf-8")
        )

        assert row["route_source"] == route_data["source"]
        assert row["routing_engine"] == route_data["routing_engine"]

    else:
        assert row["route_quality"] == "illustrative_waypoints"
        assert row["route_source"] == (
            "project_illustrative_waypoints"
        )
        assert row["routing_engine"] == ""

        assert row["distance_method"] == (
            "haversine_sum_over_illustrative_waypoints"
        )


def test_cont001_preserves_osrm_source_estimates(rows_by_container):
    row = rows_by_container["CONT001"]

    route_data = json.loads(
        route_file_for("CONT001").read_text(encoding="utf-8")
    )

    assert float(row["source_reported_distance_km"]) == pytest.approx(
        route_data["route_distance_km"]
    )

    assert float(
        row["source_estimated_duration_hours"]
    ) == pytest.approx(
        route_data["estimated_duration_hours"]
    )

    assert row["source_retrieved_at"] == route_data["retrieved_at"]
    assert row["source_attribution"] == route_data["attribution"]


def test_illustrative_routes_do_not_claim_external_estimates(
    rows_by_container,
):
    for container_id in CONTAINER_ROUTES:

        if route_file_for(container_id).is_file():
            continue

        row = rows_by_container[container_id]

        assert row["source_reported_distance_km"] == ""
        assert row["source_estimated_duration_hours"] == ""
        assert row["source_retrieved_at"] == ""
        assert row["source_attribution"] == ""


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_shipment_numeric_values_are_positive_and_finite(
    container_id,
    rows_by_container,
):
    row = rows_by_container[container_id]

    numeric_fields = (
        "quantity",
        "distance_km",
        "configured_speed_kmh",
        "simulated_duration_hours",
    )

    for field in numeric_fields:
        value = float(row[field])

        assert math.isfinite(value), (
            f"{container_id}: {field} must be finite"
        )

        assert value > 0, (
            f"{container_id}: {field} must be positive"
        )
