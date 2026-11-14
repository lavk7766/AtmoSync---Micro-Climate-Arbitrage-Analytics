# AtmoSync Missing-Data Handling Policy

**Project:** AtmoSync – Micro-Climate Arbitrage Analytics  
**Prepared by:** Lav Kumar  
**Date:** 14 November 2026  
**Status:** Proposed for team review and approval

## 1. Purpose

This policy defines how missing temperature, humidity and timestamp data must be identified, measured, documented and handled before the data is used in analytics, dbt models or dashboards.

The objective is to preserve data integrity and prevent unsupported assumptions during cleaning.

## 2. Scope

This policy applies to:

- Cold-storage sensor Raw.zip files.
- Cold-storage sensor Preprocessed.zip files.
- Sensor overview.csv.
- Household cold-chain reference data, which must remain separate from shipping-container telemetry.

Raw and preprocessed sensor datasets must be assessed independently before comparison.

## 3. Missing-value identification

For every sensor file, identify and record:

- Total number of records.
- Missing temperature values.
- Missing humidity values.
- Missing values in other required fields.
- Duplicate timestamps.
- Invalid or unparseable timestamps.
- Missing time intervals between consecutive observations.

Do not assume that a preprocessed file contains no missing values.

## 4. Missing temperature and humidity

- Preserve missing measurements as null in the cleaned dataset unless a documented transformation is approved.
- Do not replace missing values with zero, the mean, median or an arbitrary constant.
- Do not automatically delete a complete row because temperature or humidity is missing.
- Keep valid measurements from other fields where appropriate.
- Report missing temperature and humidity separately.
- Compare missing-value counts between raw and preprocessed versions.

## 5. Timestamp gaps

- Parse dates and times consistently.
- Sort records chronologically for gap analysis.
- Calculate time differences between consecutive observations.
- Identify missing intervals separately from null temperature or humidity readings.
- Investigate whether gaps are caused by missing records, irregular sampling or timestamp parsing problems.
- Do not generate artificial sensor readings to fill missing intervals.

The expected sampling interval must be verified from each file rather than assumed to be identical across all sensors.

## 6. Rules for interpolation and imputation

No automatic imputation is permitted by default.

Interpolation may only be considered when:

1. The analysis has a clear reason to use it.
2. The maximum permitted gap is explicitly defined and justified.
3. The method is documented.
4. Original observations remain unchanged.
5. Imputed values are distinguishable from observed values through a quality flag.
6. The responsible data engineer and project coordinator review the decision.

Long missing intervals must not be filled with invented values.

## 7. Required quality measurements

For every sensor and measurement field, record:

| Metric | Required information |
|---|---|
| Original records | Number of records before cleaning |
| Original missing values | Missing count before cleaning |
| Original missing percentage | Missing count / original records × 100 |
| Removed records | Count and documented reason |
| Remaining records | Number of records after cleaning |
| Remaining missing values | Missing count after cleaning |
| Imputed values | Count, method and reason, if applicable |
| Timestamp gaps | Number and duration of identified gaps |

All before-and-after counts must be retained in the cleaning report.

## 8. Raw-data preservation

- Never overwrite original raw files.
- Store temporary transformations in data/interim/.
- Store validated outputs in data/processed/.
- Maintain a cleaning log with source file, transformation, date and reason.
- Keep raw and preprocessed dataset results separate.
- Document any discrepancy between overview.csv and independently calculated statistics.

## 9. Responsibilities

**Lav Kumar – Project Coordinator**
- Coordinate policy review and approval.
- Maintain the decision log.
- Ensure missing-data rules are documented.
- Review quality reports and unresolved issues.

**Manash Mandal – Snowflake, dbt and SQL Data Engineer**
- Calculate missing-value counts and percentages.
- Compare raw and preprocessed sensor files.
- Investigate missing values and timestamp gaps.
- Implement approved cleaning rules.
- Preserve before-and-after quality evidence.

**Aditya Singh Bisht – IoT Simulator and Kafka Developer**
- Review timestamp and event-generation behaviour.
- Check whether simulator sampling intervals are consistent.
- Avoid generating artificial historical sensor readings to conceal source-data gaps.

**ANKUSH PAL – Dashboard and Alerts Developer**
- Define data-completeness indicators.
- Display missing measurements and sensor availability clearly.
- Avoid presenting incomplete measurements as verified observations.

## 10. Approval and change control

This document is a proposed policy as of 14 November 2026.

The policy becomes approved only after review by the project coordinator and data engineer, with team agreement recorded in the project decision log.

Any change to missing-value handling, interpolation or deletion rules must be documented with its reason and impact.

## 11. Expected deliverables

- Sensor-wise missing-value report.
- Raw versus preprocessed comparison.
- Timestamp-gap report.
- Documented cleaning decisions.
- Before-and-after quality measurements.
- Team approval record.

## 12. Current status

**Policy preparation:** Completed  
**Manash review:** Pending  
**Team approval:** Pending  
**Implementation evidence:** Pending

No dataset-cleaning result is claimed by this policy itself.
