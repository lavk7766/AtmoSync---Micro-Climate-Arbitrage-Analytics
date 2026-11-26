from datetime import datetime, timezone, timedelta

import pytest

from simulator.spoilage_assessment_adapter import (
    ELIGIBLE,
    INSUFFICIENT,
    REQUIRED_FIELDS,
    validate_spoilage_assessment,
)


EVALUATION_TIME = datetime(
    2026, 11, 26, 10, 0, 0, tzinfo=timezone.utc
)

REFERENCE_CONTAINERS = {
    "CONT001": "Apple",
    "CONT002": "Banana",
}

REFERENCE_PRODUCTS = {
    "apple",
    "banana",
}


def valid_assessment():
    return {
        "container_id": "CONT001",
        "product_name": "Apple",
        "latest_temperature_c": 3.0,
        "latest_humidity_pct": 92.0,
        "initial_shelf_life_hours": 720.0,
        "cumulative_aged_hours": 100.0,
        "remaining_shelf_life_hours": 620.0,
        "risk_level": "NORMAL",
        "unknown_exposure_hours": 0.0,
        "reading_count": 10,
        "data_quality_status": "OBSERVED",
        "latitude": 28.61393,
        "longitude": 77.20877,
        "last_reading_at": "2026-11-26T09:50:00Z",
        "is_assumption_based": True,
        "source_reading_count": 10,
        "missing_temperature_reading_count": 0,
        "missing_humidity_reading_count": 0,
        "missing_temperature_interval_count": 0,
        "missing_temperature_interval_hours": 0.0,
        "sensor_data_sufficient": True,
        "assessment_updated_at": "2026-11-26T09:55:00Z",
    }


def validate(record=None, **overrides):
    data = valid_assessment() if record is None else dict(record)
    data.update(overrides)

    return validate_spoilage_assessment(
        data,
        evaluation_time_utc=EVALUATION_TIME,
        max_sensor_age_hours=1.0,
        max_assessment_age_hours=2.0,
        valid_container_products=REFERENCE_CONTAINERS,
        valid_products=REFERENCE_PRODUCTS,
    )


def test_complete_fresh_assessment_is_eligible():
    result = validate()

    assert result.status == ELIGIBLE
    assert result.reason_codes == ()
    assert result.is_eligible()


def test_valid_assessment_normalizes_container_and_product():
    result = validate({
        **valid_assessment(),
        "container_id": "cont001",
        "product_name": "apple",
    })

    assert result.container_id == "CONT001"
    assert result.product_name == "apple"
    assert result.status == ELIGIBLE


def test_assumption_based_assessment_remains_prototype_only():
    result = validate(is_assumption_based="TRUE")

    assert result.status == ELIGIBLE
    assert result.prototype_only is True


def test_numeric_strings_from_snowflake_csv_are_accepted():
    record = valid_assessment()

    for field in (
        "latest_temperature_c",
        "latest_humidity_pct",
        "initial_shelf_life_hours",
        "cumulative_aged_hours",
        "remaining_shelf_life_hours",
        "unknown_exposure_hours",
        "latitude",
        "longitude",
        "reading_count",
        "source_reading_count",
    ):
        record[field] = str(record[field])

    result = validate(record)

    assert result.status == ELIGIBLE
    assert result.remaining_shelf_life_hours == 620.0


@pytest.mark.parametrize(
    "field",
    [
        "source_reading_count",
        "missing_temperature_reading_count",
        "missing_humidity_reading_count",
        "missing_temperature_interval_count",
        "missing_temperature_interval_hours",
        "sensor_data_sufficient",
        "assessment_updated_at",
    ],
)
def test_missing_proposed_contract_fields_are_rejected(field):
    record = valid_assessment()
    del record[field]

    result = validate(record)

    assert result.status == INSUFFICIENT
    assert f"MISSING_REQUIRED_FIELD:{field}" in result.reason_codes


@pytest.mark.parametrize(
    "field",
    [
        "missing_temperature_reading_count",
        "missing_humidity_reading_count",
    ],
)
def test_missing_sensor_readings_block_eligibility(field):
    result = validate(**{field: 1})

    assert result.status == INSUFFICIENT


def test_missing_temperature_intervals_block_eligibility():
    result = validate(missing_temperature_interval_count=1)

    assert "MISSING_TEMPERATURE_INTERVALS" in result.reason_codes


def test_missing_temperature_interval_hours_block_eligibility():
    result = validate(missing_temperature_interval_hours=0.005)

    assert "MISSING_TEMPERATURE_INTERVAL_HOURS" in result.reason_codes


def test_unknown_exposure_blocks_eligibility():
    result = validate(unknown_exposure_hours=0.1)

    assert "UNKNOWN_SENSOR_EXPOSURE" in result.reason_codes


@pytest.mark.parametrize(
    "status",
    [
        "INCOMPLETE_COVERAGE",
        "INSUFFICIENT_READINGS",
        "DEV_PLACEHOLDER",
        "UNKNOWN",
    ],
)
def test_non_observed_data_quality_status_is_rejected(status):
    result = validate(data_quality_status=status)

    assert result.status == INSUFFICIENT
    assert "DATA_QUALITY_NOT_OBSERVED" in result.reason_codes


def test_false_sensor_sufficiency_blocks_eligibility():
    result = validate(sensor_data_sufficient=False)

    assert "SENSOR_DATA_NOT_SUFFICIENT" in result.reason_codes


