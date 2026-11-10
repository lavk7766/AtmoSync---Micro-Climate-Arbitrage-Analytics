# AtmoSync Sensor Dataset Analysis

## 1. Objective

This document summarizes the inspection of the raw and preprocessed sensor datasets supplied for the AtmoSync Micro-Climate Arbitrage Analytics project.

The analysis focuses on:
- Identifying available sensor measurements.
- Understanding the dataset structure and measurement units.
- Examining recording periods and sampling intervals.
- Comparing raw and preprocessed sensor records.
- Identifying missing measurements and data-quality issues.
- Mapping the available measurements to the synthetic IoT telemetry schema.

## 2. Source Files

The sensor dataset directory contains three files:

| File | Description |
|---|---|
| `Raw.zip` | Original recordings from nine sensors |
| `Preprocessed.zip` | Preprocessed recordings from the same nine sensors |
| `overview.csv` | Sensor-level statistics and recording metadata |

Both ZIP archives contain nine CSV files, corresponding to `SENSOR01` through `SENSOR09`.

The overview file contains 42 metadata rows and ten columns: one metadata label column and nine sensor columns.

## 3. Dataset Structure and Field Identification

### 3.1 Raw Sensor CSV Structure

The raw sensor files use a semicolon (`;`) delimiter.

| Field | Description | Unit / Format |
|---|---|---|
| `Date` | Measurement date | DD.MM.YYYY |
| `Time` | Measurement time | HH:MM:SS |
| `Temperature (C)` | Recorded temperature | Degrees Celsius (°C) |
| `Humidity (%)` | Relative humidity | Percentage (%) |

### 3.2 Preprocessed Sensor CSV Structure

The preprocessed files use the following columns:

| Field | Description | Unit |
|---|---|---|
| `Date` | Measurement date | DD.MM.YYYY |
| `Time` | Measurement time | HH:MM:SS |
| `Temperature` | Processed temperature measurement | °C |
| `Humidity` | Processed relative humidity measurement | % |

The preprocessed field names omit the units, but correspond to the temperature and humidity measurements in the raw files.

### 3.3 Identified Sensor Variables

The inspected sensor CSV files contain two measurement variables:

- Temperature.
- Relative humidity.

**Vibration measurements are not present in the inspected raw or preprocessed sensor CSV files.** Vibration is handled separately as a synthetic measurement in the AtmoSync IoT simulator.

## 4. Raw Dataset Analysis

The raw archive contains nine sensor recordings.

