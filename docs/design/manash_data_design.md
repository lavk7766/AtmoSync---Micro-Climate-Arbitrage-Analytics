# AtmoSync: Data Design (Manash Mandal)

Author: Manash Mandal (Snowflake, dbt and SQL)
Date: 10 November 2026
Status: Section 1 complete. Sections 2 and 3 pending (cold-chain and sensor data inspection).

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

## 2. Household Cold-Chain Dataset
Pending: inspection in progress.

## 3. Snowflake Schema Plan and dbt Model Structure
Provisional (commodity prices only; final version after Section 2):

| Layer | Object | Purpose |
|---|---|---|
| Raw | RAW_COMMODITY_PRICE_MONTHLY (price_month, commodity, unit, price, source_file, loaded_at) | Long format, loaded by a script |
| Staging | stg_commodity_price_monthly | Clean names, date type, NULL handling |
| Intermediate | int_fruit_prices | Banana (Europe, US) and Orange in $/kg |
| Mart | To be defined in Week 3 | Joins prices with spoilage reference and telemetry |

Planned dbt tests: price_month not null, commodity not null, unit not null, price not negative, and one row per commodity and month.