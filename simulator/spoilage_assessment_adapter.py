"""Snowflake spoilage assessment adapter for AtmoSync.

The adapter validates supplied spoilage assessments before they can
be used by the Python arbitrage engine.

It does not calculate shelf life, food safety or spoilage risk.

Prototype eligibility requires explicit, complete sensor-quality
indicators and caller-supplied freshness limits.
"""

import csv
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONTAINER_METADATA_PATH = (
    PROJECT_ROOT / "data/reference/container_metadata.csv"
)

PRODUCT_REFERENCE_PATH = (
    PROJECT_ROOT / "data/reference/product_spoilage_reference.csv"
)

ELIGIBLE = "ELIGIBLE_FOR_ARBITRAGE_EVALUATION"
INSUFFICIENT = "INSUFFICIENT_DATA"

ALLOWED_RISK_LEVELS = {
    "NORMAL",
    "WARNING",
    "HIGH_RISK",
}

REQUIRED_FIELDS = (
    "container_id",
    "product_name",
    "latest_temperature_c",
    "latest_humidity_pct",
    "initial_shelf_life_hours",
    "cumulative_aged_hours",
    "remaining_shelf_life_hours",
    "risk_level",
    "unknown_exposure_hours",
    "reading_count",
    "data_quality_status",
    "latitude",
    "longitude",
    "last_reading_at",
    "is_assumption_based",
    "source_reading_count",
    "missing_temperature_reading_count",
    "missing_humidity_reading_count",
    "missing_temperature_interval_count",
    "missing_temperature_interval_hours",
    "sensor_data_sufficient",
    "assessment_updated_at",
)


@dataclass(frozen=True)
class SpoilageAssessmentResult:
    """Normalized result of spoilage assessment validation."""

    status: str
    reason_codes: tuple[str, ...]

    container_id: str | None
    product_name: str | None

    remaining_shelf_life_hours: float | None
    initial_shelf_life_hours: float | None
    cumulative_aged_hours: float | None

    risk_level: str | None
    data_quality_status: str | None

    latest_temperature_c: float | None
    latest_humidity_pct: float | None

    latitude: float | None
    longitude: float | None

    last_reading_at: datetime | None
    assessment_updated_at: datetime | None

    source_reading_count: int | None
    reading_count: int | None
    unknown_exposure_hours: float | None

    sensor_data_sufficient: bool | None
    is_assumption_based: bool | None
    prototype_only: bool

    def is_eligible(self) -> bool:
        """Return whether this assessment passed adapter validation."""
        return self.status == ELIGIBLE


def _parse_number(value, field_name):
    """Parse finite numeric values, including Snowflake CSV strings."""

    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric.")

    if not isinstance(value, (Real, str)):
        raise ValueError(f"{field_name} must be numeric.")

    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be numeric."
        ) from exc

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite.")

    return number


def _parse_count(value, field_name):
    """Parse a non-negative integer count."""

    number = _parse_number(value, field_name)

    if number < 0 or not number.is_integer():
        raise ValueError(
            f"{field_name} must be a non-negative integer."
        )

    return int(number)


def _parse_boolean(value, field_name):
    """Accept native booleans and explicit TRUE/FALSE strings."""

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().casefold()

        if normalized == "true":
            return True

        if normalized == "false":
            return False

    raise ValueError(
        f"{field_name} must be a boolean or TRUE/FALSE string."
    )


def _parse_timestamp(value, field_name):
    """Parse a timezone-aware timestamp."""

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must be a valid ISO timestamp."
            ) from exc
    else:
        raise ValueError(
            f"{field_name} must be a valid ISO timestamp."
        )

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"{field_name} must include timezone information."
        )

    return parsed.astimezone(timezone.utc)


