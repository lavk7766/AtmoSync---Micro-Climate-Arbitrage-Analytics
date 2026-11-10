
import json
from pathlib import Path

# AtmoSync - Simulated Container Routes
#
# Coordinates use WGS84 decimal degrees:
# (latitude, longitude).

# Load the verified OpenStreetMap road route for CONT001.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONT001_ROUTE_FILE = (
    PROJECT_ROOT / "data" / "routes" / "CONT001_road.json"
)

with open(CONT001_ROUTE_FILE, "r", encoding="utf-8") as file:
    route_data = json.load(file)

CONTAINER_ROUTES = {
    "CONT001": [
        tuple(point)
        for point in route_data["route_coordinates"]
    ],

    "CONT002": [
        (19.07609, 72.87743),  # Mumbai
        (18.52043, 73.85674),  # Pune
        (17.65992, 75.90639),  # Solapur
    ],

    "CONT003": [
        (12.97160, 77.59456),  # Bengaluru
        (13.08268, 80.27072),  # Chennai
        (15.82813, 78.03728),  # Kurnool
    ],

    "CONT004": [
        (22.57265, 88.36389),  # Kolkata
        (23.34410, 85.30956),  # Ranchi
        (25.59409, 85.13756),  # Patna
    ],

    "CONT005": [
        (18.9388, 72.8354),  # Mumbai port area
        (17.5000, 71.8000),  # Illustrative offshore waypoint
        (16.0000, 72.1000),  # Illustrative offshore waypoint
        (15.4050, 73.8000),  # Goa port area
        (14.0000, 73.5000),  # Illustrative offshore waypoint
        (12.9172, 74.8560),  # Mangaluru port area
    ],
}

CONTAINER_TRANSPORT_MODES = {
    "CONT001": "road",
    "CONT002": "rail",
    "CONT003": "road",
    "CONT004": "rail",
    "CONT005": "sea",
}
