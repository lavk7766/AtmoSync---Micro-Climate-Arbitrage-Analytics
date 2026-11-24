"""Prototype arbitrage calculations for independent validation.

These helpers implement the team's documented draft equations.
They are not an operational routing engine or food-safety model.

Distances use Haversine straight-line distance, not road, rail or sea
network distance. Transport speed, aging factor and financial assumptions
must be supplied by the caller.
"""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from numbers import Real


EARTH_RADIUS_KM = 6371.0088


def _finite_number(name, value):
    """Return a finite float, rejecting booleans and missing values."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number.")

    number = float(value)

    if not (number == number and abs(number) != float("inf")):
        raise ValueError(f"{name} must be a finite number.")

    return number


def _coordinate_pair(name, coordinate):
    """Validate and normalize a (latitude, longitude) pair."""
    if not isinstance(coordinate, (tuple, list)) or len(coordinate) != 2:
        raise ValueError(f"{name} must contain latitude and longitude.")

    latitude = _finite_number(f"{name} latitude", coordinate[0])
    longitude = _finite_number(f"{name} longitude", coordinate[1])

    if not -90 <= latitude <= 90:
        raise ValueError(f"{name} latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError(f"{name} longitude must be between -180 and 180.")

    return latitude, longitude


def haversine_distance_km(origin, destination):
    """Calculate straight-line distance between two WGS84 coordinates."""
    lat1, lon1 = _coordinate_pair("origin", origin)
    lat2, lon2 = _coordinate_pair("destination", destination)

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )

    # Protect against minor floating-point rounding outside [0, 1].
    haversine = min(1.0, max(0.0, haversine))

    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def estimate_travel_hours(distance_km, average_speed_kmph):
    """Estimate travel time using distance divided by average speed."""
    distance = _finite_number("distance_km", distance_km)
    speed = _finite_number("average_speed_kmph", average_speed_kmph)

    if distance < 0:
        raise ValueError("distance_km cannot be negative.")

    if speed <= 0:
        raise ValueError("average_speed_kmph must be greater than zero.")

    return distance / speed


@dataclass(frozen=True)
class MarketValueAssessment:
    """Calculated arrival and financial metrics for one market."""

    remaining_at_arrival_hours: float
    quality_at_arrival: float
    expected_net_value: float


def calculate_market_value(
    *,
    price_per_kg,
    quantity_kg,
    remaining_shelf_life_hours,
    initial_shelf_life_hours,
    travel_hours,
    expected_aging_factor,
    transport_cost,
):
    """Apply the documented prototype market-value equation.

    expected_net_value =
        price_per_kg * quantity_kg * quality_at_arrival - transport_cost
    """
    price = _finite_number("price_per_kg", price_per_kg)
    quantity = _finite_number("quantity_kg", quantity_kg)
    remaining = _finite_number(
        "remaining_shelf_life_hours",
        remaining_shelf_life_hours,
    )
    initial = _finite_number(
        "initial_shelf_life_hours",
        initial_shelf_life_hours,
    )
    travel = _finite_number("travel_hours", travel_hours)
    aging_factor = _finite_number(
        "expected_aging_factor",
        expected_aging_factor,
    )
    cost = _finite_number("transport_cost", transport_cost)

    if price < 0:
        raise ValueError("price_per_kg cannot be negative.")

    if quantity <= 0:
        raise ValueError("quantity_kg must be greater than zero.")

    if initial <= 0:
        raise ValueError("initial_shelf_life_hours must be greater than zero.")

    if remaining < 0 or remaining > initial:
        raise ValueError(
            "remaining_shelf_life_hours must be between zero "
            "and initial shelf life."
        )

    if travel < 0:
        raise ValueError("travel_hours cannot be negative.")

    if aging_factor < 1:
        raise ValueError("expected_aging_factor must be at least one.")

    if cost < 0:
        raise ValueError("transport_cost cannot be negative.")

    remaining_at_arrival = max(
        remaining - travel * aging_factor,
        0.0,
    )

    quality_at_arrival = remaining_at_arrival / initial

    expected_net_value = (
        price * quantity * quality_at_arrival - cost
    )

    return MarketValueAssessment(
        remaining_at_arrival_hours=remaining_at_arrival,
        quality_at_arrival=quality_at_arrival,
        expected_net_value=expected_net_value,
    )


def is_reroute_recommended(
    *,
    risk_level,
    alternative_remaining_at_arrival_hours,
    alternative_net_value,
    planned_destination_net_value,
    sensor_data_sufficient,
):
    """Apply the draft reroute decision conditions.

    The caller must determine sensor_data_sufficient using the project's
    approved data-quality policy. This helper deliberately does not decide
    which dbt data-quality statuses qualify.
    """
    if not isinstance(risk_level, str) or not risk_level.strip():
        raise ValueError("risk_level must be a non-empty string.")

    if not isinstance(sensor_data_sufficient, bool):
        raise ValueError("sensor_data_sufficient must be True or False.")

    remaining = _finite_number(
        "alternative_remaining_at_arrival_hours",
        alternative_remaining_at_arrival_hours,
    )
    alternative_value = _finite_number(
        "alternative_net_value",
        alternative_net_value,
    )
    planned_value = _finite_number(
        "planned_destination_net_value",
        planned_destination_net_value,
    )

    if remaining < 0:
        raise ValueError(
            "alternative_remaining_at_arrival_hours cannot be negative."
        )

    return (
        risk_level.strip().upper() == "HIGH_RISK"
        and sensor_data_sufficient
        and remaining > 0
        and alternative_value > planned_value
    )
