
import math
import time
from datetime import datetime, timedelta, timezone

from simulator.config import SIMULATION_TIME_MULTIPLIER


class SimulationClock:
    """Shared clock that can advance faster than real-world time."""

    def __init__(
        self,
        multiplier=SIMULATION_TIME_MULTIPLIER,
        start_time=None,
        monotonic_fn=time.monotonic,
    ):
        if (
            not isinstance(multiplier, (int, float))
            or isinstance(multiplier, bool)
            or not math.isfinite(multiplier)
            or multiplier <= 0
        ):
            raise ValueError("Time multiplier must be a positive finite number")

        self.multiplier = float(multiplier)
        self._monotonic = monotonic_fn
        self._start_monotonic = self._monotonic()

        self._start_time = start_time or datetime.now(timezone.utc)

        if (
            self._start_time.tzinfo is None
            or self._start_time.utcoffset() is None
        ):
            raise ValueError("Start time must be timezone-aware")

        self._start_time = self._start_time.astimezone(timezone.utc)

    def elapsed_seconds(self):
        """Return elapsed simulated time in seconds."""
        real_elapsed = self._monotonic() - self._start_monotonic
        return max(0.0, real_elapsed) * self.multiplier

    def now(self):
        """Return the current simulated UTC timestamp."""
        return self._start_time + timedelta(
            seconds=self.elapsed_seconds()
        )


# One shared clock for the simulator.
simulation_clock = SimulationClock()
