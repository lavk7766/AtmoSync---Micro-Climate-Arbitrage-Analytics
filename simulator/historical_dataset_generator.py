
import csv
import json
import random
import uuid

from datetime import datetime, timedelta, timezone
from pathlib import Path

from simulator.config import (
    TEMPERATURE_RANGE,
    HUMIDITY_RANGE,
    VIBRATION_RANGE,
    SOURCE_TYPE,
    TRANSPORT_SPEED_KMH,
)
from simulator.routes import (
    CONTAINER_ROUTES,
    CONTAINER_TRANSPORT_MODES,
)
from simulator.location_simulator import LocationSimulator
from simulator.data_validator import validate_event


# Dataset settings
RECORDS_PER_CONTAINER = 50
INTERVAL_MINUTES = 5
RANDOM_SEED = 42

BASE_TIMESTAMP = datetime(
    2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "synthetic_telemetry"
)

CSV_FILE = OUTPUT_DIR / "historical_telemetry.csv"
JSONL_FILE = OUTPUT_DIR / "historical_telemetry.jsonl"
MANIFEST_FILE = OUTPUT_DIR / "dataset_manifest.json"

FIELDS = [
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


class FakeClock:
    """Controllable clock for historical GPS simulation."""

    def __init__(self):
        self.elapsed = 0.0

    def elapsed_seconds(self):
        return self.elapsed

    def advance(self, seconds):
        self.elapsed += seconds



def generate_dataset():
    rng = random.Random(RANDOM_SEED)
    namespace = uuid.NAMESPACE_URL

    # Protect existing dataset files from accidental overwriting.
    existing_files = [
        path for path in [CSV_FILE, JSONL_FILE, MANIFEST_FILE]
        if path.exists()
    ]

    if existing_files:
        names = ", ".join(path.name for path in existing_files)
        raise FileExistsError(
            f"Dataset files already exist: {names}. "
            "Move or back them up before generating again."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


    container_ids = sorted(CONTAINER_ROUTES.keys())

    # Give each container an independent route clock.
    clocks = {
        container_id: FakeClock()
        for container_id in container_ids
    }

    simulators = {
        container_id: LocationSimulator(
            clock=clocks[container_id]
        )
        for container_id in container_ids
    }

    events = []

    for sample_number in range(RECORDS_PER_CONTAINER):

        timestamp = BASE_TIMESTAMP + timedelta(
            minutes=sample_number * INTERVAL_MINUTES
        )

        for container_id in container_ids:

            if sample_number > 0:
                clocks[container_id].advance(
                    INTERVAL_MINUTES * 60
                )

            latitude, longitude = (
                simulators[container_id].get_current_location(
                    container_id
                )
            )

            # Deterministic event ID for reproducibility.
            event_id = str(
                uuid.uuid5(
                    namespace,
                    f"atmosync-day8-{container_id}-{sample_number}"
                )
            )

            event = {
                "event_id": event_id,
                "container_id": container_id,
                "timestamp": timestamp.isoformat().replace(
                    "+00:00", "Z"
                ),
                "temperature_c": round(
                    rng.uniform(*TEMPERATURE_RANGE), 2
                ),
                "humidity_pct": round(
                    rng.uniform(*HUMIDITY_RANGE), 2
                ),
                "vibration_g": round(
                    rng.uniform(*VIBRATION_RANGE), 3
                ),
                "latitude": latitude,
                "longitude": longitude,
                "source_type": SOURCE_TYPE,
            }

            valid, message = validate_event(event)

            if not valid:
                raise ValueError(
                    f"Invalid event {event_id}: {message}"
                )

            events.append(event)

    # Export CSV.
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(events)

    # Export JSON Lines.
    with open(JSONL_FILE, "w", encoding="utf-8") as file:
        for event in events:
            file.write(json.dumps(event) + "\n")

    # Document route provenance.
    route_provenance = {
        "CONT001": "OpenStreetMap-derived road route",
        "CONT002": "Illustrative rail waypoints",
        "CONT003": "Illustrative road waypoints",
        "CONT004": "Illustrative rail waypoints",
        "CONT005": "Illustrative sea waypoints",
    }

    manifest = {
        "dataset_name": "AtmoSync Synthetic Historical Telemetry",
        "dataset_type": "synthetic_simulated",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "records_per_container": RECORDS_PER_CONTAINER,
        "total_records": len(events),
        "container_ids": container_ids,
        "interval_minutes": INTERVAL_MINUTES,
        "base_timestamp": BASE_TIMESTAMP.isoformat(),
        "last_timestamp": events[-1]["timestamp"],
        "schema_fields": FIELDS,
        "transport_speeds_kmh": TRANSPORT_SPEED_KMH,
        "route_provenance": route_provenance,
        "validation": {
            "validator": "simulator.data_validator.validate_event",
            "validated_records": len(events),
            "invalid_records": 0,
        },
        "output_files": [
            CSV_FILE.name,
            JSONL_FILE.name,
            MANIFEST_FILE.name,
        ],
    }

    with open(
        MANIFEST_FILE, "w", encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=4)

    print("\nHistorical telemetry dataset generated successfully.")
    print(f"Total records: {len(events)}")
    print(f"Containers: {len(container_ids)}")
    print(f"Records per container: {RECORDS_PER_CONTAINER}")
    print(f"Validated records: {len(events)}")
    print(f"Invalid records: 0")
    print(f"\nOutput folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_dataset()
