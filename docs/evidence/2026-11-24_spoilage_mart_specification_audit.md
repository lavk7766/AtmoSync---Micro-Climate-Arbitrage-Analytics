# Spoilage Mart Technical Specification Audit

Date: 24 November 2026
Reviewer: Aditya
Reviewed branch: origin/manash
Reviewed commit: 200d4c8
Scope: Spoilage-risk mart, staging models and selected dbt tests

## 1. Purpose

Compare the current dbt spoilage-risk implementation with the
proposed spoilage and arbitrage requirements in
docs/design/spoilage_arbitrage_plan.md.

This is a technical review. Prototype formulas, alert thresholds,
sensor tolerances and data-quality eligibility rules remain subject
to project coordinator approval.

## 2. Confirmed implementation observations

### Finding 1: Missing temperature readings can be treated as observed exposure

The mart filters out rows with null temperature before calculating
event intervals.

Consequently, a missing reading between two valid readings can be
removed before interval calculation. For example:

- 10:00:00: valid temperature
- 10:00:05: missing temperature
- 10:00:10: valid temperature

After filtering, the mart may calculate a 10-second interval between
the two surviving readings. Since this is within the 1-15 second
observed interval range, the complete interval is counted as observed
exposure.

This conflicts with the draft requirement that intervals involving
missing temperature readings must be excluded from observed aging
and reported as unknown exposure.

Suggested follow-up:
Preserve reading continuity or explicitly identify missing-temperature
intervals before filtering. Add a test for a missing reading within
an otherwise valid 15-second interval.

Priority: High

### Finding 2: Temperature and humidity excursion alerts are absent

The current mart outputs latest temperature and humidity, but does
not calculate:

- temperature_excursion_minutes
- humidity_excursion_minutes
- temperature_alert
- humidity_alert

The current humidity validation test checks product-reference
humidity bounds. It does not validate telemetry excursion durations.

The draft specification proposes separate temperature and humidity
duration thresholds and alert classifications.

Suggested follow-up:
After coordinator approval, implement excursion-duration tracking
and corresponding tests. Preserve temperature and humidity exposure
as separate indicators.

Priority: High

### Finding 3: Data-quality status does not identify all missing readings

The current data-quality classification checks:

- Development placeholder status
- Fewer than two surviving readings
- Unknown exposure from intervals above 15 seconds
- Otherwise OBSERVED

Because null-temperature readings are filtered before aggregation,
they are not independently counted or represented in the final
data-quality status. Missing humidity values are also not explicitly
identified by the current classification.

A container may therefore receive OBSERVED status despite incomplete
sensor fields.

Suggested follow-up:
Retain missing-field indicators and distinguish incomplete sensor
coverage from observed exposure. Define which statuses are eligible
for downstream spoilage and arbitrage recommendations.

Priority: High

### Finding 4: No arbitrage mart exists in the inspected dbt tree

The inspected origin/manash dbt file listing includes
mart_spoilage_risk.sql but does not include mart_arbitrage.sql.

The proposed arbitrage calculation therefore remains a separate
implementation dependency.

Required inputs identified in the design include:

- Remaining shelf life and risk classification
- Container coordinates and quantity
- Planned destination
- Candidate market coordinates
- Product prices
- Transport speed and cost

Candidate-market data and operational transport costs were also
identified as missing in the design document.

Suggested follow-up:
Confirm the approved business assumptions and required input
tables before implementing the arbitrage mart.

Priority: High

## 3. Data coverage and matching observations

### Finding 5: Inner joins can exclude containers from the mart

The spoilage mart joins telemetry to container metadata and product
references using inner joins.

Telemetry without matching metadata, or metadata with an unmatched
product reference, will not appear in the final spoilage mart.

The existing product-reference singular test helps identify
unmatched product names, but a successful uniqueness test alone
does not prove that every expected container is represented.

Suggested follow-up:
Add a container-coverage reconciliation check between expected
metadata containers and the spoilage mart output.

Priority: Medium

### Finding 6: Product spelling requires canonical agreement

Both metadata and product-reference staging models use lowercase
and trim product names. This handles differences in capitalization
and surrounding spaces.

It does not resolve semantic aliases such as:

- Tomatoes
- Tomato

The existing product-reference test performs an exact normalized
name match and should fail for an unmatched spelling. The mart's
inner join would exclude that unmatched product.

Suggested follow-up:
Agree on canonical product names and correct source reference or
metadata values. Avoid automatic plural conversion without an
approved mapping.

Priority: Medium

## 4. Functionality already implemented

The current mart includes:

- Latest container metadata selection
- Product-specific temperature reference joins
- Chronological telemetry ordering
- Temperature-based aging factor
- Effective aging accumulation for accepted intervals
- Unknown exposure for gaps above 15 seconds
- Remaining shelf-life hours and percentage
- NORMAL, WARNING and HIGH_RISK classification
- Development placeholder identification
- Latest sensor readings and coordinates
- Assumption-based indicator

Existing validation includes product-reference matching,
humidity and temperature reference bounds, shelf-life bounds,
risk bounds, risk classification and unique-container checks.

## 5. Approval dependencies

The following proposed rules remain subject to coordinator approval:

- Temperature aging factor
- Risk classification thresholds
- Temperature and humidity alert durations
- Sensor tolerance for zero-width temperature ranges
- Maximum valid reading interval
- Data-quality eligibility for downstream recommendations
- Accelerated simulation assumptions
- Candidate market and transport assumptions

These findings should not be interpreted as approval of the
prototype assumptions.

## 6. Suggested ownership and next actions

Aditya:
- Provide missing-reading and timestamp-gap simulator fixtures.
- Add independent validation tests where interfaces are agreed.
- Reconcile expected container coverage where source data is available.

Manash:
- Review missing-temperature interval handling.
- Confirm alert implementation scope.
- Confirm dbt output and data-quality eligibility behavior.
- Continue arbitrage mart implementation after approvals.

Lav:
- Approve or revise prototype formulas and thresholds.
- Confirm product naming and canonical references.
- Confirm data-quality eligibility and market assumptions.

Ankush:
- Ensure incomplete or provisional data is not presented as a
  confirmed operational recommendation.
- Reconcile dashboard counts with mart output and source containers.

## 7. Review limitation

This audit is based on source inspection of origin/manash commit
200d4c8 and the selected staging models, mart SQL and tests.

It does not establish whether the latest dbt models execute
successfully in Snowflake or whether live source data currently
exhibits every identified edge case.

No files on Manash's branch were modified.
