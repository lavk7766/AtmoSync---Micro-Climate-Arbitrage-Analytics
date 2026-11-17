"""
Unit test for the telemetry validation rules in kafka_to_snowflake.py.
No Kafka, Docker or Snowflake needed.

Usage (from the repo root):
    python ingestion/test_validate_events.py
"""

import sys

import kafka_to_snowflake as loader

MISSING = object()


def good_event():
    return {
        "event_id": "00000000-0000-0000-0000-000000000001",
        "container_id": "CONT001",
        "timestamp": "2026-11-12T10:30:00Z",
        "temperature_c": 8.5,
        "humidity_pct": 72.5,
        "vibration_g": 0.35,
        "latitude": 19.70,
        "longitude": -101.19,
        "source_type": "synthetic_simulated",
    }


def with_change(**changes):
    event = good_event()
    for key, value in changes.items():
        if value is MISSING:
            event.pop(key, None)
        else:
            event[key] = value
    return event


# (name, event, expected error text or None if the event must be accepted)
GPS_REQUIRED_CASES = [
    ("valid event with GPS", good_event(), None),
    ("latitude 95 (too high)", with_change(latitude=95.0), "latitude outside"),
    ("latitude -90.5 (too low)", with_change(latitude=-90.5), "latitude outside"),
    ("longitude 181 (too high)", with_change(longitude=181.0), "longitude outside"),
    ("longitude -180.5 (too low)", with_change(longitude=-180.5), "longitude outside"),
    ("latitude missing", with_change(latitude=MISSING), "missing field: latitude"),
    ("longitude missing", with_change(longitude=MISSING), "missing field: longitude"),
    ("latitude as text", with_change(latitude="north"), "not numeric: latitude"),
    ("longitude as text", with_change(longitude="east"), "not numeric: longitude"),
    ("latitude null", with_change(latitude=None), "missing field: latitude"),
    ("latitude NaN", with_change(latitude=float("nan")), "NaN"),
    ("boundary values 90 and -180 accepted", with_change(latitude=90, longitude=-180), None),
    ("humidity 150 still rejected", with_change(humidity_pct=150), "humidity_pct outside"),
    ("container_id missing still rejected", with_change(container_id=MISSING), "container_id"),
]

GPS_OPTIONAL_CASES = [
    ("GPS optional: both missing accepted", with_change(latitude=MISSING, longitude=MISSING), None),
    ("GPS optional: bad latitude still rejected", with_change(latitude=95.0), "latitude outside"),
]


def run(cases):
    failures = 0
    for name, event, expected in cases:
        error = loader.validate(event)
        ok = (error is None) if expected is None else (error is not None and expected in error)
        result = "accepted" if error is None else f"rejected: {error}"
        print(f"{'PASS' if ok else 'FAIL'}  {name}  ->  {result}")
        failures += 0 if ok else 1
    return failures


def main():
    loader.GPS_REQUIRED = True
    print("GPS required:")
    failures = run(GPS_REQUIRED_CASES)
    loader.GPS_REQUIRED = False
    print("\nGPS optional:")
    failures += run(GPS_OPTIONAL_CASES)

    total = len(GPS_REQUIRED_CASES) + len(GPS_OPTIONAL_CASES)
    print(f"\n{total - failures} of {total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())