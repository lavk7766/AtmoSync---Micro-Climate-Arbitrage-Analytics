# Review of the Missing-Data Handling Policy

**Reviewer:** Manash Mandal (Snowflake, dbt and SQL)
**Policy reviewed:** docs/dataset/missing_data_policy.md (proposed by Lav Kumar, 14 November 2026)
**Date:** 14 November 2026
**Recommendation:** Approve with the changes below.

## 1. Agreed as written
- Missing temperature and humidity stay NULL: no zero, mean, median or constant replacement (section 4).
- No automatic deletion of rows because one measurement is missing (section 4).
- No imputation by default; interpolation only with a stated reason, a maximum gap, a documented method and a quality flag (section 6).
- Raw files are never overwritten; raw and preprocessed results are kept separate (section 8).
- Before and after counts per sensor and field (section 7).
These match what the pipeline already does: no values are filled in staging, and the sensor models keep NULLs.

## 2. Suggested changes
1. **Define the two kinds of missing data explicitly.** (a) A NULL value in an existing row. (b) A missing time slot: no row at all for an expected timestamp. The preprocessed files turn some missing slots into rows with empty values, so a count of NULLs alone mixes the two. Proposal: every report states null values and missing slots as separate numbers. The data shows why: the raw files contain 0 NULL values but 73,442 missing slots (SENSOR01: 966, SENSOR03: 72,476), while the preprocessed files contain 328,893 NULL values per field and no missing slots. All 328,893 empty preprocessed rows have no raw counterpart (grid padding), and none has values.
2. **Add a row-origin flag for processed data.** Proposed values: observed, null_value, grid_padding. A row that exists only in the preprocessed file and has no raw counterpart is grid_padding. The comparison in docs/dataset/sensor_missing_values_report.md counts these rows.
3. **Gap size classes for reporting** (for Ankush's completeness indicators): up to 1 minute, up to 1 hour, longer than 1 hour. These are reporting classes only; no gap is filled. The class limits are a proposal.
4. **Duplicates need their own rule.** Section 4 forbids deleting rows because of missing values, but section 7 lists removed records. Proposal: a duplicate sensor and timestamp pair keeps the most recently loaded row, and the removed count is reported. The current dbt model stg_sensor_readings already does this, and the raw load contained 0 duplicates.
5. **Interpolation:** keep it off for the staging and mart models. If an analysis later needs it, the maximum gap is set at that time, with a quality flag column.
6. **ELT equivalent of section 8.** The policy names data/interim, data/processed and a cleaning log. In this pipeline the raw layer is the Snowflake RAW schema, cleaning happens in dbt models (STAGING, INTERMEDIATE, MARTS), and the cleaning log is docs/dataset/cleaning_log.md plus the model SQL. Please confirm this counts, or tell me if processed CSV files are also required.
7. **overview.csv discrepancies (section 8):** the Length values in overview.csv differ from the raw record counts for all 9 sensors (573 rows in total), but they equal the number of non-empty readings in the preprocessed files for all 9 sensors (total 1,082,622). overview.csv therefore describes the preprocessed version on its common 5-second grid, not the raw files. The 573 extra raw rows are readings outside that grid. The policy should state which version a summary file describes, who investigates a discrepancy and where it is recorded.

## 3. Open questions for the coordinator
- Is the household cold-chain data covered by the same counts and rules? Its README states different loggers and a different interval.
- Who owns the decision log entry that makes this policy approved?

## 4. Evidence
docs/dataset/sensor_missing_values_report.md, docs/dataset/sensor_missing_values_report.csv, docs/dataset/sensor_missing_values_comparison.csv, docs/evidence/2026-11-14_sensor_missing_values_run.txt

## 5. Status
Manash review: completed with the changes above. Team approval: pending the coordinator.