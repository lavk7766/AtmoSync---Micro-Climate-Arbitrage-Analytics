
import pytest

from simulator.config import TRANSPORT_SPEED_KMH
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)
from simulator.location_simulator import LocationSimulator


class FakeClock:
    def __init__(self):
        self.elapsed = 0.0

    def elapsed_seconds(self):
        return self.elapsed

    def advance(self, seconds):
        self.elapsed += seconds


@pytest.mark.parametrize(
    "container_id",
    list(CONTAINER_ROUTES.keys())
)

def test_container_moves_at_configured_speed(container_id):
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    # Initialize the container's route position.
    simulator.get_current_location(container_id)

    initial_distance = simulator.distance_travelled[container_id]

    # Advance simulated time by exactly one hour.
    clock.advance(3600)

    # Update the container's location.
    simulator.get_current_location(container_id)

    final_distance = simulator.distance_travelled[container_id]

    actual_distance = final_distance - initial_distance

    mode = CONTAINER_TRANSPORT_MODES[container_id]
    expected_speed = TRANSPORT_SPEED_KMH[mode]

    assert actual_distance == pytest.approx(
        expected_speed,
        abs=0.001
    )


def test_repeated_location_call_does_not_advance_route():
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    first_location = simulator.get_current_location("CONT001")
    second_location = simulator.get_current_location("CONT001")

    assert first_location == second_location


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


def test_container_stops_at_route_destination():
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    container_id = "CONT001"

    simulator.get_current_location(container_id)

    # Advance far beyond the journey duration.
    clock.advance(100000000)

    location = simulator.get_current_location(container_id)
    destination = CONTAINER_ROUTES[container_id][-1]

    assert location == (
        round(destination[0], 5),
        round(destination[1], 5),
    )
