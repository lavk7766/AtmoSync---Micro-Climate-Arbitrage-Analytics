# AtmoSync – Superset Dashboard Implementation Notes

**Owner:** Ankush Pal
**Role:** Apache Superset, BI Dashboard & Alerts Developer
**Dashboard:** AtmoSync Container Monitoring Dashboard

## 1. Purpose

This document records the dashboard components configured in Apache Superset.
The dashboard is intended to support container telemetry monitoring, data-quality
review and commodity-market analysis.

## 2. Existing Dashboard Components

### KPI cards
- Total Monitored Containers
- Average Container Temperature
- Average Container Humidity
- Average Container Vibration
- Container Data Quality (%)
- Data Freshness (Hours)

### Time-series and analytical charts
- Container Temperature by Time
- Container Humidity by Time
- Container Vibration by Time
- Commodity Prices by Market
- Container Health Overview

### Timestamp and telemetry-availability charts added on 14 November
- Observed Timestamp Gap Distribution
- Maximum Inter-Event Gap by Container
- Long Timestamp Gaps by Container
- Telemetry Sampling Consistency (%)
- Telemetry Records by Container

## 3. Dashboard Filters

The dashboard has three native filters:

1. **Time Range**
   - Used for telemetry time-series and relevant container monitoring charts.
   - Commodity charts are excluded from its scope.

2. **Container ID**
   - Datasource: `STAGING.STG_CONTAINER_TELEMETRY`
   - Column: `CONTAINER_ID`
   - Scoped to telemetry charts and relevant container health and quality charts.

3. **Container ID (Latest KPI)**
   - Datasource: `MARTS.MART_CONTAINER_LATEST`
   - Column: `CONTAINER_ID`
   - Scoped to the four top-level KPI cards:
     - Total Monitored Containers
     - Average Container Temperature
     - Average Container Humidity
     - Average Container Vibration

### Filter validation — 20 November 2026

The two Container ID filters were tested together using `CONT001`.

Verified KPI results:

| KPI | Filtered result |
|---|---:|
| Total Monitored Containers | 1 |
| Average Container Temperature | 8.39 °C |
| Average Container Humidity | 40.60 %RH |
| Average Container Vibration | 0.729 g |

The container health overview also displayed only `CONT001`.

After clearing both filters, the dashboard returned to its default values:

| KPI | Default result |
|---|---:|
| Total Monitored Containers | 5 |
| Average Container Temperature | 5.68 °C |
| Average Container Humidity | 69.38 %RH |
| Average Container Vibration | 0.617 g |

Both filter configurations persisted after saving and refreshing the dashboard.

The separate KPI filter is necessary because the top KPI charts use
`MARTS.MART_CONTAINER_LATEST`, whereas the original Container ID filter
uses `STAGING.STG_CONTAINER_TELEMETRY`.

Commodity panels remained unaffected during the Container ID filter tests.

## 4. Data Source Notes

The telemetry staging source inspected for timestamp-gap analysis was:

`STAGING.STG_CONTAINER_TELEMETRY`

Fields used or inspected include:
- EVENT_TS
- INGESTED_AT
- CONTAINER_ID
- EVENT_ID
- TEMPERATURE_C
- HUMIDITY_PCT
- VIBRATION_G
- LATITUDE
- LONGITUDE
- SOURCE_TYPE

The inspected table did not contain a SENSOR_ID field. Therefore, the
timestamp-gap indicators are calculated at container level, not sensor level.

## 5. Provisional Sampling-Consistency Calculation

The 14 November prototype classified an observed interval as consistent
when its duration was between 5 and 10 seconds, inclusive.

The provisional KPI was calculated as:

`Intervals between 5 and 10 seconds / All observed intervals * 100`

The observed result was 90%.

**This is not an approved data-completeness measure.** The assumed interval
range requires team confirmation. Simulator downtime, observation-window
selection and timestamp tolerance must be considered before finalizing
a production metric.

## 6. Alert Prototypes

Two alert configurations were prepared in Superset:

1. Container Data Quality Alert – configured to check the data-quality
   percentage against a 100% threshold.
