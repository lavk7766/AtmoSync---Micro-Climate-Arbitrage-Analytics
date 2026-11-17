
import json
import math
from pathlib import Path

import pytest

from simulator.config import TRANSPORT_SPEED_KMH
from simulator.container_generator import create_containers
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)


def test_routes_cover_all_configured_containers():
    assert set(CONTAINER_ROUTES) == set(create_containers())


def test_every_container_has_a_transport_mode():
    assert set(CONTAINER_ROUTES) == set(CONTAINER_TRANSPORT_MODES)


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_route_has_at_least_two_points(container_id):
    route = CONTAINER_ROUTES[container_id]

    assert len(route) >= 2


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_route_coordinates_are_valid(container_id):
    route = CONTAINER_ROUTES[container_id]

    for latitude, longitude in route:
        assert isinstance(latitude, (int, float))
        assert isinstance(longitude, (int, float))

        assert not isinstance(latitude, bool)
        assert not isinstance(longitude, bool)

        assert math.isfinite(latitude)
        assert math.isfinite(longitude)

        assert -90 <= latitude <= 90
        assert -180 <= longitude <= 180


@pytest.mark.parametrize(
    "container_id",
    sorted(CONTAINER_ROUTES),
)
def test_transport_mode_is_supported(container_id):
    mode = CONTAINER_TRANSPORT_MODES[container_id]

    assert mode in TRANSPORT_SPEED_KMH
    assert TRANSPORT_SPEED_KMH[mode] > 0


def test_cont001_route_matches_osm_route_file():
    project_root = Path(__file__).resolve().parent.parent

    route_file = (
        project_root / "data" / "routes" / "CONT001_road.json"
    )

    assert route_file.is_file()

    with route_file.open("r", encoding="utf-8") as file:
        route_data = json.load(file)

    assert route_data["container_id"] == "CONT001"
    assert route_data["transport_mode"] == "road"

    expected_route = [
        tuple(point)
        for point in route_data["route_coordinates"]
    ]

    assert CONTAINER_ROUTES["CONT001"] == expected_route
