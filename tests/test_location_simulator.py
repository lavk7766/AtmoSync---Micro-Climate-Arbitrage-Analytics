import pytest

from simulator.config import (
    SIMULATION_INTERVAL_SECONDS,
    TRANSPORT_SPEED_KMH,
)
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)
from simulator.location_simulator import LocationSimulator


@pytest.mark.parametrize(
    "container_id",
    list(CONTAINER_ROUTES.keys())
)
def test_container_moves_at_configured_speed(container_id):

    simulator = LocationSimulator()

    first_location = simulator.get_current_location(container_id)
    second_location = simulator.get_current_location(container_id)

    actual_distance = simulator.calculate_distance(
        first_location,
        second_location
    )

    mode = CONTAINER_TRANSPORT_MODES[container_id]
    speed = TRANSPORT_SPEED_KMH[mode]

    expected_distance = (
        speed * SIMULATION_INTERVAL_SECONDS / 3600
    )

    assert actual_distance == pytest.approx(
        expected_distance,
        abs=0.002
    )


def test_haversine_distance_is_zero_for_same_point():

    point = (28.61394, 77.20902)

    distance = LocationSimulator.calculate_distance(
        point,
        point
    )

    assert distance == 0.0


def test_container_stays_within_route_bounds():

    simulator = LocationSimulator()

    for container_id, route in CONTAINER_ROUTES.items():

        latitude, longitude = simulator.get_current_location(
            container_id
        )

        assert min(point[0] for point in route) <= latitude <= max(
            point[0] for point in route
        )

        assert min(point[1] for point in route) <= longitude <= max(
            point[1] for point in route
        )