def test_stale_sensor_reading_is_rejected():
    result = validate(
        last_reading_at="2026-11-26T08:30:00Z"
    )

    assert "STALE_SENSOR_READING" in result.reason_codes


def test_stale_assessment_is_rejected():
    result = validate(
        assessment_updated_at="2026-11-26T07:00:00Z"
    )

    assert "STALE_ASSESSMENT" in result.reason_codes


def test_future_sensor_reading_is_rejected():
    result = validate(
        last_reading_at="2026-11-26T10:10:00Z",
        assessment_updated_at="2026-11-26T10:15:00Z",
    )

    assert "FUTURE_SENSOR_READING" in result.reason_codes


def test_future_assessment_timestamp_is_rejected():
    result = validate(
        assessment_updated_at="2026-11-26T10:10:00Z"
    )

    assert "FUTURE_ASSESSMENT_TIMESTAMP" in result.reason_codes


def test_assessment_cannot_precede_latest_reading():
    result = validate(
        last_reading_at="2026-11-26T09:58:00Z",
        assessment_updated_at="2026-11-26T09:55:00Z",
    )

    assert "ASSESSMENT_PRECEDES_LATEST_READING" in result.reason_codes


def test_missing_freshness_policy_blocks_eligibility():
    record = valid_assessment()

    result = validate_spoilage_assessment(
        record,
        evaluation_time_utc=EVALUATION_TIME,
        max_sensor_age_hours=None,
        max_assessment_age_hours=2.0,
        valid_container_products=REFERENCE_CONTAINERS,
        valid_products=REFERENCE_PRODUCTS,
    )

    assert "INVALID_FRESHNESS_POLICY:max_sensor_age_hours" in (
        result.reason_codes
    )


def test_invalid_freshness_limit_is_rejected():
    record = valid_assessment()

    result = validate_spoilage_assessment(
        record,
        evaluation_time_utc=EVALUATION_TIME,
        max_sensor_age_hours=-1,
        max_assessment_age_hours=2,
        valid_container_products=REFERENCE_CONTAINERS,
        valid_products=REFERENCE_PRODUCTS,
    )

    assert result.status == INSUFFICIENT


def test_container_product_mismatch_is_rejected():
    result = validate(product_name="Banana")

    assert "CONTAINER_PRODUCT_MISMATCH" in result.reason_codes


def test_unknown_canonical_product_is_rejected():
    result = validate(product_name="Tomatoes")

    assert "UNKNOWN_CANONICAL_PRODUCT" in result.reason_codes


def test_unknown_container_is_rejected():
    result = validate(container_id="CONT999")

    assert "UNKNOWN_CONTAINER_ID" in result.reason_codes


def test_invalid_humidity_is_rejected():
    result = validate(latest_humidity_pct=105)

    assert "INVALID_LATEST_HUMIDITY_PCT" in result.reason_codes


@pytest.mark.parametrize(
    "field,value",
    [
        ("latitude", 95),
        ("latitude", float("nan")),
        ("longitude", 190),
    ],
)
def test_invalid_coordinates_are_rejected(field, value):
    result = validate(**{field: value})

    assert result.status == INSUFFICIENT


def test_remaining_shelf_life_cannot_exceed_initial():
    result = validate(remaining_shelf_life_hours=800)

    assert "REMAINING_SHELF_LIFE_EXCEEDS_INITIAL" in (
        result.reason_codes
    )


def test_negative_remaining_shelf_life_is_rejected():
    result = validate(remaining_shelf_life_hours=-1)

    assert "INVALID_REMAINING_SHELF_LIFE_HOURS" in (
        result.reason_codes
    )


def test_invalid_risk_level_is_rejected():
    result = validate(risk_level="CRITICAL_UNKNOWN")

    assert "INVALID_RISK_LEVEL" in result.reason_codes


def test_insufficient_reading_count_is_rejected():
    result = validate(reading_count=1)

    assert "INSUFFICIENT_READING_COUNT" in result.reason_codes


def test_source_count_cannot_be_lower_than_surviving_reading_count():
    result = validate(
        source_reading_count=5,
        reading_count=10,
    )

    assert "SOURCE_READING_COUNT_BELOW_READING_COUNT" in (
        result.reason_codes
    )


def test_current_manash_mart_shape_is_incomplete_for_new_contract():
    record = valid_assessment()

    for field in (
        "source_reading_count",
        "missing_temperature_reading_count",
        "missing_humidity_reading_count",
        "missing_temperature_interval_count",
        "missing_temperature_interval_hours",
        "sensor_data_sufficient",
        "assessment_updated_at",
    ):
        record.pop(field)

    result = validate(record)

    assert result.status == INSUFFICIENT
    assert len(result.reason_codes) == 7


def test_assessment_timestamps_are_normalized_to_utc():
    result = validate(
        last_reading_at="2026-11-26T15:20:00+05:30",
        assessment_updated_at="2026-11-26T15:25:00+05:30",
    )

    assert result.status == ELIGIBLE
    assert result.last_reading_at.utcoffset().total_seconds() == 0
    assert result.assessment_updated_at.utcoffset().total_seconds() == 0


def test_naive_timestamps_are_rejected():
    result = validate(
        last_reading_at="2026-11-26T09:50:00",
    )

    assert result.status == INSUFFICIENT
    assert "INVALID_LAST_READING_AT" in result.reason_codes
