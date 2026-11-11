# AtmoSync: Data Design (Manash Mandal)

Author: Manash Mandal (Snowflake, dbt and SQL)
Date: 10 November 2026
Status: Section 1 complete. Section 2 partly complete (inventory and sensor overview). Section 3 pending.

## 1. Commodity Price Dataset

### 1.1 Source
- Name: World Bank Commodity Price Data (The Pink Sheet), monthly prices in nominal US dollars
- File: data/raw/commodity_prices/CMO-Historical-Data-Monthly.xlsx (updated 3 November 2026)
- Sheets: Mismatch Details, Monthly Prices, Monthly Indices, Description, Index Weights
- Used: Monthly Prices (data) and Description (series definitions)

### 1.2 Structure of the Monthly Prices sheet
| Item | Detail |
|---|---|
| Layout | Wide: one column per commodity, one row per month |
| Title rows | Rows 1 to 4 (text only) |
| Commodity names | Row 5 |
| Units | Row 6, for example ($/kg) |
| Data | From row 7 onward |
| Period | 1960M01 to 2026M10 (802 months) |
| Series | 71 commodity columns, plus a month column |

### 1.3 Units
| Unit | Series |
|---|---|
| $/mt | 34 |
| $/kg | 20 |
| $/bbl | 4 |
| $/cubic meter | 4 |
| $/mmbtu | 3 |
| $/troy oz | 3 |
| 2010=100 (index) | 1 |
| cents/sheet | 1 |
| $/dmtu | 1 |

Units are mixed, so a price is only meaningful together with its unit. The unit must be stored as a column and prices of different units must never be averaged together.

### 1.4 Data quality findings
1. Wide layout: must be unpivoted to one row per month and commodity.
2. Month format is text (for example 1960M01): convert to a date (first day of the month).
3. Missing values appear as the placeholders "…" and "...", and as blank cells (for example Gold in 1960).
4. Some names carry footnote marks (for example Beef **, Chicken **, Rubber TSR20 **) and some have trailing spaces (Urea ): strip both.
5. Banana, Europe starts in 1997-01, while Banana, US and Orange start in 1960-01.
6. Prices are nominal US dollars, monthly, global benchmark prices. They are not per-market daily prices.
7. After cleaning: 0 duplicate commodity names, 0 rows with an invalid month.

### 1.5 Coverage of the 20 spoilage-reference products
| Product | Price series in this dataset | Unit | Months | Latest |
|---|---|---|---|---|
| Banana | Banana, Europe | $/kg | 358 (1997-01 to 2026-10) | 1.10 |
| Banana | Banana, US | $/kg | 802 (1960-01 to 2026-10) | 1.18 |
| Orange | Orange | $/kg | 802 (1960-01 to 2026-10) | 0.75 |
| 18 other products | No match | not applicable | not applicable | not applicable |

No price exists here for: Apple, Tomato, Strawberry, Apricot, Blueberry, Grape, Guava, Mango, Broccoli, Cabbage, Carrot, Cucumber, Eggplant, Garlic, Spinach, Sweet Pepper, Green Beans and Dry Onion.

Banana is available for two markets (Europe and US), which can serve as two candidate markets in the arbitrage demonstration.

### 1.6 Transformation requirements
- Unpivot to long format: price_month, commodity, unit, price.
- Parse the month text into a date.
- Replace placeholders and blanks with NULL, and keep NULL rows out of the clean table.
- Strip footnote marks and surrounding spaces from commodity names.
- Standardize names to lowercase for joins with the spoilage reference.
- Keep the unit as a column. For the fruit series ($/kg) no conversion is needed.
- Record the source file name and load time.

### 1.7 Open decisions (for the Team Lead)
1. Prices for the 18 uncovered products: add a second public source, generate synthetic prices marked as assumed, or limit the demonstration to banana and orange.
2. The data is monthly and global, so arbitrage margins will be indicative, not real-time.

## 2. Household Cold-Chain and Sensor Datasets

### 2.1 Household cold-chain archive (inventory verified from the file listing)
- Archive: data/raw/household_cold_chain/dataverse_files.zip (13.6 MB); the file name indicates a Dataverse download
- 123 data files named NNN_<type>.txt (001 to 123), each about 97 to 103 KB; type suffixes seen: 1D, 2DT, 2DB
- 246 PNG charts: one temperature (_TEMP) and one humidity (_HUM) chart per data file
- Supporting files: readme.txt, MANIFEST.TXT, script_fridge.R, Fig1.png, Fig2.jpg
- Likely content: household refrigerator temperature and humidity time series (suggested by the dataset name and script_fridge.R; to be confirmed from readme.txt)

