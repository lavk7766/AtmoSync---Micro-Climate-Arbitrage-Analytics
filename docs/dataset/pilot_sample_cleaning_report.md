# AtmoSync – Dataset Quality and Pilot Sample Cleaning Report

**Date:** 16 November 2026

**Author:** Manash Mandal – Snowflake / dbt / SQL Data Engineer

## 1. Objective

Complete the data-quality validation assigned on 15 November and generate separate cleaned pilot samples for cold-storage sensor data and household refrigerator reference data.

## 2. Dataset Quality Validation

A total of 141 measurement files were analyzed.

| Metric | Raw Sensor | Preprocessed Sensor | Household |
|---|---:|---:|---:|
| Files | 9 | 9 | 123 |
| Records | 1,083,195 | 1,411,515 | 180,687 |
| Duplicate records | 0 | 0 | 0 |
| Duplicate time keys | 0 | 0 | 0 |
| Invalid time keys | 0 | 0 | 0 |
| Missing cells | 0 | 657,786 | 0 |
| Non-numeric cells | 0 | 0 | 0 |
| Non-finite cells | 0 | 0 | 0 |
| Irregular intervals | 3 | 0 | 0 |
| Repeated header rows | 4 | 0 | 0 |
| Temperature screening violations | 0 | 0 | 0 |
| Humidity range violations | 0 | 0 | 0 |

No identity or header consistency issues were detected.

## 3. Measurement Units and Plausibility

- Cold-storage temperature: degrees Celsius.
- Relative humidity: percentage.
- Cold-storage sampling interval: 5 seconds.
- Household sampling interval: 5 minutes.
- Household time: elapsed minutes.
- Cold-storage temperature screening range: -50 to 80 degrees Celsius (provisional).
- Household temperature screening range: -30 to 70 degrees Celsius, based on the documented logger range.
- Humidity screening range: 0 to 100 percent.

Preprocessed sensor units are inferred from comparison with the raw dataset.

These screening ranges are not validated food-safety or spoilage thresholds.

## 4. Cleaning Transformations

The following transformations were applied:

1. Parsed timestamps using the documented date and time format.
2. Converted measurement fields into numeric values.
3. Standardized column names and measurement units.
4. Sorted records chronologically within each device.
5. Derived device identifiers from source filenames.
6. Added source filename, source row and source-type fields.
7. Preserved missing measurements as NULL, represented by empty CSV fields.
8. Added missing-measurement quality flags to sensor records.
9. Calculated intervals before sample selection.
10. Preserved refrigerator types and measurement context.

No measurement imputation was performed. No original source files were overwritten.

## 5. Pilot Sample Selection

### Cold-storage sensor sample

Source: Preprocessed sensor dataset.

Selection method: First 100 chronological records per sensor, plus up to 100 missing-measurement records per sensor. Overlapping sample selections were removed.

| Metric | Count |
|---|---:|
| Source records | 1,411,515 |
| Selected records | 1,100 |
| Records outside sample | 1,410,415 |
| Sensors represented | 9 |
| Source missing temperature values | 328,893 |
| Source missing humidity values | 328,893 |
| Sample missing temperature values | 500 |
| Sample missing humidity values | 500 |
| Sample duplicate keys | 0 |
| Imputed values | 0 |

Output: data/processed/sensor_pilot_sample.csv

### Household refrigerator sample

Selection method: First 100 chronological records per refrigerator.

| Metric | Count |
|---|---:|
| Source records | 180,687 |
| Selected records | 12,300 |
| Records outside sample | 168,387 |
| Refrigerators represented | 123 |
| Sample duplicate keys | 0 |
| Source missing cells | 0 |
| Sample missing cells | 0 |
| Imputed values | 0 |

Output: data/processed/household_pilot_sample.csv

Records outside the pilot samples remain unchanged in the source datasets.

## 6. Unresolved Quality Limitations

- Three irregular sampling intervals remain in the raw sensor dataset.
- Preprocessed sensor data contains 328,893 missing temperature and humidity values per field.
- Original preprocessing methodology has not been fully verified.
- Historical sensor timestamp timezone remains unconfirmed.
- Sensor identity is derived from filenames rather than embedded device identifiers.
- Pilot samples are deterministic and not statistically representative.
- Missing measurements are deliberately overrepresented in the sensor pilot sample.
- Calculated interval fields refer to consecutive source observations, not necessarily consecutive selected sample rows.
- Household data represents domestic refrigerators, not shipping-container telemetry.
- Cold-storage screening thresholds require further review.
- Dataset redistribution permissions require confirmation before publishing sample CSV files.
- The proposed missing-data policy remains subject to team approval.

## 7. Deliverables

- scripts/validate_dataset_quality.py
- scripts/generate_cleaned_pilot_samples.py
- docs/dataset/dataset_quality_report.csv
- docs/dataset/pilot_sample_cleaning_report.md
- data/processed/sensor_pilot_sample.csv (local)
- data/processed/household_pilot_sample.csv (local)

## 8. Conclusion

The dataset-quality validation and pilot sample generation were executed successfully. Both pilot samples contain zero duplicate keys. Missing measurements have been preserved without imputation, and the original datasets remain unchanged.

The samples are suitable for exploratory pipeline development, subject to the documented limitations and team review.