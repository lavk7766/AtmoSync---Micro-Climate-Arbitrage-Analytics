from dataclasses import dataclass
from datetime import datetime


@dataclass
class SensorEvent:
    event_id: str
    container_id: str
    timestamp: datetime
    temperature_c: float
    humidity_pct: float
    vibration_g: float
    latitude: float
    longitude: float
    source_type: str