import csv
import json
from datetime import datetime
from pathlib import Path

import pytest

from simulator.data_validator import validate_event


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_FILE = (
    PROJECT_ROOT / "data" / "scenarios"
    / "missing_sensor_reading_scenarios.jsonl"
)
METADATA_FILE = (
    PROJECT_ROOT / "data" / "scenarios"
    / "missing_sensor_container_metadata.csv"
)

EXPECTED_EVENT_FIELDS = {
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


@pytest.fixture(scope="module")
def records():
    with SCENARIO_FILE.open("r", encoding="utf-8-sig") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


@pytest.fixture(scope="module")
def payloads(records):
    return [record["event_payload"] for record in records]


def parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_fixture_contains_eleven_unique_events(records, payloads):
    assert len(records) == 11

    event_ids = [event["event_id"] for event in payloads]
    assert len(set(event_ids)) == 11

    assert [record["kafka_offset"] for record in records] == list(range(11))
    assert all(record["kafka_partition"] == 0 for record in records)

    assert {
        record["kafka_topic"] for record in records
    } == {"atmosync_missing_sensor_fixture_20261124"}


def test_fixture_preserves_the_nine_field_event_schema(payloads):
    for event in payloads:
        assert set(event) == EXPECTED_EVENT_FIELDS
        assert event["source_type"] == "synthetic_test_fixture"


def test_fixture_contains_three_dedicated_test_containers(payloads):
    containers = {event["container_id"] for event in payloads}

    assert containers == {
        "TEST_MISSING_TEMP_001",
        "TEST_MISSING_HUM_001",
        "TEST_LONG_GAP_001",
    }


def test_missing_temperature_scenario_is_preserved(payloads):
    events = [
        event for event in payloads
        if event["container_id"] == "TEST_MISSING_TEMP_001"
    ]

    assert len(events) == 4
    assert [event["temperature_c"] for event in events] == [
        2.0, None, 2.0, 2.0
    ]

    times = [parse_timestamp(event["timestamp"]) for event in events]
    assert [
        (later - earlier).total_seconds()
        for earlier, later in zip(times, times[1:])
    ] == [5.0, 5.0, 5.0]


def test_missing_humidity_scenario_is_preserved(payloads):
    events = [
        event for event in payloads
        if event["container_id"] == "TEST_MISSING_HUM_001"
    ]

    assert len(events) == 4
    assert [event["humidity_pct"] for event in events] == [
        93.0, None, 93.0, 93.0
    ]

    times = [parse_timestamp(event["timestamp"]) for event in events]
    assert [
        (later - earlier).total_seconds()
        for earlier, later in zip(times, times[1:])
    ] == [5.0, 5.0, 5.0]


def test_long_gap_and_recovery_scenario_is_preserved(payloads):
    events = [
        event for event in payloads
        if event["container_id"] == "TEST_LONG_GAP_001"
    ]

    assert len(events) == 3

    times = [parse_timestamp(event["timestamp"]) for event in events]
    intervals = [
        (later - earlier).total_seconds()
        for earlier, later in zip(times, times[1:])
    ]

    assert intervals == [20.0, 5.0]


def test_application_validator_accepts_complete_and_rejects_incomplete_events(
    payloads,
):
    accepted = []
    rejected = []

    for event in payloads:
        is_valid, reason = validate_event(event)

        if is_valid:
            accepted.append(event)
        else:
            rejected.append((event, reason))

    assert len(accepted) == 9
    assert len(rejected) == 2

    rejected_fields = {
        event["event_id"]: reason
        for event, reason in rejected
    }

    assert len(rejected_fields) == 2

    assert any(
        "temperature_c" in reason
        for reason in rejected_fields.values()
    )
    assert any(
        "humidity_pct" in reason
        for reason in rejected_fields.values()
    )


def test_metadata_covers_all_fixture_containers(payloads):
    with METADATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        metadata = list(csv.DictReader(file))

    telemetry_containers = {
        event["container_id"] for event in payloads
    }
    metadata_containers = {
        row["container_id"] for row in metadata
    }

    assert len(metadata) == 3
    assert metadata_containers == telemetry_containers

    for row in metadata:
        assert row["product_name"] == "Apple"
        assert float(row["quantity"]) == 100.0
        assert row["quantity_unit"] == "kg"
        assert row["source_type"] == "synthetic_test_fixture"