2. AtmoSync Data Freshness Alert – configured to check whether the age of
   the latest ingested record exceeds 24 hours.

These are prototype configurations. Successful scheduled execution and
email delivery have not yet been verified. Thresholds and notification
behaviour remain subject to team review.

## 7. Known Limitations and Pending Validation

- Confirm display units and chart labels against the approved data dictionary.
- Verify the source unit and interpretation of vibration measurements.
- Confirm timestamp display timezone.
- Confirm the expected telemetry cadence and acceptable sampling tolerance.
- Agree on simulator downtime handling.
- Finalize the data-completeness calculation.
- Verify alert execution and notification delivery.
- Export or otherwise preserve dashboard configuration as a repository
  artifact where the project workflow supports it.

## 8. Important Interpretation Rules

- Do not treat a container identifier as a sensor identifier.
- Do not treat timestamp gaps as confirmed missing readings without an
  approved expected-cadence and downtime policy.
- Do not silently clip or delete implausible measurements.
- Keep household refrigerator reference data separate from shipping-container
  telemetry.
- Clearly label synthetic or provisional data and calculations.

## 9. Commodity Market Dashboard Requirements

### 9.1 Purpose and scope

The commodity-market dashboard will provide historical monitoring of
selected global commodity benchmark prices using the World Bank Commodity
Price Data (The Pink Sheet).

The initial dashboard scope covers six commodities:
- Cocoa
- Coffee, Arabica
- Palm oil
- Soybeans
- Maize
- Rice, Thai 5%

Coffee, Robusta is documented as an additional available series and may
be included in a later dashboard iteration.

### 9.2 Source dataset

- Source file: `data/raw/commodity_prices/CMO-Historical-Data-Monthly.xlsx`
- Worksheet: `Monthly Prices`
- Frequency: Monthly
- Price basis: Nominal US dollars
- Source update date inspected: 03 November 2026
- Latest observation inspected: October 2026
- Historical coverage inspected: January 1960 to October 2026

The source update date must not be confused with the latest observation
month. The dashboard should display the latest available observation
month for the selected commodity.

### 9.3 Proposed KPI cards

1. Latest Commodity Price – latest non-missing monthly price for the
   selected commodity, displayed with its original unit.
2. Month-over-Month Change (%) – percentage change from the previous
   available month.
3. Year-over-Year Change (%) – percentage change from the corresponding
   month in the previous year.
4. Latest Observation Month – latest month with a valid price for the
   selected commodity.

Percentage-change calculations must use valid observations and handle
missing values and zero denominators explicitly.

### 9.4 Proposed charts

- Monthly Commodity Price Trend – monthly historical price for the
  selected commodity.
- Commodity Price Comparison – comparison across selected commodities.
- Monthly Percentage Change – month-over-month percentage movement.

The comparison chart must not place incompatible units on a common
unconverted scale. Use explicit unit conversion or separate unit groups.
Any normalized comparison must clearly state its base period and method.

### 9.5 Proposed dashboard filters

- Commodity
- Observation Date Range

Filters should apply consistently to the commodity KPIs and charts,
except where a KPI explicitly requires a fixed comparison period.

### 9.6 Data-quality and interpretation rules

- Preserve the original source value and commodity series identity.
- Treat unavailable markers such as `...` as missing values, not zero.
- Validate monthly dates, numeric values and units before loading.
- Do not calculate percentage changes across invalid or missing
  observations as though they were valid prices.
- Display the price unit on every KPI and chart.
- Retain source update date and latest observation month as separate
  metadata fields.
- Preserve historical source-definition changes where relevant.
- Clearly identify the World Bank benchmark as a global reference price.

### 9.7 Scope limitations

World Bank benchmark prices are not local Indian market offers.
They do not independently establish profitable arbitrage opportunities.

Further analysis requires appropriate local market prices, transport
and handling costs, availability, timing and other relevant transaction
costs. Dashboard trends should be presented as market-reference
indicators, not guaranteed trading opportunities.

### 9.8 Implementation status

This section records proposed requirements. The commodity staging model,
Snowflake table, Superset dataset, KPI calculations, chart configuration
and filter behaviour must be verified before being marked complete.
