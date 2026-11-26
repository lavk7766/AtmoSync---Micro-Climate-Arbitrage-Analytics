"""Prototype market-aware arbitrage evaluator for AtmoSync.

This module combines market-price observations, shipment metadata,
route estimates and the existing draft spoilage/arbitrage equations.

It is a prototype, not a production routing or financial system.
All route costs, remaining shelf life, aging factors and sensor-quality
decisions must be supplied explicitly by the caller.
"""

import csv
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from numbers import Real
from pathlib import Path

from simulator.arbitrage_validation import (
    calculate_market_value,
    is_reroute_recommended,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PRICE_PATH = (
    PROJECT_ROOT
    / "data/processed/synthetic_market_prices/"
    / "synthetic_local_market_prices.csv"
)


@dataclass(frozen=True)
class ArbitrageDecision:
    """Outcome and financial comparison for one alternative destination."""

    status: str
    reason: str
    container_id: str
    product_name: str
    planned_destination: str
    alternative_destination: str
    quantity_kg: float
    as_of_date: str

    planned_price_inr_per_kg: float | None
    alternative_price_inr_per_kg: float | None

    planned_remaining_at_arrival_hours: float | None
    alternative_remaining_at_arrival_hours: float | None

    planned_quality_at_arrival: float | None
    alternative_quality_at_arrival: float | None

    planned_value_after_transport_inr: float | None
    alternative_value_after_transport_inr: float | None
    alternative_value_difference_inr: float | None

    planned_price_source_type: str | None
    alternative_price_source_type: str | None

    planned_route_source_type: str
    alternative_route_source_type: str


def _text(record, field, label):
    value = record.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")

    return value.strip()


def _finite_number(name, value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number.")

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")

    return number


def load_market_price_records(path=DEFAULT_PRICE_PATH):
    """Load market prices from the generated CSV."""

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Market price dataset not found: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        records = list(csv.DictReader(file))

    if not records:
        raise ValueError("Market price dataset contains no records.")

    return records


def _validate_shipment(shipment):
    if not isinstance(shipment, Mapping):
        raise ValueError("shipment must be a mapping.")

    container_id = _text(
        shipment,
        "container_id",
        "container_id",
    )

    product_name = _text(
        shipment,
        "product_name",
        "product_name",
    )

    origin = _text(shipment, "origin", "shipment origin")

    raw_quantity = shipment.get("quantity")

    # CSV DictReader returns numeric fields as strings.
    # Convert valid numeric strings before applying numeric validation.
    if isinstance(raw_quantity, str):
        raw_quantity = raw_quantity.strip()

        if not raw_quantity:
            raise ValueError("shipment quantity must not be empty.")

        try:
            raw_quantity = float(raw_quantity)
        except ValueError as exc:
            raise ValueError(
                "shipment quantity must be numeric."
            ) from exc

    quantity = _finite_number(
        "shipment quantity",
        raw_quantity,
    )

    if quantity <= 0:
        raise ValueError("shipment quantity must be greater than zero.")

    quantity_unit = _text(
        shipment,
        "quantity_unit",
        "quantity_unit",
    ).lower()

    unit_multipliers = {
        "kg": 1.0,
        "tonne": 1000.0,
    }

    if quantity_unit not in unit_multipliers:
        raise ValueError(
            "Unsupported shipment quantity unit. "
            "Use kg or tonne explicitly."
        )

    quantity_kg = quantity * unit_multipliers[quantity_unit]

    return container_id, product_name, origin, quantity_kg


def _validate_route(route, label, expected_origin):
    if not isinstance(route, Mapping):
        raise ValueError(f"{label} must be a route mapping.")

    origin = _text(route, "origin", f"{label} origin")
    destination = _text(
        route,
        "destination",
        f"{label} destination",
    )

    if origin.casefold() != expected_origin.casefold():
        raise ValueError(
            f"{label} origin does not match shipment origin."
        )

    distance = _finite_number(
        f"{label} distance_km",
        route.get("distance_km"),
    )

    travel_hours = _finite_number(
        f"{label} estimated_travel_hours",
        route.get("estimated_travel_hours"),
    )

    transport_cost = _finite_number(
        f"{label} transport_cost",
        route.get("transport_cost"),
    )

    currency = _text(
        route,
        "currency",
        f"{label} currency",
    ).upper()

    source_type = _text(
        route,
        "source_type",
        f"{label} source_type",
    )

    if distance <= 0:
        raise ValueError(f"{label} distance must be greater than zero.")

    if travel_hours <= 0:
        raise ValueError(
            f"{label} estimated travel time must be greater than zero."
        )

    if transport_cost < 0:
        raise ValueError(f"{label} transport cost cannot be negative.")

    if currency != "INR":
        raise ValueError(
            f"{label} transport currency must be INR."
        )

    return {
        "origin": origin,
        "destination": destination,
        "distance_km": distance,
        "estimated_travel_hours": travel_hours,
        "transport_cost": transport_cost,
        "currency": currency,
        "source_type": source_type,
    }


def _lookup_price(
    records,
    product_name,
    market_name,
    as_of_date,
):
    """Find exactly one usable INR/kg price for a product-market-date."""

    matches = []

    for record in records:
        if not isinstance(record, Mapping):
            continue

        record_product = record.get("product_name")
        record_market = record.get("market_name")
        record_date = record.get("simulated_as_of_date")

        if (
            isinstance(record_product, str)
            and isinstance(record_market, str)
            and isinstance(record_date, str)
            and record_product.strip().casefold()
            == product_name.casefold()
            and record_market.strip().casefold()
            == market_name.casefold()
            and record_date.strip() == as_of_date
        ):
            matches.append(record)

    if not matches:
        return None, None, (
            f"No price found for {product_name} in {market_name} "
            f"on {as_of_date}."
        )

    if len(matches) != 1:
        return None, None, (
            f"Multiple matching prices found for "
            f"{product_name} in {market_name} on {as_of_date}."
        )

    record = matches[0]

    currency = record.get("currency")
    quantity_unit = record.get("quantity_unit")

    if not isinstance(currency, str) or currency.upper() != "INR":
        return None, None, (
            f"Price for {market_name} is not explicitly denominated in INR."
        )

    if (
        not isinstance(quantity_unit, str)
        or quantity_unit.strip().lower() != "kg"
    ):
        return None, None, (
            f"Price for {market_name} is not explicitly quoted per kg."
        )

    source_type = (
        record.get("price_source_type")
        or record.get("source_type")
    )

    if not isinstance(source_type, str) or not source_type.strip():
        return None, None, (
            f"Price source type is missing for {market_name}."
        )

    try:
        price = _finite_number(
            f"price in {market_name}",
            float(record["price_per_kg"]),
        )
    except (KeyError, TypeError, ValueError):
        return None, None, (
            f"Price value is missing or invalid for {market_name}."
        )

    if price <= 0:
        return None, None, (
            f"Price for {market_name} must be greater than zero."
        )

    return price, source_type.strip(), None


def _incomplete_decision(
    *,
    reason,
    container_id,
    product_name,
    planned_route,
    alternative_route,
    quantity_kg,
    as_of_date,
    planned_price=None,
    alternative_price=None,
    planned_source=None,
    alternative_source=None,
):
    return ArbitrageDecision(
        status="INSUFFICIENT_DATA",
        reason=reason,
        container_id=container_id,
        product_name=product_name,
        planned_destination=planned_route["destination"],
        alternative_destination=alternative_route["destination"],
        quantity_kg=quantity_kg,
        as_of_date=as_of_date,
        planned_price_inr_per_kg=planned_price,
        alternative_price_inr_per_kg=alternative_price,
        planned_remaining_at_arrival_hours=None,
        alternative_remaining_at_arrival_hours=None,
        planned_quality_at_arrival=None,
        alternative_quality_at_arrival=None,
        planned_value_after_transport_inr=None,
        alternative_value_after_transport_inr=None,
        alternative_value_difference_inr=None,
        planned_price_source_type=planned_source,
        alternative_price_source_type=alternative_source,
        planned_route_source_type=planned_route["source_type"],
        alternative_route_source_type=alternative_route["source_type"],
    )


def evaluate_reroute_option(
    *,
    shipment,
    planned_route,
    alternative_route,
    price_records: Iterable[Mapping],
    as_of_date,
    remaining_shelf_life_hours,
    initial_shelf_life_hours,
    expected_aging_factor,
    risk_level,
    sensor_data_sufficient,
):
    """Compare one alternative destination with the planned destination.

    Financial outputs are estimated destination values after transport.
    They are not complete profits because acquisition and other costs
    are not deducted.

    The draft rerouting condition from arbitrage_validation.py is retained:
    HIGH_RISK, sufficient sensor data, positive remaining shelf life,
    and higher alternative value.
    """

    container_id, product_name, origin, quantity_kg = (
        _validate_shipment(shipment)
    )

    planned_route = _validate_route(
        planned_route,
        "planned_route",
        origin,
    )

    alternative_route = _validate_route(
        alternative_route,
        "alternative_route",
        origin,
    )

    if (
        planned_route["destination"].casefold()
        == alternative_route["destination"].casefold()
    ):
        raise ValueError(
            "Alternative destination must differ from planned destination."
        )

    if not isinstance(as_of_date, str):
        raise ValueError("as_of_date must be an ISO date string.")

    try:
        date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise ValueError(
            "as_of_date must use YYYY-MM-DD format."
        ) from exc

    if not isinstance(sensor_data_sufficient, bool):
        raise ValueError(
            "sensor_data_sufficient must be True or False."
        )

    if not isinstance(risk_level, str) or not risk_level.strip():
        raise ValueError("risk_level must be a non-empty string.")

    # Validate financial and shelf-life inputs even when sensor data
    # is insufficient, so malformed caller inputs are not concealed.
    initial_life = _finite_number(
        "initial_shelf_life_hours",
        initial_shelf_life_hours,
    )

    remaining_life = _finite_number(
        "remaining_shelf_life_hours",
        remaining_shelf_life_hours,
    )

    aging_factor = _finite_number(
        "expected_aging_factor",
        expected_aging_factor,
    )

    if initial_life <= 0:
        raise ValueError("initial_shelf_life_hours must be positive.")

    if remaining_life < 0 or remaining_life > initial_life:
        raise ValueError(
            "remaining_shelf_life_hours must be between zero "
            "and initial shelf life."
        )

    if aging_factor < 1:
        raise ValueError("expected_aging_factor must be at least one.")

    if not sensor_data_sufficient:
        return _incomplete_decision(
            reason=(
                "Sensor data is insufficient under the supplied "
                "data-quality assessment. No rerouting decision is made."
            ),
            container_id=container_id,
            product_name=product_name,
            planned_route=planned_route,
            alternative_route=alternative_route,
            quantity_kg=quantity_kg,
            as_of_date=as_of_date,
        )

    try:
        records = list(price_records)
    except TypeError as exc:
        raise ValueError(
            "price_records must be an iterable of price records."
        ) from exc

    planned_price, planned_source, planned_issue = _lookup_price(
        records,
        product_name,
        planned_route["destination"],
        as_of_date,
    )

    alternative_price, alternative_source, alternative_issue = (
        _lookup_price(
            records,
            product_name,
            alternative_route["destination"],
            as_of_date,
        )
    )

    if planned_issue or alternative_issue:
        reasons = [
            reason
            for reason in (planned_issue, alternative_issue)
            if reason
        ]

        return _incomplete_decision(
            reason=" ".join(reasons),
            container_id=container_id,
            product_name=product_name,
            planned_route=planned_route,
            alternative_route=alternative_route,
            quantity_kg=quantity_kg,
            as_of_date=as_of_date,
            planned_price=planned_price,
            alternative_price=alternative_price,
            planned_source=planned_source,
            alternative_source=alternative_source,
        )

    planned_assessment = calculate_market_value(
        price_per_kg=planned_price,
        quantity_kg=quantity_kg,
        remaining_shelf_life_hours=remaining_life,
        initial_shelf_life_hours=initial_life,
        travel_hours=planned_route["estimated_travel_hours"],
        expected_aging_factor=aging_factor,
        transport_cost=planned_route["transport_cost"],
    )

    alternative_assessment = calculate_market_value(
        price_per_kg=alternative_price,
        quantity_kg=quantity_kg,
        remaining_shelf_life_hours=remaining_life,
        initial_shelf_life_hours=initial_life,
        travel_hours=alternative_route["estimated_travel_hours"],
        expected_aging_factor=aging_factor,
        transport_cost=alternative_route["transport_cost"],
    )

    reroute = is_reroute_recommended(
        risk_level=risk_level,
        alternative_remaining_at_arrival_hours=(
            alternative_assessment.remaining_at_arrival_hours
        ),
        alternative_net_value=alternative_assessment.expected_net_value,
        planned_destination_net_value=(
            planned_assessment.expected_net_value
        ),
        sensor_data_sufficient=sensor_data_sufficient,
    )

    difference = (
        alternative_assessment.expected_net_value
        - planned_assessment.expected_net_value
    )

    if reroute:
        status = "REROUTE_RECOMMENDED"
        reason = (
            "All supplied draft rerouting conditions passed: HIGH_RISK, "
            "sufficient sensor data, positive alternative remaining "
            "shelf life and higher estimated value after transport."
        )
    else:
        status = "KEEP_PLANNED_ROUTE"

        if risk_level.strip().upper() != "HIGH_RISK":
            reason = (
                "The draft rerouting rule requires HIGH_RISK status."
            )
        elif alternative_assessment.remaining_at_arrival_hours <= 0:
            reason = (
                "Alternative arrival leaves no remaining shelf life."
            )
        else:
            reason = (
                "Alternative estimated value after transport does not "
                "exceed the planned destination value."
            )

    return ArbitrageDecision(
        status=status,
        reason=reason,
        container_id=container_id,
        product_name=product_name,
        planned_destination=planned_route["destination"],
        alternative_destination=alternative_route["destination"],
        quantity_kg=quantity_kg,
        as_of_date=as_of_date,
        planned_price_inr_per_kg=planned_price,
        alternative_price_inr_per_kg=alternative_price,
        planned_remaining_at_arrival_hours=(
            planned_assessment.remaining_at_arrival_hours
        ),
        alternative_remaining_at_arrival_hours=(
            alternative_assessment.remaining_at_arrival_hours
        ),
        planned_quality_at_arrival=(
            planned_assessment.quality_at_arrival
        ),
        alternative_quality_at_arrival=(
            alternative_assessment.quality_at_arrival
        ),
        planned_value_after_transport_inr=(
            planned_assessment.expected_net_value
        ),
        alternative_value_after_transport_inr=(
            alternative_assessment.expected_net_value
        ),
        alternative_value_difference_inr=difference,
        planned_price_source_type=planned_source,
        alternative_price_source_type=alternative_source,
        planned_route_source_type=planned_route["source_type"],
        alternative_route_source_type=alternative_route["source_type"],
    )