def _load_default_references():
    """Load canonical product names and container/product mappings."""

    if not CONTAINER_METADATA_PATH.exists():
        raise FileNotFoundError(CONTAINER_METADATA_PATH)

    if not PRODUCT_REFERENCE_PATH.exists():
        raise FileNotFoundError(PRODUCT_REFERENCE_PATH)

    with CONTAINER_METADATA_PATH.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        metadata = list(csv.DictReader(file))

    with PRODUCT_REFERENCE_PATH.open(
        encoding="utf-8-sig",
        newline="",
    ) as file:
        products = list(csv.DictReader(file))

    container_products = {}

    for row in metadata:
        container_id = row["container_id"].strip().upper()
        product_name = row["product_name"].strip()

        if container_id in container_products:
            raise ValueError(
                f"Duplicate container metadata: {container_id}"
            )

        container_products[container_id] = product_name

    canonical_products = {
        row["product_name"].strip().casefold()
        for row in products
        if row.get("product_name", "").strip()
    }

    return container_products, canonical_products


def _optional_number(record, field, reasons, *, minimum=None, maximum=None):
    """Parse and validate one required numeric field."""

    try:
        number = _parse_number(record.get(field), field)
    except ValueError:
        reasons.add(f"INVALID_{field.upper()}")
        return None

    if minimum is not None and number < minimum:
        reasons.add(f"INVALID_{field.upper()}")

    if maximum is not None and number > maximum:
        reasons.add(f"INVALID_{field.upper()}")

    return number


def _optional_count(record, field, reasons):
    try:
        return _parse_count(record.get(field), field)
    except ValueError:
        reasons.add(f"INVALID_{field.upper()}")
        return None


def _optional_boolean(record, field, reasons):
    try:
        return _parse_boolean(record.get(field), field)
    except ValueError:
        reasons.add(f"INVALID_{field.upper()}")
        return None


def _optional_timestamp(record, field, reasons):
    try:
        return _parse_timestamp(record.get(field), field)
    except ValueError:
        reasons.add(f"INVALID_{field.upper()}")
        return None


def _normalize_reference_mapping(mapping):
    """Normalize externally supplied container/product mappings."""

    normalized = {}

    for container_id, product_name in mapping.items():
        if (
            not isinstance(container_id, str)
            or not isinstance(product_name, str)
            or not container_id.strip()
            or not product_name.strip()
        ):
            raise ValueError(
                "Reference mappings require non-empty strings."
            )

        key = container_id.strip().upper()

        if key in normalized:
            raise ValueError(f"Duplicate container mapping: {key}")

        normalized[key] = product_name.strip()

    return normalized


def _incomplete_result(reason_codes, record):
    """Return an incomplete result without using unvalidated values."""

    container_id = record.get("container_id")
    product_name = record.get("product_name")

    if isinstance(container_id, str):
        container_id = container_id.strip().upper() or None
    else:
        container_id = None

    if isinstance(product_name, str):
        product_name = product_name.strip() or None
    else:
        product_name = None

    return SpoilageAssessmentResult(
        status=INSUFFICIENT,
        reason_codes=tuple(sorted(set(reason_codes))),
        container_id=container_id,
        product_name=product_name,
        remaining_shelf_life_hours=None,
        initial_shelf_life_hours=None,
        cumulative_aged_hours=None,
        risk_level=None,
        data_quality_status=None,
        latest_temperature_c=None,
        latest_humidity_pct=None,
        latitude=None,
        longitude=None,
        last_reading_at=None,
        assessment_updated_at=None,
        source_reading_count=None,
        reading_count=None,
        unknown_exposure_hours=None,
        sensor_data_sufficient=None,
        is_assumption_based=None,
        prototype_only=True,
    )


