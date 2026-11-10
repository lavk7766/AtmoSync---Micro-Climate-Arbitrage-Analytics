# AtmoSync Data Quality Checklist

This checklist defines the validation work required before datasets are used in analytics or dashboards.

## 1. Sensor raw data

- [ ] Confirm all nine sensor files are present.
- [ ] Read CSV files using the semicolon delimiter.
- [ ] Confirm expected columns: Date, Time, Temperature (C), Humidity (%).
- [ ] Parse date and time values.
- [ ] Check for missing temperature and humidity values.
- [ ] Check for duplicate timestamps.
- [ ] Check chronological ordering.
- [ ] Check sampling intervals and identify gaps.
- [ ] Identify impossible or suspicious values for investigation.
- [ ] Compare file-level statistics with overview.csv.

## 2. Sensor preprocessed data

- [ ] Confirm all nine preprocessed files are present.
- [ ] Read files using the semicolon delimiter.
- [ ] Confirm expected columns: Date, Time, Temperature, Humidity.
- [ ] Check missing values and duplicate timestamps.
- [ ] Compare raw and preprocessed records.
- [ ] Identify changes in row counts.
- [ ] Document the preprocessing methodology when available.
- [ ] Verify that preprocessing has not introduced unexplained changes.

## 3. Sensor overview

- [ ] Confirm the nine sensor columns are parsed correctly.
- [ ] Validate start and end timestamps.
- [ ] Inspect Missing Start and Missing End fields.
- [ ] Verify measurement lengths against the original files.
- [ ] Recalculate minimum, maximum and mean temperature.
- [ ] Investigate unusual values and inconsistent summary statistics.

## 4. Commodity prices

- [ ] Identify the correct header row in each workbook sheet.
- [ ] Preserve the monthly period field.
- [ ] Preserve commodity-specific measurement units.
- [ ] Convert missing-value symbols into an appropriate missing representation.
- [ ] Check duplicate monthly periods.
- [ ] Check chronological ordering.
- [ ] Check missing values for each commodity.
- [ ] Verify numeric conversion.
- [ ] Record the workbook update date and source.
- [ ] Avoid mixing price series with different units.

## 5. Household cold-chain reference data

- [ ] Inspect the archive README and data dictionary.
- [ ] Confirm the measurement files and their structure.
- [ ] Verify the five-minute sampling interval.
- [ ] Check missing and duplicate measurements.
- [ ] Validate temperature and humidity fields.
- [ ] Preserve refrigerator type and measurement context where available.
- [ ] Confirm license and redistribution conditions.
- [ ] Keep this dataset clearly labelled as household refrigerator reference data.

## 6. Integration readiness

- [ ] Document the source and meaning of every field.
- [ ] Define timestamp and timezone handling.
- [ ] Define missing-data handling.
- [ ] Define units for all measurements.
- [ ] Keep historical reference data separate from simulated telemetry.
- [ ] Keep monthly commodity benchmarks separate from live market offers.
- [ ] Record transformations and validation results.
- [ ] Obtain team review before using datasets in production-style dashboards.

## Status

This checklist is a validation plan. Items should only be marked complete after the corresponding checks have actually been performed and recorded.
