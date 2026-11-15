# AtmoSync – Superset Dashboard Implementation Notes

**Owner:** Ankush Pal
**Role:** Apache Superset, BI Dashboard & Alerts Developer
**Dashboard:** AtmoSync Container Monitoring Dashboard

## 1. Purpose

This document records the dashboard components configured in Apache Superset.
The dashboard is intended to support container telemetry monitoring, data-quality
review and commodity-market analysis.

## 2. Existing Dashboard Components

### KPI cards
- Total Monitored Containers
- Average Container Temperature
- Average Container Humidity
- Average Container Vibration
- Container Data Quality (%)
- Data Freshness (Hours)

### Time-series and analytical charts
- Container Temperature by Time
- Container Humidity by Time
- Container Vibration by Time
- Commodity Prices by Market
- Container Health Overview

### Timestamp and telemetry-availability charts added on 14 November
- Observed Timestamp Gap Distribution
- Maximum Inter-Event Gap by Container
- Long Timestamp Gaps by Container
- Telemetry Sampling Consistency (%)
- Telemetry Records by Container

## 3. Dashboard Filters

- Container ID
- Time Range

The Container ID and Time Range filters were configured with scoped
application to the relevant container health and time-series visualizations.
Filter behaviour was checked using a specific container selection.

## 4. Data Source Notes

The telemetry staging source inspected for timestamp-gap analysis was:

`STAGING.STG_CONTAINER_TELEMETRY`

Fields used or inspected include:
- EVENT_TS
- INGESTED_AT
- CONTAINER_ID
- EVENT_ID
- TEMPERATURE_C
- HUMIDITY_PCT
- VIBRATION_G
- LATITUDE
- LONGITUDE
- SOURCE_TYPE

The inspected table did not contain a SENSOR_ID field. Therefore, the
timestamp-gap indicators are calculated at container level, not sensor level.

## 5. Provisional Sampling-Consistency Calculation

The 14 November prototype classified an observed interval as consistent
when its duration was between 5 and 10 seconds, inclusive.

The provisional KPI was calculated as:

`Intervals between 5 and 10 seconds / All observed intervals * 100`

The observed result was 90%.

**This is not an approved data-completeness measure.** The assumed interval
range requires team confirmation. Simulator downtime, observation-window
selection and timestamp tolerance must be considered before finalizing
a production metric.

## 6. Alert Prototypes

Two alert configurations were prepared in Superset:

1. Container Data Quality Alert – configured to check the data-quality
   percentage against a 100% threshold.
2. AtmoSync Data Freshness Alert – configured to check whether the age of
   the latest ingested record exceeds 24 hours.

These are prototype configurations. Successful scheduled execution and
email delivery have not yet been verified. Thresholds and notification
behaviour remain subject to team review.

## 7. Known Limitations and Pending Validation

- Confirm display units and chart labels against the approved data dictionary.
- Verify the source unit and interpretation of vibration measurements.
- Confirm timestamp display timezone.
- Confirm the expected telemetry cadence and acceptable sampling tolerance.
- Agree on simulator downtime handling.
- Finalize the data-completeness calculation.
- Verify alert execution and notification delivery.
- Export or otherwise preserve dashboard configuration as a repository
  artifact where the project workflow supports it.

## 8. Important Interpretation Rules

- Do not treat a container identifier as a sensor identifier.
- Do not treat timestamp gaps as confirmed missing readings without an
  approved expected-cadence and downtime policy.
- Do not silently clip or delete implausible measurements.
- Keep household refrigerator reference data separate from shipping-container
  telemetry.
- Clearly label synthetic or provisional data and calculations.
