import csv
import json
import uuid
from datetime import datetime, timezone

import pytest

from scripts.generate_time_window_telemetry_fixtures import generate_time_window_telemetry_fixtures
from simulator.container_metadata import load_container_metadata
from simulator.data_validator import validate_event
from simulator.product_reference import load_product_references


@pytest.fixture
def generated_fixture(tmp_path, monkeypatch):
    from simulator import event_builder

    monkeypatch.setattr(
        event_builder.location_simulator,
        "get_current_location",
        lambda container_id: (28.61393, 77.20877),
    )
    return generate_time_window_telemetry_fixtures(
        tmp_path / "time_window_analytics",
        metadata=load_container_metadata(),
        references=load_product_references(),
    )


def _read_jsonl(path):
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def _read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_fixture_has_65_events_and_13_per_container(generated_fixture):
    events = _read_jsonl(generated_fixture["events"])
    assert len(events) == 65
    assert {container_id: sum(e["container_id"] == container_id for e in events)
            for container_id in {e["container_id"] for e in events}} == {
        "CONT001": 13,
        "CONT002": 13,
        "CONT003": 13,
        "CONT004": 13,
        "CONT005": 13,
    }


def test_fixture_preserves_existing_nine_field_event_schema(generated_fixture):
    expected = {
        "event_id", "container_id", "timestamp", "temperature_c",
        "humidity_pct", "vibration_g", "latitude", "longitude", "source_type",
    }
    events = _read_jsonl(generated_fixture["events"])
    assert all(set(event) == expected for event in events)
    assert all(validate_event(event)[0] for event in events)
    assert len({event["event_id"] for event in events}) == 65
    for event in events:
        uuid.UUID(event["event_id"])


def test_fixture_contains_product_specific_excursions_and_recovery(generated_fixture):
    events = _read_jsonl(generated_fixture["events"])
    scenarios = {
        row["container_id"]: row
        for row in _read_csv(generated_fixture["scenario_manifest"])
    }
    for container_id, scenario in scenarios.items():
        records = [event for event in events if event["container_id"] == container_id]
        by_time = sorted(records, key=lambda event: event["timestamp"])
        assert len(by_time) == 13

        temp_value = float(scenario["synthetic_excursion_temperature_c"])
        humidity_value = float(scenario["synthetic_excursion_humidity_pct"])
        temp_min = float(scenario["recommended_temp_min_c"])
        temp_max = float(scenario["recommended_temp_max_c"])
        humidity_min = float(scenario["recommended_humidity_min_pct"])
        humidity_max = float(scenario["recommended_humidity_max_pct"])

        at_10 = next(event for event in by_time if event["timestamp"].endswith("10:10:00Z"))
        at_15 = next(event for event in by_time if event["timestamp"].endswith("10:15:00Z"))
        at_20 = next(event for event in by_time if event["timestamp"].endswith("10:20:00Z"))
        at_25 = next(event for event in by_time if event["timestamp"].endswith("10:25:00Z"))
        at_30 = next(event for event in by_time if event["timestamp"].endswith("10:30:00Z"))

        assert at_10["temperature_c"] == temp_value
        assert at_15["temperature_c"] == temp_value
        assert not temp_min <= at_10["temperature_c"] <= temp_max
        assert temp_min <= at_20["temperature_c"] <= temp_max
        assert at_20["humidity_pct"] == humidity_value
        assert at_25["humidity_pct"] == humidity_value
        assert not humidity_min <= at_20["humidity_pct"] <= humidity_max
        assert humidity_min <= at_30["humidity_pct"] <= humidity_max


def test_arrival_manifest_is_monotonic_and_marks_one_late_event_per_container(
    generated_fixture,
):
    arrivals = _read_csv(generated_fixture["arrival_manifest"])
    assert len(arrivals) == 65
    assert [int(row["arrival_sequence"]) for row in arrivals] == list(range(1, 66))

    ingestion_times = [
        datetime.fromisoformat(row["simulated_ingestion_timestamp_utc"].replace("Z", "+00:00"))
        for row in arrivals
    ]
    assert all(later >= earlier for earlier, later in zip(ingestion_times, ingestion_times[1:]))

    late = [row for row in arrivals if row["is_late_arrival"] == "true"]
    assert len(late) == 5
    assert {row["container_id"] for row in late} == {
        "CONT001", "CONT002", "CONT003", "CONT004", "CONT005"
    }
    assert all(row["delivery_phase"] == "late" for row in late)


def test_event_time_gap_is_20_minutes_with_three_missing_five_minute_slots(
    generated_fixture,
):
    events = _read_jsonl(generated_fixture["events"])
    for container_id in {event["container_id"] for event in events}:
        timestamps = sorted(
            datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            for event in events
            if event["container_id"] == container_id
        )
        intervals = [
            (later - earlier).total_seconds()
            for earlier, later in zip(timestamps, timestamps[1:])
        ]
        assert 1200.0 in intervals
        assert intervals.count(300.0) == 11


def test_scenario_manifest_labels_reference_and_synthetic_assumptions(generated_fixture):
    scenarios = _read_csv(generated_fixture["scenario_manifest"])
    assert len(scenarios) == 5
    assert {row["reference_data_source"] for row in scenarios} == {"FAO"}
    assert all(
        row["data_label"] == "synthetic_simulated_time_window_fixture"
        for row in scenarios
    )
    assert all(
        int(row["expected_missing_5_minute_readings_in_gap"]) == 3
        for row in scenarios
    )
