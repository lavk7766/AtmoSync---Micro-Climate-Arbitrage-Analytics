
import math

from simulator.config import TRANSPORT_SPEED_KMH
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)
from simulator.simulation_clock import simulation_clock


class LocationSimulator:
    def __init__(self, clock=None):
        self.clock = clock or simulation_clock

        self.distance_travelled = {
            container_id: 0.0
            for container_id in CONTAINER_ROUTES
        }

        self.route_distances = {
            container_id: self._calculate_route_distance(route)
            for container_id, route in CONTAINER_ROUTES.items()
        }

        # All containers share the same simulation start time.
        self._simulation_start_elapsed = None

    @staticmethod
    def calculate_distance(point1, point2):
        """Calculate distance between two GPS coordinates in km."""

        lat1, lon1 = point1
        lat2, lon2 = point2

        earth_radius = 6371.0

        lat1 = math.radians(lat1)
        lat2 = math.radians(lat2)
        lon1 = math.radians(lon1)
        lon2 = math.radians(lon2)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(delta_lon / 2) ** 2
        )

        return 2 * earth_radius * math.asin(math.sqrt(a))

    def _calculate_route_distance(self, route):
        return sum(
            self.calculate_distance(route[i], route[i + 1])
            for i in range(len(route) - 1)
        )

    def _get_location_at_distance(self, container_id, distance):
        route = CONTAINER_ROUTES[container_id]
        remaining_distance = distance

        for i in range(len(route) - 1):
            start = route[i]
            end = route[i + 1]

            segment_distance = self.calculate_distance(start, end)

            if segment_distance == 0:
                continue

            if remaining_distance <= segment_distance:
                progress = remaining_distance / segment_distance

                latitude = start[0] + (
                    end[0] - start[0]
                ) * progress

                longitude = start[1] + (
                    end[1] - start[1]
                ) * progress

                return round(latitude, 5), round(longitude, 5)

            remaining_distance -= segment_distance

        return round(route[-1][0], 5), round(route[-1][1], 5)

    def get_current_location(self, container_id):
        """Calculate GPS position using elapsed simulated time."""

        route = CONTAINER_ROUTES[container_id]

        if len(route) < 2:
            raise ValueError(
                f"Route for {container_id} needs at least two waypoints"
            )

        if self._simulation_start_elapsed is None:
            self._simulation_start_elapsed = self.clock.elapsed_seconds()

        elapsed_simulated_seconds = max(
            0.0,
            self.clock.elapsed_seconds() - self._simulation_start_elapsed,
        )

        transport_mode = CONTAINER_TRANSPORT_MODES[container_id]
        speed = TRANSPORT_SPEED_KMH[transport_mode]

        distance = speed * elapsed_simulated_seconds / 3600

        distance = min(
            distance,
            self.route_distances[container_id],
        )

        self.distance_travelled[container_id] = distance

        return self._get_location_at_distance(
            container_id,
            distance,
        )
