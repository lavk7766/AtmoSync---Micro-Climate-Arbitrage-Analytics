# Pipeline Validation: 12 November 2026 (Manash Mandal)

## 1. Scope
Snowflake raw sensor data, dbt staging, intermediate and mart models, and the data quality tests.

## 2. Sensor ingestion (RAW.RAW_SENSOR_READINGS)
- Rows loaded: 1,083,195 from 9 sensors. The row count per sensor matches the loader output exactly (difference 0 for all 9 sensors), and first and last readings match.
- Duplicate sensor and timestamp pairs: 0. Rows with NULL temperature or humidity: 0.
- Humidity outside 0 to 100: 0. Temperature outside -30 to +70 C: 0.
- Overlap window of all 9 sensors (INTERMEDIATE.int_sensor_readings_common_window; the time span in which every sensor has readings, not the wider window of the preprocessed files described in section 2.5 of the data design document): 2024-09-09 16:13:15 to 2024-09-11 03:32:40, 9 sensors, 228,906 rows (25,434 readings per sensor).
- Evidence: screenshots 01 and 02.

## 3. dbt execution
| Command | Result | Log |
|---|---|---|
| dbt run | PASS=10 (6 staging views, 2 intermediate views, 2 mart tables) | docs/evidence/2026-11-12_dbt_run.txt |
| dbt test | PASS=47, 0 failures | docs/evidence/2026-11-12_dbt_test.txt |

Models land in the intended schemas: STAGING (views), INTERMEDIATE (views), MARTS (tables).

## 4. Tests by type (47)
| Type | Count | Covers |
|---|---|---|
| Singular (SQL) | 16 | per-kg conversion rules, price status uniqueness per product and series, banana series kept separate, commodity monthly uniqueness, household humidity and uniqueness, telemetry humidity, product map and price-status coverage, sensor humidity, temperature and uniqueness, spoilage reference temperature, humidity, shelf life and unique product |
| not_null | 28 | staging models, int_commodity_price_latest, mart_product_price_status |
| unique | 2 | telemetry event_id, commodity in int_commodity_price_latest |
| accepted_values | 1 | price_status |

## 5. Price handling
Per-kg conversion (STAGING.stg_commodity_price_monthly), evidence: screenshot 03.

| Unit | Rows | Rows with price_per_kg | Rows NULL |
|---|---|---|---|
| $/kg | 14,960 | 14,960 | 0 |
| $/mt | 23,316 | 23,316 | 0 |
| $/bbl | 2,944 | 0 | 2,944 |
| $/cubic meter | 2,716 | 0 | 2,716 |
| $/mmbtu | 2,202 | 0 | 2,202 |
| $/troy oz | 2,406 | 0 | 2,406 |
| $/dmtu | 802 | 0 | 802 |
| 2010=100 (index) | 598 | 0 | 598 |
| cents/sheet | 574 | 0 | 574 |
| Total | 50,518 | 38,276 | 12,242 |

- price_per_kg is filled only for $/kg and $/mt series. Every other unit stays NULL on purpose, because it cannot be converted to a per-kilogram price. No row is silently filled with a wrong value.
- Latest price (INTERMEDIATE.int_commodity_price_latest): one row per price series (71). The model orders by price_month, then loaded_at, then price (all descending), so even a duplicate month could not change the result. In addition, a tie cannot occur, because the tests assert one price per commodity and month (assert_commodity_monthly_unique) and one row per commodity in this model (unique_int_commodity_price_latest_commodity). Content hash before and after a full rebuild: 1780870720877619393 and 1780870720877619393, 71 rows each. Evidence: screenshots 06 and 07.
- Banana series stay separate (screenshot 04), latest month 2026-10-01:

| Series | Unit | Latest price per kg |
|---|---|---|
| banana, europe | $/kg | 1.10 |
| banana, us | $/kg | 1.18 |
| orange | $/kg | 0.75 |

- Mart status (MARTS.mart_product_price_status, 21 rows), screenshot 05: "direct match" 3 (two banana series and orange), "no price data" 18.
- Read access for the BI login (ATMOSYNC_READER): mart_container_latest 3 rows, mart_product_price_status 21 rows, int_sensor_readings_common_window 228,906 rows (screenshot 08).

## 6. Issues found and fixed
- No dbt test failed on 12 November.
- Hardening added on 12 November: explicit ELSE NULL for non-convertible units, a tie-breaker in the latest-price ordering, and three new tests (conversion rules, unique product and series in the mart, banana series separate).
-Earlier (11 November): dbt_project.yml had no schema setting for the intermediate folder, so an intermediate model without its own setting would have been built in the default STAGING schema. A setting for the intermediate folder (view, schema intermediate) was added. The run log shows INTERMEDIATE and MARTS.

## 7. Evidence
Logs: docs/evidence/. Screenshots: docs/screenshots/2026-11-12/.

## 8. Not covered yet
GPS latitude and longitude tests on telemetry (waiting for the simulator update); container metadata, market price and route models (no source data yet); spoilage and arbitrage marts (Week 3).