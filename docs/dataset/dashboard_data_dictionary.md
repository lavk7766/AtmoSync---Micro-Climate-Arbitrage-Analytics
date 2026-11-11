# AtmoSync – Dashboard Data Dictionary

**Owner:** Ankush Pal  
**Role:** Apache Superset, BI Dashboard & Alerts Developer  
**Date:** 11 November 2026

## 1. Purpose

This document identifies the source fields, units, descriptions and proposed
dashboard fields required for AtmoSync analytics.

The project uses three distinct data sources. Household refrigerator data
must not be treated as shipping-container telemetry.

## 2. Cold-Storage Sensor Dataset

**Source:** Raw.zip, Preprocessed.zip and overview.csv  
**Coverage:** 9 sensor files (SENSOR01 to SENSOR09)  
**Measurement fields:** Temperature and relative humidity.

| Source field | Proposed dashboard field | Data type | Unit | Description |
|---|---|---|---|---|
| Date | reading_date | Date | YYYY-MM-DD | Date of sensor reading |
| Time | reading_time | Time | HH:MM:SS | Time of sensor reading |
| Date + Time | timestamp | Timestamp | Date/time | Combined reading timestamp |
| Temperature (C) / Temperature | temperature_c | Numeric | °C | Recorded temperature |
| Humidity (%) / Humidity | relative_humidity_pct | Numeric | % | Recorded relative humidity |
| Filename (SENSOR01...) | sensor_id | String | N/A | Sensor identifier derived from filename |

### Dashboard measures

| Measure | Calculation / usage | Dashboard purpose |
|---|---|---|
| Average temperature | AVG(temperature_c) | Temperature KPI |
| Average humidity | AVG(relative_humidity_pct) | Humidity KPI |
| Minimum temperature | MIN(temperature_c) | Temperature analysis |
| Maximum temperature | MAX(temperature_c) | Temperature analysis |
| Temperature trend | Temperature grouped by timestamp | Time-series chart |
| Humidity trend | Humidity grouped by timestamp | Time-series chart |
| Sensor comparison | Group readings by sensor_id | Sensor comparison |
| Reading count | COUNT(readings) | Data availability |
| Missing readings | Count of missing expected readings, after defining expected intervals | Data-quality KPI |

**Important:** Raw and preprocessed files are separate source versions.
Their records should not be combined without checking overlap and duplication.
The overview.csv file is reference metadata/statistics, not a replacement
for the individual time-series readings.

## 3. Household Refrigerator Reference Dataset

**Source:** dataverse_files.zip  
**Dataset title:** Dataset of household cold-chain conditions: temperature
and relative humidity monitoring in domestic refrigerators in Bangkok,
Thailand.

**DOI:** https://doi.org/10.57745/TMWYBQ

This dataset represents household refrigerators and is separate from
shipping-container sensor telemetry.

| Source field | Proposed dashboard field | Unit | Description |
|---|---|---|---|
| Time elapsed (minutes) | elapsed_minutes | Minutes | Time elapsed during measurement |
| T_AMB | ambient_temperature_c | °C | Ambient temperature |
| T_MS | temperature_ms_c | °C | MS measurement location |
| T_TS | temperature_ts_c | °C | TS measurement location |
| T_VD | temperature_vd_c | °C | VD measurement location |
| T_DS | temperature_ds_c | °C | DS measurement location |
| T_FC | temperature_fc_c | °C | FC measurement location |
| RH_AMB | ambient_humidity_pct | % | Ambient relative humidity |
| RH_MS | humidity_ms_pct | % | MS relative humidity |
| RH_TS | humidity_ts_pct | % | TS relative humidity |
| RH_VD | humidity_vd_pct | % | VD relative humidity |
| RH_DS | humidity_ds_pct | % | DS relative humidity |
| RH_FC | humidity_fc_pct | % | FC relative humidity |
| TP | product_simulating_temperature_c | °C | Gel product-simulating temperature |

**Dashboard usage:** Optional separate household refrigerator reference
comparison. Preserve refrigerator identifiers and refrigerator types
where available.

**Restriction:** Do not merge these measurements into the shipping-container
sensor population or label them as container readings.

