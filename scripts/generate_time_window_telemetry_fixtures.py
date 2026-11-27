"""Generate reproducible Synthetic time-window telemetry fixtures.

The JSONL file preserves the existing nine-field SensorEvent payload.
Arrival/ingestion order is intentionally kept in a separate CSV manifest.
All generated data is synthetic and intended for development/testing only.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator import event_builder
from simulator.config import HUMIDITY_RANGE, TEMPERATURE_RANGE
from simulator.container_metadata import load_container_metadata
from simulator.data_validator import validate_event
from simulator.humidity_fault_injector import (
    HumidityFaultInjector,
    HumidityFaultWindow,
)
from simulator.product_reference import (
    find_product_reference,
    load_product_references,
)
from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)


START_AT = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)
NOMINAL_INTERVAL_SECONDS = 5 * 60
TEMPERATURE_FAULT_START_MINUTE = 10
TEMPERATURE_FAULT_END_MINUTE = 20
HUMIDITY_FAULT_START_MINUTE = 20
HUMIDITY_FAULT_END_MINUTE = 30
LATE_EVENT_MINUTE = 50
POST_GAP_EVENT_MINUTE = 70
FINAL_EVENT_MINUTE = 75

EVENT_FIELDS = {
    "event_id",
    "container_id",
    "timestamp",
    "temperature_c",
    "humidity_pct",
    "vibration_g",
    "latitude",
    "longitude",
    "source_type",
}

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "scenarios" / "time_window_analytics"


class _SequenceClock:
    """Small clock adapter allowing the existing event builder to be replayed."""

    def __init__(self, timestamps: Iterable[datetime]):
        self._timestamps = iter(timestamps)

    def now(self) -> datetime:
        return next(self._timestamps)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _physical_bounds(bounds, field_name: str) -> tuple[float, float]:
    if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
        raise ValueError(f"{field_name} must be a two-value range in simulator.config")
    lower, upper = float(bounds[0]), float(bounds[1])
    if lower > upper:
        raise ValueError(f"Invalid {field_name} in simulator.config")
    return lower, upper


def _choose_temperature_excursion(reference) -> float:
    """Choose an out-of-product-range value inside global simulator limits."""
    physical_min, physical_max = _physical_bounds(
        TEMPERATURE_RANGE, "TEMPERATURE_RANGE"
    )
    product_min = reference.recommended_temp_min_c
    product_max = reference.recommended_temp_max_c
    candidates = (
        product_max + 5.0,
        product_min - 5.0,
        product_max + 1.0,
        product_min - 1.0,
    )
    for value in candidates:
        if physical_min <= value <= physical_max and not product_min <= value <= product_max:
            return float(value)
    raise ValueError(
        f"No physically permitted temperature excursion exists for "
        f"{reference.product_name} ({product_min} to {product_max} C)"
    )


def _choose_humidity_excursion(reference) -> float:
    """Choose an out-of-product-range value inside global simulator limits."""
    physical_min, physical_max = _physical_bounds(
        HUMIDITY_RANGE, "HUMIDITY_RANGE"
    )
    product_min = reference.humidity_min_pct
    product_max = reference.humidity_max_pct
    candidates = (
        product_min - 10.0,
        product_max + 5.0,
        product_min - 1.0,
        product_max + 1.0,
    )
    for value in candidates:
        if (
            physical_min <= value <= physical_max
            and 0.0 <= value <= 100.0
            and not product_min <= value <= product_max
        ):
            return float(value)
    raise ValueError(
        f"No physically permitted humidity excursion exists for "
        f"{reference.product_name} ({product_min} to {product_max} %)"
    )


def _build_arrival_plan(container_ids: list[str]):
    """Build event delivery order, deliberately delivering 50m after 70m."""
    regular_minutes = list(range(0, 50, 5))  # 0, 5, ..., 45
    plan = [
        (container_id, minute, "on_time")
        for minute in regular_minutes
        for container_id in container_ids
    ]
    plan.extend(
        (container_id, POST_GAP_EVENT_MINUTE, "post_gap")
        for container_id in container_ids
    )
    plan.extend(
        (container_id, LATE_EVENT_MINUTE, "late")
        for container_id in container_ids
    )
    plan.extend(
        (container_id, FINAL_EVENT_MINUTE, "on_time")
        for container_id in container_ids
    )
    return plan


def _arrival_timestamp(
    event_timestamp: datetime, phase: str, index: int, start_at: datetime
) -> datetime:
    """Create monotonic synthetic ingestion times, independent of event time."""
    if phase == "late":
        # The 50-minute event is delivered just after the 70-minute event.
        return start_at + timedelta(
            minutes=POST_GAP_EVENT_MINUTE,
            seconds=6 + index,
        )
    if phase == "post_gap":
        return start_at + timedelta(
            minutes=POST_GAP_EVENT_MINUTE,
            seconds=1 + index,
        )
    return event_timestamp + timedelta(seconds=1 + index)


def generate_time_window_telemetry_fixtures(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    metadata=None,
    references=None,
    start_at: datetime = START_AT,
) -> dict[str, Path]:
    """Generate telemetry JSONL and companion arrival/scenario manifests."""
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ValueError("start_at must be timezone-aware")
    start_at = start_at.astimezone(timezone.utc)

    metadata = metadata if metadata is not None else load_container_metadata()
    references = references if references is not None else load_product_references()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    container_ids = sorted(metadata)
    if not container_ids:
        raise ValueError("No container metadata records are available")

    references_by_container = {}
    temperature_injector_schedules = {}
    humidity_injector_schedules = {}
    scenario_rows = []

    for container_id in container_ids:
        container = metadata[container_id]
        reference = find_product_reference(references, container.product_name)
        references_by_container[container_id] = reference

        temp_value = _choose_temperature_excursion(reference)
        humidity_value = _choose_humidity_excursion(reference)
        temp_start = start_at + timedelta(minutes=TEMPERATURE_FAULT_START_MINUTE)
        temp_end = start_at + timedelta(minutes=TEMPERATURE_FAULT_END_MINUTE)
        humidity_start = start_at + timedelta(minutes=HUMIDITY_FAULT_START_MINUTE)
        humidity_end = start_at + timedelta(minutes=HUMIDITY_FAULT_END_MINUTE)

        temperature_injector_schedules[container_id] = [
            TemperatureFaultWindow(
                start_at=temp_start,
                end_at=temp_end,
                temperature_c=temp_value,
                label="high_temperature_time_window_excursion",
            )
        ]
        humidity_injector_schedules[container_id] = [
            HumidityFaultWindow(
                start_at=humidity_start,
                end_at=humidity_end,
                humidity_pct=humidity_value,
                label="low_humidity_time_window_excursion",
            )
        ]

        scenario_rows.append(
            {
                "container_id": container_id,
                "origin": container.origin,
                "destination": container.destination,
                "quantity": container.quantity,
                "quantity_unit": container.quantity_unit,
                "batch_id": container.batch_id,
                "shipment_source_type": container.source_type,
                "product_name": reference.product_name,
                "product_stage_or_variety": reference.product_stage_or_variety,
                "reference_data_source": reference.data_source,
                "reference_source_url": reference.source_url,
                "recommended_temp_min_c": reference.recommended_temp_min_c,
                "recommended_temp_max_c": reference.recommended_temp_max_c,
                "recommended_humidity_min_pct": reference.humidity_min_pct,
                "recommended_humidity_max_pct": reference.humidity_max_pct,
                "synthetic_excursion_temperature_c": temp_value,
                "synthetic_excursion_humidity_pct": humidity_value,
                "temperature_fault_start_utc": _iso_utc(temp_start),
                "temperature_fault_end_utc_exclusive": _iso_utc(temp_end),
                "humidity_fault_start_utc": _iso_utc(humidity_start),
                "humidity_fault_end_utc_exclusive": _iso_utc(humidity_end),
                "nominal_sampling_interval_seconds": NOMINAL_INTERVAL_SECONDS,
                "intentional_event_time_gap_start_utc": _iso_utc(
                    start_at + timedelta(minutes=LATE_EVENT_MINUTE)
                ),
                "intentional_event_time_gap_end_utc": _iso_utc(
                    start_at + timedelta(minutes=POST_GAP_EVENT_MINUTE)
                ),
                "expected_missing_5_minute_readings_in_gap": 3,
                "data_label": "synthetic_simulated_time_window_fixture",
            }
        )

    temp_injector = TemperatureFaultInjector(temperature_injector_schedules)
    humidity_injector = HumidityFaultInjector(humidity_injector_schedules)
    arrival_plan = _build_arrival_plan(container_ids)
    event_timestamps = [
        start_at + timedelta(minutes=minute)
        for _, minute, _ in arrival_plan
    ]

    previous_clock = event_builder.simulation_clock
    random_state = random.getstate()
    event_rows = []
    arrival_rows = []
    latest_event_time_by_container = {}

    try:
        event_builder.simulation_clock = _SequenceClock(event_timestamps)
        random.seed(17017)

        for arrival_sequence, (container_id, minute, phase) in enumerate(
            arrival_plan, start=1
        ):
            reference = references_by_container[container_id]
            event = event_builder.build_sensor_event(
                container_id,
                product_reference=reference,
                fault_injector=temp_injector,
                humidity_fault_injector=humidity_injector,
            )
            payload = event_builder.event_to_dict(event)

            if set(payload) != EVENT_FIELDS:
                raise ValueError(
                    f"Event schema changed for {container_id}: "
                    f"{sorted(payload)}"
                )
            valid, message = validate_event(payload)
            if not valid:
                raise ValueError(
                    f"Generated event failed simulator validation: {message}"
                )

            event_time = event.timestamp.astimezone(timezone.utc)
            previous_latest = latest_event_time_by_container.get(container_id)
            is_late = previous_latest is not None and event_time < previous_latest
            latest_event_time_by_container[container_id] = (
                max(previous_latest, event_time)
                if previous_latest is not None
                else event_time
            )
            ingest_time = _arrival_timestamp(
                event_time,
                phase,
                container_ids.index(container_id),
                start_at,
            )

            event_rows.append(payload)
            arrival_rows.append(
                {
                    "arrival_sequence": arrival_sequence,
                    "event_id": payload["event_id"],
                    "container_id": container_id,
                    "event_timestamp_utc": _iso_utc(event_time),
                    "simulated_ingestion_timestamp_utc": _iso_utc(ingest_time),
                    "event_time_lag_seconds": round(
                        (ingest_time - event_time).total_seconds(), 3
                    ),
                    "is_late_arrival": "true" if is_late else "false",
                    "delivery_phase": phase,
                    "data_label": "synthetic_simulated_not_actual_kafka_offset",
                }
            )
    finally:
        event_builder.simulation_clock = previous_clock
        random.setstate(random_state)

    # Assert manifest ingestion timestamps are monotonic in delivery order.
    ingest_times = [
        datetime.fromisoformat(
            row["simulated_ingestion_timestamp_utc"].replace("Z", "+00:00")
        )
        for row in arrival_rows
    ]
    if any(later < earlier for earlier, later in zip(ingest_times, ingest_times[1:])):
        raise ValueError("Synthetic ingestion timestamps are not monotonic")

    events_file = output_path / "time_window_telemetry_events.jsonl"
    arrival_file = output_path / "time_window_arrival_manifest.csv"
    scenarios_file = output_path / "time_window_scenario_manifest.csv"

    with events_file.open("w", encoding="utf-8", newline="") as file:
        for payload in event_rows:
            file.write(json.dumps(payload, separators=(",", ":")) + "\n")

    _write_csv(arrival_file, arrival_rows)
    _write_csv(scenarios_file, scenario_rows)

    return {
        "events": events_file,
        "arrival_manifest": arrival_file,
        "scenario_manifest": scenarios_file,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write an empty fixture: {path.name}")
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    outputs = generate_time_window_telemetry_fixtures()
    print("Synthetic time-window telemetry fixtures generated:")
    for label, path in outputs.items():
        print(f"{label}: {path}")
    print("Expected telemetry events: 65 (13 per shipment container)")
    print("Expected late arrivals: 5 (one per container)")
    print("Expected intentional event-time gap: 20 minutes per container")
    print("No actual Kafka offsets or freight/commercial outcomes are represented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