### 2.2 Sensor overview file (data/raw/sensor_data/overview.csv)
| Item | Finding |
|---|---|
| Format | Semicolon-separated, transposed (one row per property, one column per sensor) |
| Sensors | 9 (SENSOR01 to SENSOR09) |
| Period | 2024-09-02 to 2024-09-11 |
| Sampling | About one reading every 5 seconds (derived from Length and the time span) |
| Late starts | SENSOR05 and SENSOR09 start on 2024-09-09 |
| Early end | SENSOR04 ends at 2024-09-11 03:32, about 8 hours before the others |
| Gaps | Recorded for SENSOR01, 03, 04, 05 and 09 |
| Temperature range | 5.3 to 42.2 C (SENSOR01) and 5.8 to 38.7 C (SENSOR02); the other sensors peak at about 12 to 23 C |
| Humidity | Not part of overview.csv |

Data-quality needs: an outlier rule for temperatures above about 25 C, handling of the recorded gaps, and alignment of sensors that start or end at different times.

### 2.3 Household dataset structure (verified from readme.txt)
- One file per refrigerator: 123 refrigerators; file name pattern <number>_<type>.txt
- Types: 1D = single-door (41), 2DT = two-door with top freezer (77), 2DB = two-door with bottom freezer (5)
- Format: tab-delimited text, 5-minute time step; 5 days of data per refrigerator, selected from 7 recorded days after the stabilization period
- Sensors: TagPlus TH loggers (Freshliance). Temperature resolution 0.1 C, range -30 to +70 C, expanded uncertainty +/-0.5 C. Relative humidity resolution 0.1 %, expanded uncertainty +/-3 %.
- Product temperature: a sensor in a meat-simulating gel (hydroxyethyl cellulose, distilled water, antifungal agent)

| Column | Meaning |
|---|---|
| Time | Minutes elapsed since the start of the recording (no calendar timestamp) |
| T_AMB, RH_AMB | Ambient air outside the refrigerator |
| T_MS, RH_MS | Middle shelf |
| T_TS, RH_TS | Top shelf |
| T_VD, RH_VD | Vegetable drawer |
| T_DS, RH_DS | Door shelf |
| T_FC, RH_FC | Freezer compartment or coldest zone |
| TP | Product temperature (gel) |

Data-quality needs:
- Time is elapsed minutes, so a documented start date is needed before any join with container telemetry.
- Sensor columns are wide and must be unpivoted per position (one row per refrigerator, time, position and measure).
- Not every refrigerator has every compartment, so NULL handling is needed (to be confirmed from the data files).
- Humidity uncertainty (+/-3 %) is larger than temperature uncertainty (+/-0.5 C).

Relevance to AtmoSync: a reference for realistic temperature and humidity behaviour (stable periods, door-opening spikes, compartment differences) when calibrating the IoT simulator and the alert thresholds. It is not shipment data: it has no location or product name.

### 2.4 Verified file structure (samples 001_1D.txt and 002_2DT.txt)
- Data files are in the 01_src subfolder of the archive
- Header (14 columns, tab-separated): Time, T_AMB, T_MS, T_TS, T_VD, T_DS, T_FC, RH_AMB, RH_MS, RH_TS, RH_VD, RH_DS, RH_FC, TP
- Time starts at 0 and increases by 5 minutes per row
- 001_1D.txt: 1,469 data rows (about 5.1 days)
- Files per type match the readme: 1D = 41, 2DT = 77, 2DB = 5
- Freezer values differ by type: about -21 C in the first rows of 001_1D and about -5 C in 002_2DT
- TP is constant in the first rows of 001_1D (2.594)
- Full verification of all 123 files: scripts/profile_household_cold_chain.py, output in docs/design/household_file_profile.csv

### 2.5 Sensor dataset (data/raw/sensor_data)

Verified on 2026-11-11 with `scripts/profile_sensor_data.py`. The per-sensor results are in `docs/design/sensor_file_profile.csv`.

**Files**
- Raw.zip: 9 files, SENSOR01.CSV to SENSOR09.CSV
- Preprocessed.zip: 9 files, SENSOR01_preprocessed.csv to SENSOR09_preprocessed.csv
- overview.csv: one column per sensor with start, end, missing period, length and statistics

**Format**
- Semicolon-separated; dates DD.MM.YYYY; times HH:MM:SS; decimal point
- Raw header (all 9 files): `Date;Time;Temperature (C);Humidity (%)`
- Preprocessed header (all 9 files): `Date;Time;Temperature;Humidity` (no units)
- Raw readings are 5 seconds apart. There are no duplicate timestamps in any file.

