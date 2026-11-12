# AtmoSync Dataset Documentation

## Purpose

This directory documents the datasets used by AtmoSync – Micro-Climate Arbitrage Analytics.

The project combines environmental sensor information with commodity-price reference data to support exploratory analysis of environmental conditions and market opportunities.

## Dataset categories

1. Sensor measurements: raw and preprocessed temperature and humidity readings from nine sensors.
2. Sensor overview: measurement periods, missing intervals and summary statistics.
3. Household cold-chain reference: refrigerator temperature and relative humidity measurements from Bangkok, Thailand.
4. Commodity prices: World Bank Pink Sheet monthly commodity prices and indices.

## Important data limitations

- The sensor files are historical reference measurements, not confirmed live shipping-container telemetry.
- Household refrigerator measurements are not shipping-container measurements.
- World Bank commodity prices are monthly benchmark reference prices, not live local market offers.
- Missing intervals and data quality must be evaluated before analysis.
- Do not interpret statistical summaries as validated food-safety thresholds.

## Related documentation

- [Dataset inventory](dataset_inventory.md)
- [Data quality checklist](data_quality_checklist.md)
