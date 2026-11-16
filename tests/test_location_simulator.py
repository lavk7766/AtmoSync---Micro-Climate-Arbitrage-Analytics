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


@pytest.mark.parametrize("container_id", list(CONTAINER_ROUTES))
def test_container_moves_at_configured_speed(container_id):
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    initial_location = simulator.get_current_location(container_id)
    initial_distance = simulator.distance_travelled[container_id]

    clock.advance(3600)

    final_location = simulator.get_current_location(container_id)
    final_distance = simulator.distance_travelled[container_id]

    mode = CONTAINER_TRANSPORT_MODES[container_id]
    expected_speed = TRANSPORT_SPEED_KMH[mode]

    actual_distance = final_distance - initial_distance

    assert actual_distance == pytest.approx(expected_speed, abs=0.001)
    assert final_location != initial_location


def test_repeated_location_call_does_not_advance_route():
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    first_location = simulator.get_current_location("CONT001")
    second_location = simulator.get_current_location("CONT001")

    assert first_location == second_location


def test_haversine_distance_is_zero_for_same_point():
    point = (28.61394, 77.20902)

    distance = LocationSimulator.calculate_distance(point, point)

    assert distance == 0.0


@pytest.mark.parametrize("container_id", list(CONTAINER_ROUTES))
def test_location_follows_configured_route(container_id):
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    simulator.get_current_location(container_id)

    clock.advance(1800)

    location = simulator.get_current_location(container_id)
    route = CONTAINER_ROUTES[container_id]

    # Check whether the generated location lies on one of the route segments.
    location_is_on_route = False

    for point_a, point_b in zip(route, route[1:]):
        distance_a_b = LocationSimulator.calculate_distance(
            point_a, point_b
        )
        distance_a_location = LocationSimulator.calculate_distance(
            point_a, location
        )
        distance_location_b = LocationSimulator.calculate_distance(
            location, point_b
        )

        if abs(
            (distance_a_location + distance_location_b) - distance_a_b
        ) <= 0.01:
            location_is_on_route = True
            break

    assert location_is_on_route


@pytest.mark.parametrize("container_id", list(CONTAINER_ROUTES))
def test_container_stops_at_route_destination(container_id):
    clock = FakeClock()
    simulator = LocationSimulator(clock=clock)

    simulator.get_current_location(container_id)

    mode = CONTAINER_TRANSPORT_MODES[container_id]
    speed = TRANSPORT_SPEED_KMH[mode]
    route_distance = simulator.route_distances[container_id]

    # Advance beyond the time required to complete the route.
    journey_seconds = ((route_distance / speed) + 1) * 3600
    clock.advance(journey_seconds)

    location = simulator.get_current_location(container_id)
    destination = CONTAINER_ROUTES[container_id][-1]

    expected_location = (
        round(destination[0], 5),
        round(destination[1], 5),
    )

    assert location == expected_location
    assert simulator.distance_travelled[container_id] == pytest.approx(
        route_distance
    )