**Repeated header lines.** Four lines inside the raw files are the header line again, not readings: SENSOR01 line 119,255 and SENSOR03 lines 4, 7 and 10. The cause is not known (possibly a logger restart or joined files). They hold no data, and the loader must skip them.

**Readings per raw file and the common window.** The preprocessed files share one time window, 2024-09-02 09:35:25 to 2024-09-11 11:24:55, which is 156,835 time points. The `Length` column of overview.csv counts the raw readings that fall inside this window.

| Sensor | Readings in raw file | Before window | After window | In window (= overview Length) |
|---|---|---|---|---|
| SENSOR01 | 156,019 | 107 | 43 | 155,869 |
| SENSOR02 | 156,980 | 109 | 36 | 156,835 |
| SENSOR03 | 84,450 | 6 | 0 | 84,444 |
| SENSOR04 | 151,248 | 80 | 0 | 151,168 |
| SENSOR05 | 31,146 | 0 | 45 | 31,101 |
| SENSOR06 | 156,887 | 42 | 10 | 156,835 |
| SENSOR07 | 156,885 | 23 | 27 | 156,835 |
| SENSOR08 | 156,863 | 0 | 28 | 156,835 |
| SENSOR09 | 32,717 | 0 | 17 | 32,700 |

In total there are 1,083,195 readings in the raw files, 1,082,622 inside the window and 573 outside it. This closes the earlier question about SENSOR01: 156,020 lines minus 1 repeated header line minus 107 readings before and 43 after the window gives the overview Length of 155,869.

**Gaps and late starts** (from the preprocessed files and overview.csv)

| Sensor | Time points without a reading | Note |
|---|---|---|
| SENSOR01 | 966 | one gap of 4,835 seconds on 2024-09-09 |
| SENSOR03 | 72,391 | no readings from the start of the window until 2024-09-06 14:07:55 |
| SENSOR04 | 5,667 | stops on 2024-09-11 at 03:32:40 |
| SENSOR05 | 125,734 | starts on 2024-09-09 at 16:13:15 |
| SENSOR09 | 124,135 | starts on 2024-09-09 at 14:00:00 |
| SENSOR02, 06, 07, 08 | 0 | complete |

SENSOR03 has two steps that are not 5 seconds; the largest is 362,295 seconds (about 4.2 days).

**Preprocessed files.** Every preprocessed file has exactly 156,835 rows on a complete 5-second grid. Where a sensor has no reading, both Temperature and Humidity are empty (no row has only one value missing). Every value in a preprocessed file also exists in the raw file at the same timestamp with the same value (0 values not found, 0 values different). The preprocessed files therefore contain no information that cannot be rebuilt from the raw files.

**First readings.** SENSOR01, 02, 03, 04, 06, 07 and 08 start at 21.2 to 22.2 C and 56 to 68 % humidity. SENSOR05 starts at 13.1 C and SENSOR09 at 12.0 C, because both start later (2024-09-09). For SENSOR01, 02, 04, 06 and 07 the temperature first reaches 12 C or below after 44 to 65 minutes. This is consistent with a sensor being moved into cold storage, but the data alone does not prove it. SENSOR08 takes about 695 minutes and stays warmer than the others. For SENSOR03 the figure is not meaningful because of its gap. The 12 C value is only a screening threshold, not a safety threshold.

**Comparison with the household dataset.** The sensor data has real calendar timestamps and a 5-second interval, which makes it the closest match to our IoT telemetry events. It has no location and no product name.

**Proposed handling (to be agreed with the Team Lead)**
- Role: replay source or calibration data for the simulator and alert thresholds, with `source_type = real_replayed`.
- Loading: load the raw files only, one row per reading with the sensor name, and skip the repeated header lines. The window, gaps and cleaning are handled in dbt.


## 3. Snowflake Schema Plan and dbt Model Structure

### 3.1 Database, warehouse and schemas
Database ATMOSYNC, warehouse ATMOSYNC_WH (X-Small, auto-suspend 60 s).

| Schema | Purpose | Written by |
|---|---|---|
| RAW | Source data as received, one table per source | Loader scripts |
| STAGING | One cleaned and typed model per raw table | dbt (views) |
| INTERMEDIATE | Reshaping and joins (new schema) | dbt (views) |
| MARTS | Business-ready tables for Superset | dbt (tables) |

Roles: ATMOSYNC_LOADER writes to RAW only; ATMOSYNC_READER reads RAW, STAGING, INTERMEDIATE and MARTS.

### 3.2 Raw tables
Existing: RAW_CONTAINER_TELEMETRY (JSON payload), PRODUCT_SPOILAGE_REFERENCE (20 rows), RAW_CONTAINER_METADATA, RAW_MARKET_PRICES, RAW_ROUTE_INFO, RAW_COMMODITY_PRICES (early sample table, to be retired once monthly prices are loaded).