## 4. World Bank Commodity Price Dataset

**Source:** CMO-Historical-Data-Monthly.xlsx  
**Worksheet:** Monthly Prices  
**Frequency:** Monthly  
**Latest source update inspected:** 03 November 2026  
**Latest available month inspected:** October 2026

| Source field / series | Proposed dashboard field | Unit | Description |
|---|---|---|---|
| Date | price_month | YYYYMM | Monthly observation period |
| Cocoa | cocoa_price | USD/metric tonne | Global benchmark price |
| Arabica Coffee | arabica_coffee_price | USD/kg | Global benchmark price |
| Maize | maize_price | USD/metric tonne | Global benchmark price |
| Thai Rice 5% | thai_rice_5pct_price | USD/metric tonne | Global benchmark price |
| US Wheat SRW | us_wheat_srw_price | USD/metric tonne | Global benchmark price |
| Crude Oil Average | crude_oil_avg_price | USD/barrel | Global benchmark price |
| US Natural Gas | us_natural_gas_price | USD/MMBtu | Global benchmark price |
| Gold | gold_price | USD/troy ounce | Global benchmark price |

**Dashboard usage:**
- Monthly commodity price trends.
- Latest available benchmark price.
- Month-over-month percentage change.
- Historical price comparison.

**Important:** These are global benchmark prices, not local Indian market
offers. They cannot independently establish profitable arbitrage.
Local prices, transport costs, availability and timing are also required.

## 5. Proposed Common Dashboard Fields

The following are proposed standardized fields for future staging models.
They are not claimed to exist in every original source file.

| Proposed field | Data type | Unit | Purpose |
|---|---|---|---|
| source_dataset | String | N/A | Identify source dataset |
| sensor_id | String | N/A | Identify sensor |
| timestamp | Timestamp | Date/time | Time-series analysis |
| temperature_c | Numeric | °C | Temperature KPI |
| relative_humidity_pct | Numeric | % | Humidity KPI |
| data_source_type | String | N/A | Real, reference or synthetic data |
| ingestion_timestamp | Timestamp | Date/time | Track data ingestion |

## 6. Fields Not Available in Inspected Sensor Files

| Field | Current availability | Dashboard handling |
|---|---|---|
| Vibration | Not present | Synthetic telemetry only, if generated |
| GPS latitude/longitude | Not present | Synthetic telemetry only, if generated |
| Container ID | Not verified in source files | Obtain from simulator or approved source |
| Shipping route | Not present | Obtain from simulator or approved source |
| Local market price | Not available in the inspected benchmark workbook | Requires a separate local price source |

Synthetic values must be clearly labelled and must not be presented as
real-world measurements.

## 7. Data Quality and Interpretation Rules

1. Preserve original source files and record their provenance.
2. Validate data types, timestamps, units and missing values before loading.
3. Do not silently fill missing readings or remove unusual measurements.
4. Check raw and preprocessed datasets separately for duplicates and gaps.
5. Do not define temperature or humidity alert thresholds from historical
   averages alone. Obtain approved thresholds and their source.
6. Display source labels and measurement units on dashboard charts.
7. Keep household refrigerator reference data separate from container data.
8. Show missing time periods as gaps rather than inventing observations.

## 8. Dashboard Mapping

| Dashboard component | Required fields |
|---|---|
| Average temperature KPI | temperature_c |
| Average humidity KPI | relative_humidity_pct |
| Temperature trend | timestamp, temperature_c |
| Humidity trend | timestamp, relative_humidity_pct |
| Sensor comparison | sensor_id, temperature_c, relative_humidity_pct |
| Data-quality indicators | timestamp, sensor_id, reading availability |
| Commodity trend | price_month, selected commodity price |
| Household reference view | elapsed_minutes, TP, refrigerator measurements |

## 9. Pending Validation

- Confirm final Snowflake staging-table and column names.
- Confirm timestamp format and timezone handling.
- Profile missing values and duplicate readings.
- Confirm approved alert thresholds and missing-data timeout.
- Confirm which synthetic fields will be generated by the IoT simulator.

---
**Document status:** Initial dashboard data dictionary; subject to validation
against processed data and approved Snowflake staging models.
