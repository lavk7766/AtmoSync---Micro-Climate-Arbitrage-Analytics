# AtmoSync Dataset Inventory

Last inspected: 10 November 2026

## 1. Sensor raw data

**File:** `data/raw/sensor_data/Raw.zip`

- Contains nine sensor CSV files: SENSOR01 to SENSOR09.
- Verified example file: `SENSOR06.CSV`.
- Columns:
  - `Date`
  - `Time`
  - `Temperature (C)`
  - `Humidity (%)`
- Delimiter: semicolon (`;`).
- Example records show measurements at five-second intervals.
- Date example: `02.09.2024`.

## 2. Sensor preprocessed data

**File:** `data/raw/sensor_data/Preprocessed.zip`

- Contains nine preprocessed sensor CSV files.
- Naming pattern: `SENSOR01_preprocessed.csv` to `SENSOR09_preprocessed.csv`.
- Verified columns:
  - `Date`
  - `Time`
  - `Temperature`
  - `Humidity`
- Delimiter: semicolon (`;`).
- Example records show measurements at five-second intervals.

The complete preprocessing methodology has not yet been verified. Do not assume which cleaning, filtering or imputation operations were applied.

## 3. Sensor overview

**File:** `data/raw/sensor_data/overview.csv`

- Delimiter: semicolon (`;`).
- Contains information for SENSOR01 through SENSOR09.
- Includes:
  - Start and end timestamps
  - Missing Start and Missing End
  - Measurement length
  - Temperature minimum, maximum and mean
  - Additional measurement statistics

The displayed measurement periods span September 2–11, 2024.

Some sensors have recorded missing intervals. Validate the overview structure and its summary values against the original sensor files before analysis.

## 4. Commodity price data

**File:** `data/raw/commodity_prices/CMO-Historical-Data-Monthly.xlsx`

Source description in workbook: World Bank Commodity Price Data (The Pink Sheet).

Workbook sheets include:

- Mismatch Details
- Monthly Prices
- Monthly Indices
- Description
- Index Weights

### Monthly Prices

- Monthly commodity prices in nominal US dollars.
- Workbook description: 1960 to present.
- First column contains monthly periods, for example `1960M01`.
- Remaining columns contain commodity names.
- The row immediately below the commodity names contains measurement units.
- Examples of commodities include crude oil, natural gas, rice, wheat, coffee, copper, gold and silver.
- Units vary by commodity, including dollars per barrel, kilogram, metric tonne and troy ounce.

### Monthly Indices

- Monthly commodity group indices.
- Base year: 2010 = 100.
- Workbook description: 1960 to present.
- Includes total, energy, non-energy, agriculture and other commodity group indices.

Workbook update date displayed: November 03, 2026.

The actual table headers must be handled separately from introductory rows when importing the workbook.

## 5. Household cold-chain reference dataset

**File:** `data/raw/household_cold_chain/dataverse_files.zip`

Dataset title: Dataset of household cold-chain conditions: temperature and relative humidity monitoring in domestic refrigerators in Bangkok, Thailand.

Verified README information:

- 123 domestic refrigerators.
- Refrigerator types:
  - 41 single-door
  - 77 two-door/top-freezer
  - 5 two-door/bottom-freezer
- Measurements use a five-minute sampling interval.
- Measurement protocol describes seven days of monitoring, with five days selected after stabilization.
- Archive contains measurement text files, figures, an R script and a README.

Fields documented in the README include:

- `Time`: elapsed time in minutes
- `T_AMB`: ambient air temperature
- `T_MS`: middle shelf air temperature
- `T_TS`: top shelf air temperature
- `T_VD`: vegetable drawer air temperature
- `T_DS`: door shelf air temperature
- `T_FC`: freezer compartment or coldest-zone air temperature
- `RH_AMB`: ambient relative humidity
- `RH_MS`: middle shelf relative humidity
- `RH_TS`: top shelf relative humidity
- `RH_VD`: vegetable drawer relative humidity
- `RH_DS`: door shelf relative humidity
- `RH_FC`: freezer compartment relative humidity
- `TP`: product temperature

The README identifies the sensor equipment as TagPlus TH (Freshliance). It reports temperature resolution of 0.1°C and expanded uncertainty of ±0.5°C (k=2), and relative-humidity resolution of 0.1% with expanded uncertainty of ±3% (k=2).

Reference dataset DOI:
https://doi.org/10.57745/TMWYBQ

### Usage limitation

This dataset concerns domestic refrigerators in Bangkok. It is a cold-chain reference dataset and must not be represented as actual shipping-container telemetry.

Check the dataset's license and redistribution conditions before sharing its contents.

## 6. Data interpretation rules

- Preserve original raw files.
- Use the correct delimiter when reading sensor CSV files.
- Parse dates and times explicitly.
- Preserve commodity-specific units.
- Treat missing intervals separately from measured values.
- Record all cleaning and transformation steps.
- Document dataset provenance and limitations in analysis reports.
