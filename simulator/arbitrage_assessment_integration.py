"""Connect validated spoilage assessments to the AtmoSync arbitrage engine."""

from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from simulator.arbitrage_engine import (
    ArbitrageDecision,
    evaluate_reroute_option,
)
from simulator.spoilage_assessment_adapter import (
    ELIGIBLE,
    SpoilageAssessmentResult,
)


@dataclass(frozen=True)
class IntegratedArbitrageResult:
    """Eligibility and optional prototype arbitrage evaluation."""

    status: str
    reason: str
    reason_codes: tuple[str, ...]
    container_id: str | None
    product_name: str | None
    prototype_only: bool
    decision: ArbitrageDecision | None


def _blocked_result(assessment, reason_codes):
    """Return a blocked result without running arbitrage calculations."""

    return IntegratedArbitrageResult(
        status="INSUFFICIENT_DATA",
        reason=(
            "Arbitrage evaluation was blocked because the spoilage "
            "assessment was not eligible or did not match the shipment."
        ),
        reason_codes=tuple(sorted(set(reason_codes))),
        container_id=assessment.container_id,
        product_name=assessment.product_name,
        prototype_only=True,
        decision=None,
    )


def evaluate_with_spoilage_assessment(
    *,
    shipment: Mapping,
    assessment: SpoilageAssessmentResult,
    planned_route: Mapping,
    alternative_route: Mapping,
    price_records: Iterable[Mapping],
    as_of_date: str,
) -> IntegratedArbitrageResult:
    """Run arbitrage evaluation only after spoilage validation succeeds.

    This function does not validate or modify Snowflake records itself.
    Call validate_spoilage_assessment() before invoking this integration.

    A returned REROUTE_RECOMMENDED decision remains a prototype result,
    not an operational routing instruction.
    """

    if not isinstance(assessment, SpoilageAssessmentResult):
        raise ValueError(
            "assessment must be a SpoilageAssessmentResult."
        )

    if not isinstance(shipment, Mapping):
        raise ValueError("shipment must be a mapping.")

    reason_codes = list(assessment.reason_codes)

    if assessment.status != ELIGIBLE or not assessment.is_eligible():
        if not reason_codes:
            reason_codes.append("ASSESSMENT_NOT_ELIGIBLE")

        return _blocked_result(assessment, reason_codes)

    shipment_container = shipment.get("container_id")
    shipment_product = shipment.get("product_name")

    if (
        not isinstance(shipment_container, str)
        or not shipment_container.strip()
    ):
        reason_codes.append("SHIPMENT_CONTAINER_ID_MISSING")

    elif (
        shipment_container.strip().upper()
        != assessment.container_id
    ):
        reason_codes.append("ASSESSMENT_SHIPMENT_CONTAINER_MISMATCH")

    if (
        not isinstance(shipment_product, str)
        or not shipment_product.strip()
    ):
        reason_codes.append("SHIPMENT_PRODUCT_NAME_MISSING")

    elif (
        shipment_product.strip().casefold()
        != assessment.product_name.casefold()
    ):
        reason_codes.append("ASSESSMENT_SHIPMENT_PRODUCT_MISMATCH")

    if assessment.sensor_data_sufficient is not True:
        reason_codes.append("SENSOR_DATA_NOT_SUFFICIENT")

    if assessment.remaining_shelf_life_hours is None:
        reason_codes.append("REMAINING_SHELF_LIFE_UNAVAILABLE")

    if assessment.initial_shelf_life_hours is None:
        reason_codes.append("INITIAL_SHELF_LIFE_UNAVAILABLE")

    if assessment.risk_level not in {
        "NORMAL",
        "WARNING",
        "HIGH_RISK",
    }:
        reason_codes.append("INVALID_ASSESSMENT_RISK_LEVEL")

    if reason_codes:
        return _blocked_result(assessment, reason_codes)

    decision = evaluate_reroute_option(
        shipment=shipment,
        planned_route=planned_route,
        alternative_route=alternative_route,
        price_records=price_records,
        as_of_date=as_of_date,
        remaining_shelf_life_hours=(
            assessment.remaining_shelf_life_hours
        ),
        initial_shelf_life_hours=(
            assessment.initial_shelf_life_hours
        ),
        expected_aging_factor=1.0,
        risk_level=assessment.risk_level,
        sensor_data_sufficient=True,
    )

    # Preserve an insufficient-data result returned by the
    # underlying arbitrage engine, including missing market prices.
    if decision.status == "INSUFFICIENT_DATA":
        return IntegratedArbitrageResult(
            status="INSUFFICIENT_DATA",
            reason=decision.reason,
            reason_codes=("ARBITRAGE_INPUTS_INSUFFICIENT",),
            container_id=assessment.container_id,
            product_name=assessment.product_name,
            prototype_only=True,
            decision=decision,
        )

    return IntegratedArbitrageResult(
        status="EVALUATED_PROTOTYPE",
        reason=(
            "Spoilage assessment passed the adapter checks and the "
            "prototype arbitrage calculation was completed."
        ),
        reason_codes=(),
        container_id=assessment.container_id,
        product_name=assessment.product_name,
        prototype_only=True,
        decision=decision,
    )
