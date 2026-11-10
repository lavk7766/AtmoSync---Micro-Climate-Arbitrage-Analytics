import math

from simulator.config import (
    SIMULATION_INTERVAL_SECONDS,
    TRANSPORT_SPEED_KMH,
)
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)


class LocationSimulator:

    def __init__(self):
        self.distance_travelled = {
            container_id: 0.0
            for container_id in CONTAINER_ROUTES
        }

        self.route_distances = {
            container_id: self._calculate_route_distance(route)
            for container_id, route in CONTAINER_ROUTES.items()
        }

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

    def get_current_location(self, container_id):

        route = CONTAINER_ROUTES[container_id]

        if len(route) < 2:
            raise ValueError(
                f"Route for {container_id} needs at least two waypoints"
            )

        transport_mode = CONTAINER_TRANSPORT_MODES[container_id]
        speed = TRANSPORT_SPEED_KMH[transport_mode]

        distance_step = (
            speed * SIMULATION_INTERVAL_SECONDS / 3600
        )

        remaining_distance = self.distance_travelled[container_id]
        current_distance = remaining_distance

        for i in range(len(route) - 1):

            start = route[i]
            end = route[i + 1]

            segment_distance = self.calculate_distance(start, end)

            if remaining_distance <= segment_distance:

                if segment_distance == 0:
                    return round(end[0], 5), round(end[1], 5)

                progress = remaining_distance / segment_distance

                latitude = start[0] + (
                    end[0] - start[0]
                ) * progress

                longitude = start[1] + (
                    end[1] - start[1]
                ) * progress

                self.distance_travelled[container_id] = min(
                    current_distance + distance_step,
                    self.route_distances[container_id]
                )

                return round(latitude, 5), round(longitude, 5)

            remaining_distance -= segment_distance

        self.distance_travelled[container_id] = (
            self.route_distances[container_id]
        )

        return round(route[-1][0], 5), round(route[-1][1], 5)