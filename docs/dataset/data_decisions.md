# Data decisions: missing commodity prices and household reference data

Author: Manash Mandal (Snowflake + dbt + SQL)
Last updated: 2026-11-11
Decisions by: Lav Kumar (team lead)

## 1. Missing commodity prices

**Decision:** keep prices missing for products without matching commodity price data. Investigate reliable alternative sources or suitable proxy data. Clearly document any estimated values.

**Current state**

- Source: World Bank Pink Sheet monthly prices (`CMO-Historical-Data-Monthly.xlsx`), 71 price series, loaded into `ATMOSYNC.RAW.RAW_COMMODITY_PRICE_MONTHLY` (50,518 rows).
- `price_per_kg` is calculated only where the unit allows an exact conversion: `$/kg` (as is) and `$/mt` (divided by 1,000). All other units (for example `$/bbl`, `$/troy oz`, index values) stay NULL. 54 of the 71 series have a per-kg price.
- Product-to-price matches are listed in the dbt seed `dbt/seeds/product_commodity_map.csv`. Only direct matches are in it:
  - banana: `banana, europe` and `banana, us`
  - orange: `orange`
- **18 products have no matching price series.** They appear in `mart_product_price_status` with `price_status = 'no price data'` and NULL prices:
  apple, apricot, blueberry, broccoli, cabbage, carrot, cucumber, dry onion, eggplant, garlic, grape, green beans, guava, mango, spinach, strawberry, sweet pepper, tomato.
- **No estimated or proxy values exist yet.**

**Rules for any future proxy or estimate**

- Add it to the seed with a `match_type` other than `direct` (for example `proxy`), so it can never be mistaken for a real price.
- Record the source, the method and the date in the `note` column and in this file.

**Open question for Lav:** banana has two series (Europe and US). Both are shown as separate rows. Which one should be the main one?

## 2. Household cold-chain dataset

**Decision:** use it as reference data for exploratory threshold calibration in the simulator and alerts. Domestic refrigerator readings are **not** validated shipping-container safety thresholds.

**Current state**

- 123 files, 1,469 readings per file (5-minute steps), 180,687 rows in total.
- Loaded into `ATMOSYNC.RAW.RAW_HOUSEHOLD_FRIDGE_READINGS` by `ingestion/load_household_cold_chain.py`. The loader rolls back if the row count does not match.
- Staging model: `stg_household_fridge_readings` (checks: not-null keys, humidity between 0 and 100, no duplicate fridge/time readings).
- Any threshold taken from this data must be labelled "exploratory" wherever it is used (simulator settings, alert rules, dashboards).

## 3. dbt structure

All models live in the common `dbt/` folder, using the existing `staging`, `intermediate` and `marts` folders:

| Layer | Model |
|---|---|
| staging | `stg_commodity_price_monthly`, `stg_household_fridge_readings` (plus the existing team models) |
| intermediate | `int_commodity_price_latest` |
| marts | `mart_product_price_status` |
| seed | `product_commodity_map` |