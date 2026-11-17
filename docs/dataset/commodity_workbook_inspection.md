# AtmoSync — Commodity Workbook Inspection

**Date:** 17 November 2026
**Task:** Day 8 — Agricultural Commodity Workbook Inspection
**Role:** Data Engineer — Snowflake / dbt / SQL
**Prepared by:** Manash Mandal

## 1. Objective

Inspect all five sheets of the commodity workbook, identify relevant agricultural commodity series, understand the date and value layout, and document data-quality limitations.

## 2. Dataset Information

- Source: World Bank Commodity Price Data (The Pink Sheet)
- Workbook: CMO-Historical-Data-Monthly.xlsx
- Workbook update date: 3 November 2026
- Frequency: Monthly
- Currency: Nominal USD
- Historical coverage: January 1960 to October 2026

## 3. Workbook Sheet Inventory

| Sheet | Rows | Columns | Purpose |
|---|---:|---:|---|
| Monthly Prices | 808 | 72 | Historical commodity prices |
| Monthly Indices | 811 | 17 | Commodity price indices |
| Description | 135 | 20 | Commodity definitions and sources |
| Index Weights | 90 | 19 | Commodity index calculation weights |
| Mismatch Details | 156 | 7 | Workbook comparison discrepancies |

All five expected sheets are available.

## 4. Monthly Prices

The sheet contains 71 commodity series and 802 monthly periods.

- Commodity names: Excel row 5
- Measurement units: Excel row 6
- First monthly observation: Excel row 7
- Period column: Column A
- Period format: YYYYMmm
- Duplicate monthly periods: 0
- Chronological ordering: Valid

Prices are stored in wide format, with one monthly period per row and separate columns for each commodity series.

## 5. Relevant Agricultural Commodities

The workbook contains agricultural commodities across several categories:

- Fruits: Banana and Orange
- Cereals: Rice, Wheat, Maize, Barley and Sorghum
- Beverages: Cocoa, Coffee and Tea
- Oils and meals: Soybeans, Palm oil, Coconut oil, Groundnuts and related products
- Sugar: EU, US and World series
- Other agricultural products: Cotton, Rubber and Tobacco
- Animal products: Beef, Chicken, Lamb and Shrimps

Only Banana and Orange directly match the current AtmoSync product reference list.

| Commodity | Unit | Available months | October 2026 price |
|---|---|---:|---:|
| Banana, Europe | USD/kg | 358 | 1.10 |
| Banana, US | USD/kg | 802 | 1.18 |
| Orange | USD/kg | 802 | 0.75 |

Product coverage: 2 out of 20 products (10%).

The remaining 18 products have no direct matching price series.

## 6. Commodity Definitions

- Banana, Europe: Central and South American bananas, major brands, Southern European market benchmark.
- Banana, US: Central and South American bananas, major brands, US Gulf ports import benchmark.
- Orange: Mediterranean navel oranges, European Union indicative import price, CIF Paris.

These series must remain separately identifiable because they represent different market benchmarks.

## 7. Monthly Indices

- Number of index series: 16
- Monthly periods: 802
- First data row: Excel row 10
- Base period: 2010 = 100
- Duplicate monthly periods: 0
- Chronological ordering: Valid

Agriculture, Food, Beverages, and Oils and Meals indices provide broader commodity market context.

Index values are not actual commodity selling prices and must not be interpreted as USD/kg.

## 8. Index Weights

Index weights are expressed as percentages and are based on developing countries' export values during 2002–2004.

| Commodity | Non-energy index share (%) | Subgroup share (%) | Food index share (%) |
|---|---:|---:|---:|
| Bananas | 1.945320 | 15.669418 | 4.859589 |
| Oranges | 1.441849 | 11.613999 | 3.601874 |

The workbook notes that the orange weight includes orange juice.

These weights are index calculation parameters, not commodity prices or product quantities.

## 9. Mismatch Details

- Total mismatch records: 152
- Period coverage: September 2020 to July 2026
- Blank versus number: 142
- Value mismatch: 10
- Barley mismatches: 71
- Sorghum mismatches: 71
- Duplicate period-commodity keys: 0
- Banana and Orange mismatches: 0

Repeated monthly periods are expected because multiple commodities can have discrepancies in the same month.

No source values were overwritten or corrected.

## 10. Proposed Date and Value Transformation

Convert the source workbook from wide format to long format for Snowflake and dbt processing.

Example:

| price_month | commodity | price | unit |
|---|---|---:|---|
| 2026-10-01 | Banana, Europe | 1.10 | USD/kg |
| 2026-10-01 | Banana, US | 1.18 | USD/kg |
| 2026-10-01 | Orange | 0.75 | USD/kg |

Recommended transformation rules:

- Convert YYYYMmm into the first calendar day of the corresponding month.
- Preserve the original commodity series identity.
- Preserve original measurement units.
- Convert missing-value markers into NULL.
- Convert USD/metric tonne to USD/kg only where appropriate.
- Keep index values separate from monetary prices.
- Do not fabricate prices for unmatched products.

## 11. Limitations

- Only two of the 20 AtmoSync products have matching price benchmarks.
- International monthly benchmarks are not live Indian market prices.
- Banana Europe and Banana US represent different markets.
- Missing or mismatched values require documented handling.
- Zero reported fruit mismatches does not independently establish complete price accuracy.
- Local market prices and candidate market information are required for operational arbitrage recommendations.

## 12. Deliverables

- scripts/inspect_commodity_workbook.py
- docs/dataset/commodity_workbook_inspection.md
- docs/evidence/2026-11-17_commodity_workbook_inspection.txt

## 13. Conclusion

All five workbook sheets were inspected. Relevant agricultural series, monthly date structure, measurement units, index weights and reported discrepancies were documented.

Banana and Orange are suitable for historical benchmark analysis, subject to the stated market and data limitations.

The original workbook remains unchanged.
