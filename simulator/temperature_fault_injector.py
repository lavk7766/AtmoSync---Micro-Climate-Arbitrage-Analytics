
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from simulator.container_metadata import normalize_container_id
from simulator.product_reference import ProductReference


@dataclass(frozen=True)
class TemperatureFaultWindow:
    """A scheduled period during which temperature is outside its range."""

    start_at: datetime
    end_at: datetime
    temperature_c: float
    label: str = "temperature_excursion"

    def __post_init__(self):
        for field_name, value in (
            ("start_at", self.start_at),
            ("end_at", self.end_at),
        ):
            if (
                not isinstance(value, datetime)
                or value.tzinfo is None
                or value.utcoffset() is None
            ):
                raise ValueError(
                    f"{field_name} must be timezone-aware"
                )

        if self.start_at >= self.end_at:
            raise ValueError("Fault end time must follow start time")

        if (
            isinstance(self.temperature_c, bool)
            or not isinstance(self.temperature_c, (int, float))
            or not math.isfinite(self.temperature_c)
        ):
            raise ValueError(
                "Fault temperature must be a finite number"
            )

        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("Fault label cannot be empty")

        object.__setattr__(
            self,
            "start_at",
            self.start_at.astimezone(timezone.utc),
        )
        object.__setattr__(
            self,
            "end_at",
            self.end_at.astimezone(timezone.utc),
        )
        object.__setattr__(
            self,
            "temperature_c",
            float(self.temperature_c),
        )


class TemperatureFaultInjector:
    """
    Provides scheduled temperature overrides per container.

    Fault windows use a start-inclusive, end-exclusive interval.
    Outside a fault window, None is returned so normal generation
    can continue.
    """

    def __init__(self, schedules=None):
        if schedules is None:
            schedules = {}

        if not isinstance(schedules, Mapping):
            raise TypeError("Schedules must be a mapping")

        self._schedules = {}

        for container_id, windows in schedules.items():
            normalized_id = normalize_container_id(container_id)

            if normalized_id in self._schedules:
                raise ValueError(
                    f"Duplicate container schedule: {normalized_id}"
                )

            windows = tuple(windows)

            if not all(
                isinstance(window, TemperatureFaultWindow)
                for window in windows
            ):
                raise TypeError(
                    "Each schedule must contain TemperatureFaultWindow objects"
                )

            windows = tuple(
                sorted(windows, key=lambda window: window.start_at)
            )

            for index in range(1, len(windows)):
                previous = windows[index - 1]
                current = windows[index]

                if current.start_at < previous.end_at:
                    raise ValueError(
                        f"Overlapping fault windows for {normalized_id}"
                    )

            self._schedules[normalized_id] = windows

    def get_temperature_override(
        self,
        container_id,
        timestamp,
        product_reference,
    ):
        """
        Return an out-of-range temperature during an active fault.

        Return None when no fault is scheduled at the supplied time.
        """
        normalized_id = normalize_container_id(container_id)

        if (
            not isinstance(timestamp, datetime)
            or timestamp.tzinfo is None
            or timestamp.utcoffset() is None
        ):
            raise ValueError("Timestamp must be timezone-aware")

        timestamp = timestamp.astimezone(timezone.utc)

        for window in self._schedules.get(normalized_id, ()):
            if window.start_at <= timestamp < window.end_at:

                if not isinstance(product_reference, ProductReference):
                    raise TypeError(
                        "An active fault requires a ProductReference"
                    )

                minimum = product_reference.recommended_temp_min_c
                maximum = product_reference.recommended_temp_max_c

                if minimum <= window.temperature_c <= maximum:
                    raise ValueError(
                        "Fault temperature must be outside the "
                        "product's recommended temperature range"
                    )

                return window.temperature_c

        return None
