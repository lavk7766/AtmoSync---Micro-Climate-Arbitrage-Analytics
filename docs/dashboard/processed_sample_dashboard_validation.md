# Processed Sensor Sample – Dashboard SQL Validation

- **Owner:** Ankush Pal
- **Role:** Apache Superset, BI Dashboard and Alerts Developer
- **Validation date:** 21 November 2026
- **Source:** `data/processed/reference_sensor_preview/SENSOR06_reference_preview.csv`
- **Validation method:** Python CSV parsing and in-memory SQLite queries

## 1. Source and schema

The processed reference sample is a semicolon-delimited CSV containing
household cold-storage sensor readings. The file contains 156,835 records
and these four source columns:

| Source column | Normalized field | Type / unit |
|---|---|---|
| Date | reading_date | Date |
| Time | reading_time | Time |
| Date + Time | timestamp | Timestamp |
| Temperature | temperature_c | Numeric, °C |
| Humidity | relative_humidity_pct | Numeric, % RH |
| Filename | sensor_id | Text |

The sensor identifier is derived from the filename (`SENSOR06`).
The normalized timestamp uses the source date and time together.

## 2. Data-quality checks

| Check | Result |
|---|---:|
| Total records | 156,835 |
| Missing Date values | 0 |
| Missing Time values | 0 |
| Missing Temperature values | 0 |
| Missing Humidity values | 0 |
| Valid timestamps | 156,835 |
| Duplicate timestamps | 0 |
| Timestamp intervals | 156,834 |
| Intervals exactly 5 seconds | 156,834 |
| Other timestamp intervals | 0 |
| Timestamp coverage | 2024-09-02 09:35:25 to 2024-09-11 11:24:55 |

## 3. SQL query validation

The CSV was loaded into an in-memory SQLite table named
`reference_sensor_readings`. The following dashboard-style queries ran
successfully:

- Total record count.
- Average temperature and relative humidity.
- Minimum and maximum temperature.
- Minimum and maximum relative humidity.
- Record count grouped by sensor identifier.
- Daily average temperature trend.

### Query results

| Metric | Result |
|---|---:|
| Record count | 156,835 |
| Average temperature | 7.79 °C |
| Average relative humidity | 79.61% |
| Minimum temperature | 5.1 °C |
| Maximum temperature | 22.1 °C |
| Minimum relative humidity | 53.7% |
| Maximum relative humidity | 99.9% |
| SENSOR06 record count | 156,835 |

### Daily average temperature returned by the test

| Date | Average temperature (°C) |
|---|---:|
| 2024-09-02 | 10.85 |
| 2024-09-03 | 9.85 |
| 2024-09-04 | 9.77 |
| 2024-09-05 | 7.75 |
| 2024-09-06 | 7.54 |

The daily trend table above records the five rows returned in the validation
output; it is not a complete daily summary for the entire source period.

## 4. Dashboard compatibility

The validated sample can support:

- Reading count and missing-reading checks.
- Average, minimum and maximum temperature.
- Average, minimum and maximum relative humidity.
- Temperature and humidity time-series charts.
- Daily aggregation and sensor-level grouping.

This source is household cold-storage reference data. It must remain
separate from shipping-container telemetry.

The inspected sample does not provide container ID, vibration, GPS,
shipping route or container-health fields. Therefore, it cannot directly
support the existing container-specific filters or vibration, location
and container-health KPIs.

## 5. Validation boundary and next steps

This test confirms local CSV parsing, field normalization and SQL
calculation compatibility using SQLite.

It does **not** confirm a Snowflake staging load, a Superset dataset
connection, dashboard publication or production alert behavior.

Next steps are to confirm the intended staging model and field mapping,
then test the appropriate Snowflake query and Superset connection as
part of the planned integration work. Any dashboard using this reference
sample should be labelled as household cold-storage sensor analytics,
not shipping-container monitoring.