New (script snowflake/08_commodity_and_fridge_raw_tables.sql):

| Table | Grain | Columns |
|---|---|---|
| RAW_COMMODITY_PRICE_MONTHLY | One row per commodity and month (long format) | price_month, commodity, unit, price, source_file, loaded_at |
| RAW_HOUSEHOLD_FRIDGE_READINGS | One row per refrigerator and 5-minute reading | fridge_number, fridge_type, time_minutes, t_amb, t_ms, t_ts, t_vd, t_ds, t_fc, rh_amb, rh_ms, rh_ts, rh_vd, rh_ds, rh_fc, tp, source_file, loaded_at |

Design choices:
- The commodity workbook is unpivoted before loading (71 series x 802 months, about 57,000 rows).
- The household table mirrors the source files (wide) in RAW, about 180,000 rows, and is unpivoted in dbt.
- Both tables are reloaded in full on each run, so loaders need DELETE on them.
- The sensor dataset (data/raw/sensor_data) is added after its zip files are inspected.

### 3.3 dbt models
**Staging (views)**
| Model | Source | Work done |
|---|---|---|
| stg_container_telemetry | RAW_CONTAINER_TELEMETRY | Exists: JSON parsed, deduplicated by event_id |
| stg_product_spoilage_reference | PRODUCT_SPOILAGE_REFERENCE | Exists: names lowercased and trimmed |
| stg_commodity_price_monthly | RAW_COMMODITY_PRICE_MONTHLY | Lowercase names, NULL prices removed, month as date |
| stg_household_fridge_readings | RAW_HOUSEHOLD_FRIDGE_READINGS | Decode fridge type (1D = single_door, 2DT = two_door_top_freezer, 2DB = two_door_bottom_freezer), typed columns |

**Intermediate (views)**
| Model | Purpose |
|---|---|
| int_fridge_readings_long | Unpivot to one row per fridge, time, position (ambient, middle shelf, top shelf, vegetable drawer, door shelf, freezer) with temperature_c and humidity_pct |
| int_fruit_prices | Banana (Europe, US) and Orange in $/kg, through a seed that maps each spoilage-reference product to a price series |
| int_product_price_coverage | For each of the 20 reference products: whether a price exists, the series and the latest price |

**Marts (tables)**
| Model | Purpose |
|---|---|
| mart_container_latest | Exists: latest reading per container |
| mart_fridge_temperature_profile | Mean, minimum, maximum and 95th percentile of temperature and humidity per fridge type and position, used to calibrate simulator and alert thresholds |
| mart_fruit_price_monthly | Monthly price, month-over-month change and the banana Europe versus US spread |
| mart_spoilage_risk (Week 3) | Telemetry joined to the spoilage reference: time-to-spoilage per container |
| mart_arbitrage (Week 3) | Spoilage risk joined to prices and routes: recommended reroute |

Seed: seeds/product_price_series_map.csv (product_name, price_series, unit).

### 3.4 dbt tests
- Commodity prices: price_month, commodity, unit not null; price not negative; unique per commodity and month
- Household readings: fridge_number and time_minutes not null; unique per fridge and time; fridge_type in (1D, 2DT, 2DB); relative humidity between 0 and 100; temperatures between -30 and +70 C (sensor range)
- Product price map: every product exists in stg_product_spoilage_reference
- Coverage: a warning (not an error) for reference products without a price

### 3.5 Data-cleaning requirements
| Dataset | Requirement |
|---|---|
| Commodity prices | Unpivot; parse month text (1960M01); replace placeholders and blanks with NULL; strip footnote marks and spaces; lowercase names; keep the unit as a column; do not mix units |
| Household fridge files | Read tab-separated files; strip spaces; add fridge number and type from the file name; Time is elapsed minutes (no calendar date), so it is not joined by date; handle missing compartments as NULL; flag values outside the sensor range |
| Both | Record the source file name and load time; fully reload instead of appending, so a re-run never duplicates rows |

### 3.6 Implementation order
1. Create the new raw tables and schema (snowflake/08 script)
2. Commodity loader and staging model with tests
3. Household loader and staging model with tests
4. Intermediate models and the product price map seed
5. Marts, then the Week 3 spoilage and arbitrage models

### 3.7 Decisions needed from the Team Lead
1. Prices for the 18 products that are not in the price file (second source, synthetic prices marked as assumed, or limit the demo to banana and orange).
2. Role of the household data: calibration of the simulator and alert thresholds only (proposed), since it has no location, product or calendar time.
3. Role of the sensor dataset (pending inspection).
4. Whether the dbt project moves into the repo's dbt/ folder, so only one project exists.