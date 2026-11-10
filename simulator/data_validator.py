import math
from datetime import datetime


def validate_event(event):
    required_fields = [
        "event_id",
        "container_id",
        "timestamp",
        "temperature_c",
        "humidity_pct",
        "vibration_g",
        "latitude",
        "longitude",
        "source_type",
    ]

    # Check required fields
    for field in required_fields:
        if field not in event or event[field] is None:
            return False, f"Missing or empty field: {field}"

    # Check identifiers
    if not isinstance(event["event_id"], str) or not event["event_id"].strip():
        return False, "Invalid event_id"

    if not isinstance(event["container_id"], str) or not event["container_id"].strip():
        return False, "Invalid container_id"

    # Check timestamp
    try:
        timestamp = datetime.fromisoformat(
            event["timestamp"].replace("Z", "+00:00")
        )
        if timestamp.utcoffset() is None:
            return False, "Timestamp must include timezone information"
    except (ValueError, AttributeError):
        return False, "Invalid timestamp format"

    # Validate numeric fields
    numeric_fields = [
        "temperature_c",
        "humidity_pct",
        "vibration_g",
        "latitude",
        "longitude",
    ]

    for field in numeric_fields:
        value = event[field]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f"{field} must be numeric"

        if not math.isfinite(value):
            return False, f"{field} must be a finite number"

    # Humidity validation
    if not 0 <= event["humidity_pct"] <= 100:
        return False, "Humidity must be between 0 and 100"

    # Latitude validation
    if not -90 <= event["latitude"] <= 90:
        return False, "Latitude must be between -90 and 90"

    # Longitude validation
    if not -180 <= event["longitude"] <= 180:
        return False, "Longitude must be between -180 and 180"

    # Source type validation
    if not isinstance(event["source_type"], str) or not event["source_type"].strip():
        return False, "Invalid source_type"

    return True, "Event is valid"