| Sensor | Records | Temperature min (°C) | Temperature max (°C) | Temperature mean (°C) | Humidity min (%) | Humidity max (%) | Humidity mean (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| SENSOR01 | 156,019 | 5.30 | 42.20 | 11.34 | 26.10 | 99.90 | 75.24 |
| SENSOR02 | 156,980 | 5.80 | 38.70 | 11.94 | 28.00 | 99.90 | 74.37 |
| SENSOR03 | 84,450 | 4.80 | 21.20 | 6.54 | 67.00 | 99.90 | 87.26 |
| SENSOR04 | 151,248 | 5.60 | 22.00 | 8.37 | 53.90 | 99.90 | 79.07 |
| SENSOR05 | 31,146 | 6.90 | 13.30 | 8.24 | 52.40 | 99.90 | 70.32 |
| SENSOR06 | 156,887 | 5.10 | 22.50 | 7.80 | 53.70 | 99.90 | 79.60 |
| SENSOR07 | 156,885 | 6.00 | 22.80 | 8.54 | 53.50 | 99.90 | 83.06 |
| SENSOR08 | 156,863 | 9.00 | 22.30 | 11.69 | 41.20 | 91.30 | 63.82 |
| SENSOR09 | 32,717 | 5.40 | 12.70 | 7.32 | 55.60 | 99.90 | 78.23 |

**Total valid timestamp records across the nine raw files: 1,083,195.**

### 4.1 Overall Observed Ranges

| Measurement | Minimum | Maximum |
|---|---:|---:|
| Temperature | 4.80°C | 42.20°C |
| Relative humidity | 26.10% | 99.90% |

These are observed ranges in the supplied raw dataset, not the configured ranges of the synthetic simulator.

### 4.2 Raw Data Quality

The raw dataset inspection identified:

- One repeated header row in `SENSOR01.CSV`.
- Three repeated header rows in `SENSOR03.CSV`.
- No malformed rows reported by the analysis script.
- No invalid timestamps reported.
- No duplicate timestamps reported.
- All nine sensors have a five-second most common sampling interval.

Two sensors contained occasional intervals longer than five seconds:
- SENSOR01: one interval.
- SENSOR03: two intervals.

The other seven sensor recordings had no intervals greater than five seconds in the analysis.

## 5. Preprocessed Dataset Analysis

Each preprocessed sensor CSV contains 156,835 timestamp positions.

The common timestamp window is:

- Start: 2 September 2024, 09:35:25.
- End: 11 September 2024, 11:24:55.
- Most common sampling interval: five seconds.

The nine files therefore contain a total of 1,411,515 timestamp positions.

However, not every timestamp position contains a valid temperature and humidity pair.

### 5.1 Missing Measurement Analysis

| Sensor | Timestamp positions | Missing temperature readings | Missing percentage | Complete paired readings |
|---|---:|---:|---:|---:|
| SENSOR01 | 156,835 | 966 | 0.62% | 155,869 |
| SENSOR02 | 156,835 | 0 | 0.00% | 156,835 |
| SENSOR03 | 156,835 | 72,391 | 46.16% | 84,444 |
| SENSOR04 | 156,835 | 5,667 | 3.61% | 151,168 |
| SENSOR05 | 156,835 | 125,734 | 80.17% | 31,101 |
| SENSOR06 | 156,835 | 0 | 0.00% | 156,835 |
| SENSOR07 | 156,835 | 0 | 0.00% | 156,835 |
| SENSOR08 | 156,835 | 0 | 0.00% | 156,835 |
| SENSOR09 | 156,835 | 124,135 | 79.15% | 32,700 |
| **Total** | **1,411,515** | **328,893** | **23.30%** | **1,082,622** |

The reported missing counts are the same for temperature and humidity within each affected sensor.

SENSOR05, SENSOR09 and SENSOR03 have the highest levels of missing measurements.

### 5.2 Preprocessed Data Quality

The analysis reported:

- No repeated headers.
- No invalid records.
- No duplicate timestamps.
- No sampling intervals greater than five seconds.
- A consistent five-second timestamp grid across all nine files.

The timestamp grid includes positions with blank measurement values. These must be treated as missing readings, not as measured zero values.

## 6. Comparison of Raw and Preprocessed Data

The raw dataset contains independently recorded sensor streams with different start times, end times and record counts.

The preprocessed dataset aligns all nine sensors to a common timestamp grid containing 156,835 positions per sensor.

The preprocessed dataset retains missing values at timestamps where measurements are unavailable.

An important observation is that the `Length` values in `overview.csv` correspond to the number of complete paired temperature and humidity measurements in the preprocessed files, rather than the total number of timestamp positions.

This explains why the overview counts differ from the raw record counts and from the total number of preprocessed timestamp positions.

### 6.1 Preprocessing Implications

- A common timestamp grid simplifies comparisons between sensors.
- Missing values must be handled explicitly during downstream processing.
- Missing readings should not automatically be replaced with zero.
- Raw repeated headers should be excluded during CSV ingestion.
- Sensor-specific coverage should be considered when selecting data for analytics.

## 7. Sampling Interval and Timestamp Format

The most common sampling interval across all nine sensors is five seconds.

The raw timestamps use separate `Date` and `Time` fields.

The inspected date format is:

`DD.MM.YYYY`

The inspected time format is:

`HH:MM:SS`

No timezone information is included in the supplied CSV timestamp fields. Timezone interpretation should therefore be established separately before converting historical timestamps to UTC.

The synthetic simulator generates its own UTC event timestamps.

## 8. Mapping Dataset Fields to the Synthetic IoT Event Schema

The historical sensor data and the synthetic event structure serve different purposes.

| Historical dataset field | Synthetic event field | Mapping |
|---|---|---|
| `Date` and `Time` | `timestamp` | Historical time combined and normalized according to the ingestion policy |
| `Temperature (C)` / `Temperature` | `temperature_c` | Temperature measurement |
| `Humidity (%)` / `Humidity` | `humidity_pct` | Relative humidity |
| No equivalent field | `vibration_g` | Synthetic vibration measurement |
| No equivalent field | `event_id` | Generated UUID |
| No equivalent field | `container_id` | Simulated container identifier |
| No equivalent field | `latitude` | Simulated geographic position |
| No equivalent field | `longitude` | Simulated geographic position |
| No equivalent field | `source_type` | Synthetic event source indicator |

The synthetic event structure includes:

- `event_id`
- `container_id`
- `timestamp`
- `temperature_c`
- `humidity_pct`
- `vibration_g`
- `latitude`
- `longitude`
- `source_type`

The source type used by the simulator is `synthetic_simulated`.

Vibration and geographic coordinates are generated by the simulator and are not derived from the supplied historical sensor CSV files.

## 9. Python Simulator Development Plan

The simulator follows a modular implementation approach.

### 9.1 Sensor Generation

Generate temperature, humidity and vibration readings using configurable simulation parameters.

### 9.2 Container Generation

Create simulated container identifiers and associate them with their telemetry streams.

### 9.3 Event Construction

Build structured telemetry events containing unique UUIDs, timestamps, sensor readings and geographic coordinates.

### 9.4 Data Validation

Validate required fields, data types, numeric ranges and event structure before publishing.

### 9.5 Location Simulation

Simulate container movement along configured transportation routes using latitude and longitude coordinates.

### 9.6 Kafka Publishing

Publish validated telemetry events to the Kafka topic:

`container_sensor_telemetry`

The producer uses the container identifier as the Kafka message key.

### 9.7 Testing

Use automated tests to verify sensor generation, event construction, validation, route movement, producer-consumer behaviour and repeatability.

## 10. Kafka Publishing Workflow

The telemetry publishing workflow is:

1. Generate sensor readings.
2. Build a container-level telemetry event.
3. Attach the simulated geographic position.
4. Validate the event.
5. Serialize the event into JSON.
6. Publish it to `container_sensor_telemetry`.
7. Receive and process the event through the Kafka consumer.
8. Commit consumer offsets after successful processing.

The producer and consumer are implemented as separate components to keep message publishing and consumption independently manageable.

## 11. Key Findings and Recommendations

The dataset inspection established the following:

1. Nine sensor streams are available in the supplied raw and preprocessed archives.
2. Temperature and relative humidity are the two measured environmental variables.
3. The most common sampling interval is five seconds.
4. The preprocessed dataset provides a common timestamp grid.
5. Missing measurements are concentrated in SENSOR03, SENSOR05 and SENSOR09.
6. Repeated CSV header rows were found in the raw SENSOR01 and SENSOR03 files.
7. Vibration is not included in the inspected historical sensor CSVs and must remain a separately generated synthetic field in the simulator.

Recommended handling:

- Preserve the original raw data.
- Handle repeated headers during ingestion.
- Preserve missing values and track data-quality indicators.
- Avoid treating missing measurements as zero.
- Retain the five-second sampling information.
- Keep synthetic measurements distinguishable from historical observations.
- Document timezone assumptions when integrating historical timestamps with UTC event timestamps.

## 12. Conclusion

The supplied sensor datasets provide historical temperature and relative humidity measurements from nine sensor streams, with a dominant five-second sampling interval.

The raw and preprocessed archives offer complementary views of the measurements: the raw files preserve individual sensor recording periods, while the preprocessed files provide aligned timestamp positions with explicit missing values.

These findings support the design of the AtmoSync synthetic IoT simulator and its Kafka-based telemetry publishing workflow.

The analysis also establishes an important distinction between historically measured sensor variables and additional synthetic telemetry fields such as vibration and geographic location.
