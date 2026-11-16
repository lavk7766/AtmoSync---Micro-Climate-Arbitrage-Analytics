from datetime import datetime, timedelta, timezone

import pytest

from simulator.simulation_clock import SimulationClock


class FakeMonotonic:
    """Controllable replacement for time.monotonic()."""

    def __init__(self, initial_value=100.0):
        self.value = initial_value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


@pytest.mark.parametrize(
    "multiplier",
    [
        0,
        -1,
        -0.5,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        False,
        "2",
        None,
    ],
)
def test_invalid_multiplier_is_rejected(multiplier):
    with pytest.raises(ValueError, match="positive finite number"):
        SimulationClock(multiplier=multiplier)


def test_naive_start_time_is_rejected():
    start = datetime(2026, 11, 16, 12, 0, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        SimulationClock(start_time=start)


def test_start_time_is_normalized_to_utc():
    fake_time = FakeMonotonic()

    local_timezone = timezone(timedelta(hours=5, minutes=30))
    start = datetime(
        2026, 11, 16, 12, 0, 0,
        tzinfo=local_timezone,
    )

    clock = SimulationClock(
        multiplier=1,
        start_time=start,
        monotonic_fn=fake_time,
    )

    assert clock.now() == start.astimezone(timezone.utc)
    assert clock.now().utcoffset() == timedelta(0)


def test_clock_starts_with_zero_elapsed_time():
    fake_time = FakeMonotonic()
    start = datetime(2026, 11, 16, 6, 30, tzinfo=timezone.utc)

    clock = SimulationClock(
        multiplier=1,
        start_time=start,
        monotonic_fn=fake_time,
    )

    assert clock.elapsed_seconds() == 0.0
    assert clock.now() == start


def test_accelerated_clock_advances_correctly():
    fake_time = FakeMonotonic()
    start = datetime(2026, 11, 16, 6, 30, tzinfo=timezone.utc)

    clock = SimulationClock(
        multiplier=60,
        start_time=start,
        monotonic_fn=fake_time,
    )

    fake_time.advance(2.5)

    assert clock.elapsed_seconds() == 150.0
    assert clock.now() == start + timedelta(seconds=150)


def test_clock_clamps_negative_elapsed_time_to_zero():
    fake_time = FakeMonotonic()
    start = datetime(2026, 11, 16, 6, 30, tzinfo=timezone.utc)

    clock = SimulationClock(
        multiplier=10,
        start_time=start,
        monotonic_fn=fake_time,
    )

    # Simulate an unexpected backwards monotonic reading.
    fake_time.advance(-5)

    assert clock.elapsed_seconds() == 0.0
    assert clock.now() == start


def test_normal_speed_clock_advances_one_second_per_second():
    fake_time = FakeMonotonic()
    start = datetime(2026, 11, 16, 6, 30, tzinfo=timezone.utc)

    clock = SimulationClock(
        multiplier=1,
        start_time=start,
        monotonic_fn=fake_time,
    )

    fake_time.advance(5)

    assert clock.elapsed_seconds() == 5.0
    assert clock.now() == start + timedelta(seconds=5)
