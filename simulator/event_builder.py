import uuid
from datetime import datetime, timezone

from simulator.config import SOURCE_TYPE
from simulator.sensor_generator import generate_sensor_readings
from simulator.models import SensorEvent
from simulator.location_simulator import LocationSimulator


# Maintain one movement simulator across all events.
location_simulator = LocationSimulator()


def build_sensor_event(container_id):
    readings = generate_sensor_readings()

    latitude, longitude = location_simulator.get_current_location(
        container_id
    )

    event = SensorEvent(
        event_id=str(uuid.uuid4()),
        container_id=container_id,
        timestamp=datetime.now(timezone.utc),
        temperature_c=readings["temperature_c"],
        humidity_pct=readings["humidity_pct"],
        vibration_g=readings["vibration_g"],
        latitude=latitude,
        longitude=longitude,
        source_type=SOURCE_TYPE,
    )

    return event


def event_to_dict(event):
    return {
        "event_id": event.event_id,
        "container_id": event.container_id,
        "timestamp": event.timestamp.isoformat().replace("+00:00", "Z"),
        "temperature_c": event.temperature_c,
        "humidity_pct": event.humidity_pct,
        "vibration_g": event.vibration_g,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "source_type": event.source_type,
    }