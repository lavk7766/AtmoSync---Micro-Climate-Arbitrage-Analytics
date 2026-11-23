
import uuid

from simulator.simulation_clock import simulation_clock
from simulator.config import SOURCE_TYPE
from simulator.sensor_generator import generate_sensor_readings
from simulator.models import SensorEvent
from simulator.location_simulator import LocationSimulator


# Maintain one movement simulator across all events.
location_simulator = LocationSimulator()


def build_sensor_event(
    container_id,
    product_reference=None,
    fault_injector=None,
    humidity_fault_injector=None,
):
    # Use exactly the same timestamp for the event and fault evaluation.
    event_timestamp = simulation_clock.now()

    readings = generate_sensor_readings(
        product_reference,
        container_id=container_id,
        timestamp=event_timestamp,
        fault_injector=fault_injector,
        humidity_fault_injector=humidity_fault_injector,
    )

    latitude, longitude = location_simulator.get_current_location(
        container_id
    )

    event = SensorEvent(
        event_id=str(uuid.uuid4()),
        container_id=container_id,
        timestamp=event_timestamp,
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
