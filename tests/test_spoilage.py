"""Simulator telemetry fixtures for downstream spoilage-mart validation.

These tests verify controlled timestamps and product-specific temperature
excursions. They do not execute or validate the downstream dbt SQL model.
"""

from datetime import datetime, timedelta, timezone

import pytest

import simulator.event_builder as event_builder
from simulator.product_reference import ProductReference
from simulator.temperature_fault_injector import (
    TemperatureFaultInjector,
    TemperatureFaultWindow,
)


START = datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)


def apple_reference():
    return ProductReference(
        product_name="Apple",
        product_stage_or_variety="General fresh apples",
        recommended_temp_min_c=-1.0,
        recommended_temp_max_c=4.0,
        best_temp_c=1.5,
        humidity_min_pct=90.0,
        humidity_max_pct=95.0,
        shelf_life_min_hours=720.0,
        shelf_life_max_hours=8640.0,
        data_source="FAO",
    )


def build_controlled_events(monkeypatch, timestamps, fault_injector=None):
    """Build real simulator events at supplied timestamps without waiting."""
    timestamp_iter = iter(timestamps)

    monkeypatch.setattr(
        event_builder.simulation_clock,
        "now",
        lambda: next(timestamp_iter),
    )

    # Keep route movement outside the scope of these telemetry fixtures.
    monkeypatch.setattr(
        event_builder.location_simulator,
        "get_current_location",
        lambda container_id: (28.61393, 77.20877),
    )

    reference = apple_reference()

    return [
        event_builder.build_sensor_event(
            "CONT001",
            product_reference=reference,
            fault_injector=fault_injector,
        )
        for _ in timestamps
    ]


@pytest.mark.parametrize(
    "interval_seconds",
    [
        pytest.param(5, id="regular-five-second-interval"),
        pytest.param(15, id="observed-interval-upper-boundary"),
        pytest.param(16, id="first-unknown-interval"),
        pytest.param(60, id="long-unknown-interval"),
    ],
)
def test_event_builder_emits_controlled_telemetry_intervals(
    monkeypatch, interval_seconds
):
    """Create events matching the spoilage mart's interval scenarios."""
    timestamps = [
        START,
        START + timedelta(seconds=interval_seconds),
    ]

    events = build_controlled_events(monkeypatch, timestamps)

    assert len(events) == 2
    assert events[0].timestamp == timestamps[0]
    assert events[1].timestamp == timestamps[1]

    actual_interval = (
        events[1].timestamp - events[0].timestamp
    ).total_seconds()

    assert actual_interval == interval_seconds
    assert events[0].event_id != events[1].event_id

    # Normal Apple readings stay inside the prototype reference range.
    for event in events:
        assert -1.0 <= event.temperature_c <= 4.0
        assert 90.0 <= event.humidity_pct <= 95.0


def test_event_builder_emits_fault_start_and_end_boundaries(monkeypatch):
    """A fault is active at its start and inactive at its end timestamp."""
    fault_start = START + timedelta(seconds=5)
    fault_end = START + timedelta(seconds=20)

    window = TemperatureFaultWindow(
        start_at=fault_start,
        end_at=fault_end,
        temperature_c=9.0,
        label="spoilage_fixture_high_temperature_excursion",
    )

    injector = TemperatureFaultInjector({"CONT001": [window]})

    timestamps = [
        START,
        fault_start,
        START + timedelta(seconds=10),
        START + timedelta(seconds=15),
        fault_end,
        fault_end + timedelta(seconds=5),
    ]

    events = build_controlled_events(
        monkeypatch,
        timestamps,
        fault_injector=injector,
    )

    temperatures = [event.temperature_c for event in events]

    assert -1.0 <= temperatures[0] <= 4.0
    assert temperatures[1:4] == [9.0, 9.0, 9.0]
    assert -1.0 <= temperatures[4] <= 4.0
    assert -1.0 <= temperatures[5] <= 4.0

    # Every event in this sequence is five simulated seconds apart.
    intervals = [
        (later.timestamp - earlier.timestamp).total_seconds()
        for earlier, later in zip(events, events[1:])
    ]

    assert intervals == [5.0, 5.0, 5.0, 5.0, 5.0]

    # Preserve the existing nine-field event schema.
    expected_fields = {
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

    for event in events:
        assert set(event_builder.event_to_dict(event)) == expected_fields