def validate_spoilage_assessment(
    record,
    *,
    evaluation_time_utc,
    max_sensor_age_hours,
    max_assessment_age_hours,
    valid_container_products=None,
    valid_products=None,
):
    """Validate one Snowflake spoilage assessment.

    Freshness limits are mandatory caller inputs. No default operational
    thresholds are assumed.

    A successful result means eligible for further prototype evaluation;
    it does not establish food safety or authorize a reroute.
    """

    if not isinstance(record, Mapping):
        raise ValueError("record must be a mapping.")

    reasons = set()

    missing_fields = [
        field
        for field in REQUIRED_FIELDS
        if (
            field not in record
            or record[field] is None
            or (
                isinstance(record[field], str)
                and not record[field].strip()
            )
        )
    ]

    if missing_fields:
        for field in missing_fields:
            reasons.add(f"MISSING_REQUIRED_FIELD:{field}")

        return _incomplete_result(reasons, record)

    # Reference data.
    if (
        valid_container_products is None
        or valid_products is None
    ):
        default_containers, default_products = (
            _load_default_references()
        )

        if valid_container_products is None:
            valid_container_products = default_containers

        if valid_products is None:
            valid_products = default_products

    container_mapping = _normalize_reference_mapping(
        valid_container_products
    )

    normalized_products = {
        product.strip().casefold()
        for product in valid_products
        if isinstance(product, str) and product.strip()
    }

    # Identification.
    container_id = record["container_id"].strip().upper()
    product_name = record["product_name"].strip()

    if container_id not in container_mapping:
        reasons.add("UNKNOWN_CONTAINER_ID")
    elif (
        container_mapping[container_id].casefold()
        != product_name.casefold()
    ):
        reasons.add("CONTAINER_PRODUCT_MISMATCH")

    if product_name.casefold() not in normalized_products:
        reasons.add("UNKNOWN_CANONICAL_PRODUCT")

    # Numeric fields.
    temperature = _optional_number(
        record, "latest_temperature_c", reasons
    )

    humidity = _optional_number(
        record,
        "latest_humidity_pct",
        reasons,
        minimum=0,
        maximum=100,
    )

    initial_life = _optional_number(
        record,
        "initial_shelf_life_hours",
        reasons,
        minimum=0,
    )

    aged_hours = _optional_number(
        record,
        "cumulative_aged_hours",
        reasons,
        minimum=0,
    )

    remaining_life = _optional_number(
        record,
        "remaining_shelf_life_hours",
        reasons,
        minimum=0,
    )

    unknown_hours = _optional_number(
        record,
        "unknown_exposure_hours",
        reasons,
        minimum=0,
    )

    latitude = _optional_number(
        record,
        "latitude",
        reasons,
        minimum=-90,
        maximum=90,
    )

    longitude = _optional_number(
        record,
        "longitude",
        reasons,
        minimum=-180,
        maximum=180,
    )

    missing_temperature_hours = _optional_number(
        record,
        "missing_temperature_interval_hours",
        reasons,
        minimum=0,
    )

    reading_count = _optional_count(
        record, "reading_count", reasons
    )

    source_reading_count = _optional_count(
        record, "source_reading_count", reasons
    )

    missing_temperature_count = _optional_count(
        record, "missing_temperature_reading_count", reasons
    )

    missing_humidity_count = _optional_count(
        record, "missing_humidity_reading_count", reasons
    )

    missing_interval_count = _optional_count(
        record, "missing_temperature_interval_count", reasons
    )

    # Assessment classification.
    risk_level = record["risk_level"].strip().upper()

    if risk_level not in ALLOWED_RISK_LEVELS:
        reasons.add("INVALID_RISK_LEVEL")

    data_quality_status = (
        record["data_quality_status"].strip().upper()
    )

    if data_quality_status != "OBSERVED":
        reasons.add("DATA_QUALITY_NOT_OBSERVED")

    # Boolean eligibility fields.
    sensor_sufficient = _optional_boolean(
        record,
        "sensor_data_sufficient",
        reasons,
    )

    assumption_based = _optional_boolean(
        record,
        "is_assumption_based",
        reasons,
    )

    if sensor_sufficient is False:
        reasons.add("SENSOR_DATA_NOT_SUFFICIENT")

    if sensor_sufficient is None:
        reasons.add("SENSOR_DATA_SUFFICIENCY_UNKNOWN")

    # Shelf-life consistency.
    if initial_life is not None and initial_life <= 0:
        reasons.add("INVALID_INITIAL_SHELF_LIFE")

    if (
        initial_life is not None
        and remaining_life is not None
        and remaining_life > initial_life
    ):
        reasons.add("REMAINING_SHELF_LIFE_EXCEEDS_INITIAL")

    # Readings and missing-data checks.
    if reading_count is not None and reading_count < 2:
        reasons.add("INSUFFICIENT_READING_COUNT")

    if source_reading_count is not None and source_reading_count < 2:
        reasons.add("INSUFFICIENT_SOURCE_READING_COUNT")

    if (
        reading_count is not None
        and source_reading_count is not None
        and source_reading_count < reading_count
    ):
        reasons.add("SOURCE_READING_COUNT_BELOW_READING_COUNT")

    if missing_temperature_count is not None and missing_temperature_count > 0:
        reasons.add("MISSING_TEMPERATURE_READINGS")

    if missing_humidity_count is not None and missing_humidity_count > 0:
        reasons.add("MISSING_HUMIDITY_READINGS")

    if missing_interval_count is not None and missing_interval_count > 0:
        reasons.add("MISSING_TEMPERATURE_INTERVALS")

    if (
        missing_temperature_hours is not None
        and missing_temperature_hours > 0
    ):
        reasons.add("MISSING_TEMPERATURE_INTERVAL_HOURS")

    if unknown_hours is not None and unknown_hours > 0:
        reasons.add("UNKNOWN_SENSOR_EXPOSURE")

    if data_quality_status == "DEV_PLACEHOLDER":
        reasons.add("DEVELOPMENT_PLACEHOLDER")

    # Parse timestamps.
    last_reading_at = _optional_timestamp(
        record, "last_reading_at", reasons
    )

    assessment_updated_at = _optional_timestamp(
        record, "assessment_updated_at", reasons
    )

    if isinstance(evaluation_time_utc, datetime):
        evaluation_time = evaluation_time_utc
    else:
        evaluation_time = None

    if evaluation_time is None:
        reasons.add("INVALID_EVALUATION_TIME")
    elif (
        evaluation_time.tzinfo is None
        or evaluation_time.utcoffset() is None
    ):
        reasons.add("EVALUATION_TIME_MUST_BE_TIMEZONE_AWARE")
    else:
        evaluation_time = evaluation_time.astimezone(timezone.utc)

    if (
        last_reading_at is not None
        and assessment_updated_at is not None
        and assessment_updated_at < last_reading_at
    ):
        reasons.add("ASSESSMENT_PRECEDES_LATEST_READING")

    # Explicit freshness policies.
    thresholds = {}

    for field, value in (
        ("max_sensor_age_hours", max_sensor_age_hours),
        ("max_assessment_age_hours", max_assessment_age_hours),
    ):
        try:
            threshold = _parse_number(value, field)
            if threshold < 0:
                raise ValueError()
            thresholds[field] = threshold
        except ValueError:
            reasons.add(f"INVALID_FRESHNESS_POLICY:{field}")

    if evaluation_time is not None:
        if (
            last_reading_at is not None
            and last_reading_at > evaluation_time
        ):
            reasons.add("FUTURE_SENSOR_READING")

        elif (
            last_reading_at is not None
            and "max_sensor_age_hours" in thresholds
        ):
            sensor_age = (
                evaluation_time - last_reading_at
            ).total_seconds() / 3600

            if sensor_age > thresholds["max_sensor_age_hours"]:
                reasons.add("STALE_SENSOR_READING")

        if (
            assessment_updated_at is not None
            and assessment_updated_at > evaluation_time
        ):
            reasons.add("FUTURE_ASSESSMENT_TIMESTAMP")

        elif (
            assessment_updated_at is not None
            and "max_assessment_age_hours" in thresholds
        ):
            assessment_age = (
                evaluation_time - assessment_updated_at
            ).total_seconds() / 3600

            if assessment_age > thresholds["max_assessment_age_hours"]:
                reasons.add("STALE_ASSESSMENT")

    return SpoilageAssessmentResult(
        status=INSUFFICIENT if reasons else ELIGIBLE,
        reason_codes=tuple(sorted(reasons)),
        container_id=container_id,
        product_name=product_name,
        remaining_shelf_life_hours=remaining_life,
        initial_shelf_life_hours=initial_life,
        cumulative_aged_hours=aged_hours,
        risk_level=risk_level,
        data_quality_status=data_quality_status,
        latest_temperature_c=temperature,
        latest_humidity_pct=humidity,
        latitude=latitude,
        longitude=longitude,
        last_reading_at=last_reading_at,
        assessment_updated_at=assessment_updated_at,
        source_reading_count=source_reading_count,
        reading_count=reading_count,
        unknown_exposure_hours=unknown_hours,
        sensor_data_sufficient=sensor_sufficient,
        is_assumption_based=assumption_based,
        prototype_only=bool(assumption_based),
    )
