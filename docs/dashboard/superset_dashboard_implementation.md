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

### 4.1 Staging and latest-state mart validation — 22 November 2026

The following Snowflake objects were inspected through
`ATMOSYNC.INFORMATION_SCHEMA.COLUMNS`:

- `ATMOSYNC.STAGING.STG_CONTAINER_TELEMETRY`
- `ATMOSYNC.MARTS.MART_CONTAINER_LATEST`

Both objects expose the same 13 columns, with matching data types and
column order:

- Identifiers: `EVENT_ID`, `CONTAINER_ID`
- Timestamps: `EVENT_TS`, `INGESTED_AT`
- Telemetry: `TEMPERATURE_C`, `HUMIDITY_PCT`, `VIBRATION_G`
- Location: `LATITUDE`, `LONGITUDE`
- Source metadata: `SOURCE_TYPE`, `KAFKA_TOPIC`, `KAFKA_PARTITION`,
  `KAFKA_OFFSET`

All 13 columns are nullable in both objects.

#### Row-count and identifier validation

| Validation | Staging | Mart |
|---|---:|---:|
| Total rows | 105 | 5 |
| Distinct event IDs | 105 | 5 |
| Distinct containers | 5 | 5 |
| Null event IDs | 0 | 0 |
| Null container IDs | 0 | 0 |

Both objects contain records for five containers. Staging covers
5 November 2026 10:30:00 UTC through 13 November 2026 07:58:24 UTC.
The mart covers the latest records at the end of that period.

#### Latest-event correspondence

A per-container `ROW_NUMBER()` query ordered by `EVENT_TS DESC` and
`INGESTED_AT DESC` was used to identify the latest staging event.

All five mart rows matched:
- Their corresponding staging `EVENT_ID`.
- The latest staging `EVENT_ID` for the same `CONTAINER_ID`.
- The corresponding `EVENT_TS`.

All five `IS_LATEST_EVENT` results were true.

**Dashboard dataset guidance:**
- Use staging for historical telemetry, time-series charts and timestamp-gap
  analysis.
- Use the latest-state mart for one-row-per-container KPI cards and latest
  container status.
- Use `CONTAINER_ID` for container-level grouping and filter scoping.
- `EVENT_ID` is the verified event-level correspondence key for the five
  mart records inspected.
- Keep the staging and mart datasets separate in Superset when their
  different historical and latest-state purposes are sufficient. If a
  cross-table comparison is required, validate the join cardinality first.

This validation describes the queried data; it does not establish a
permanent uniqueness constraint or guarantee future mart refresh behaviour.

### 4.2 Live Snowflake and dashboard validation — 23 November 2026

Superset services were restarted and verified healthy. A live SQL query
through Superset SQL Lab successfully accessed the Snowflake staging and
mart objects.

#### Live row-count and identifier validation

| Validation | Staging | Mart |
|---|---:|---:|
| Total rows | 111 | 5 |
| Distinct event IDs | 111 | 5 |
| Distinct containers | 8 | 5 |
| Null event IDs | 0 | 0 |
| Null container IDs | 0 | 0 |
| Duplicate event rows | 0 | 0 |

A per-container latest-event comparison found that all five mart records
matched the latest staging event for their respective containers.

Three additional staging containers were absent from the mart:
- TEST_LIVE_001 — synthetic_simulated; topic
  atmosync_ingestion_test_20261122.
- TEST_MERGE_002 — synthetic_simulated; topic
  atmosync_ingestion_test_20261122.
- TEST_SPOILAGE_001 — synthetic_test; topic
  spoilage_integration_test.

These records are labelled as synthetic test/integration data. Their
exclusion from the mart may be intentional, but the filtering rule and
intended mart scope require confirmation from the data owner.

#### Ingestion freshness validation

The latest mart ingestion was 13 November 2026 00:13:06.608 UTC,
with a query-reported age of 244.35 hours.

Source/topic inspection returned:
- container_sensor_telemetry: 100 rows; latest ingestion age
  approximately 244.33 hours.
- atmosync_ingestion_test_20261122: 2 rows; approximately 21.55 hours.
- spoilage_integration_test: 4 rows; approximately 20.35 hours.
- sample: 5 rows; approximately 434.78 hours.

All inspected source groups were labelled synthetic_simulated or
synthetic_test. Recent test-topic ingestion does not establish that fresh
production telemetry is flowing.

#### Mart uniqueness checks

The mart contained five rows, five distinct event IDs and five distinct
containers. A GROUP BY CONTAINER_ID query with HAVING COUNT(*) > 1
returned no rows.

No duplicate event IDs were detected in staging or mart. These results
describe the current snapshot only; they do not establish a permanent
uniqueness constraint or guarantee future refresh behaviour.

#### Dashboard refresh and Draft review

The AtmoSync Container Monitoring Dashboard remained in Draft status
and was not published.

A manual dashboard refresh produced the following comparison:

| Metric | Before refresh | After refresh |
|---|---:|---:|
| Top monitored containers | 5 | 5 |
| Lower monitored containers | 8 | 8 |
| Data quality | 100% | 100% |
| Data freshness | 243.87 hours | 243.97 hours |
| Active containers (24h) | 3 | 3 |
| Sampling consistency | 89.32% | 89.32% |

The freshness value advanced by 0.10 hours; the other listed values
remained unchanged. This confirms the displayed values after a manual
refresh, but does not demonstrate ingestion of new production telemetry.

The dashboard displays both five-container latest-state KPIs and
eight-container staging-related KPIs. Their different dataset scopes
must be made explicit to dashboard users.

Additional review items include synthetic test records visible in
telemetry charts, the freshness KPI source/filter definition, quality
metric definition, sampling threshold approval and commodity chart
configuration.

### 4.3 Live freshness, filtering and uniqueness validation — 24 November 2026

Superset services were restarted and verified healthy. Live SQL queries
through Superset SQL Lab successfully accessed the Snowflake staging and
latest-state mart tables.

#### Live freshness and row-count validation

| Metric | Staging | Mart |
|---|---:|---:|
| Total rows | 111 | 5 |
| Distinct event IDs | 111 | 5 |
| Distinct containers | 8 | 5 |
| Latest event timestamp | 22 Nov 2026 15:00:20 UTC | 13 Nov 2026 07:58:24 UTC |
| Latest ingestion timestamp | 22 Nov 2026 08:12:10.512 | 13 Nov 2026 00:13:06.608 |
| Ingestion age at query time | 36.53 hours | 260.52 hours |

The mart's latest ingestion remains on 13 November, while staging contains
later records. The mart ingestion age was approximately 224 hours greater
than the staging ingestion age at query time. The cause and expected refresh
schedule remain unconfirmed.

#### Source and synthetic-data inspection

All 111 staging rows were grouped into four source/topic combinations:

| Source type | Kafka topic | Rows | Containers | Latest ingestion |
|---|---|---:|---:|---|
| synthetic_test | spoilage_integration_test | 4 | 1 | 22 Nov 2026 08:12:10.512 |
| synthetic_simulated | atmosync_ingestion_test_20261122 | 2 | 2 | 22 Nov 2026 07:00:18.033 |
| synthetic_simulated | container_sensor_telemetry | 100 | 5 | 13 Nov 2026 00:13:06.608 |
| synthetic_simulated | sample | 5 | 3 | 5 Nov 2026 01:46:11.198 |

All inspected staging records are labelled synthetic_test or
synthetic_simulated. No production-labelled source was present in this
query result. This does not establish whether production ingestion exists
outside these inspected tables.

The mart contains only CONT001–CONT005, all from
synthetic_simulated / container_sensor_telemetry, with one row per
container. The three additional test containers in staging are not in
the mart. The intended filtering policy still requires data-owner
confirmation.

#### Event and container uniqueness checks

| Check | Staging | Mart |
|---|---:|---:|
| Total rows | 111 | 5 |
| Distinct event IDs | 111 | 5 |
| Duplicate event rows | 0 | 0 |

A GROUP BY CONTAINER_ID query with HAVING COUNT(*) > 1 returned no rows
for the mart. The current snapshot therefore has one row per mart
container and no duplicate event IDs in either dataset. These checks do
not establish permanent uniqueness constraints or future refresh guarantees.

#### Dashboard filter and KPI scope validation

The Draft dashboard exposed:
- Container ID filter: 8 selectable containers.
- Container ID (Latest KPI) filter: 5 selectable containers.

The three test IDs TEST_LIVE_001, TEST_MERGE_002 and TEST_SPOILAGE_001
were selectable in the general Container ID filter, but not in the
five-option latest KPI filter.

With TEST_MERGE_002 selected:
- The top latest-state Total Monitored Containers KPI remained 5.
- The lower staging-related Total Monitored Containers KPI changed
  from 8 to 1.
- The telemetry charts reflected the selected test container.
- The Container Health Overview returned no rows.

After clearing the selection:
- The top KPI returned/remained at 5.
- The lower KPI returned to 8.
- The Container Health Overview displayed CONT001–CONT005 again.

This confirms different filter and dataset scopes across dashboard
components. Synthetic test records are accessible through the general
telemetry filter and can affect staging-based visualizations.

#### Dashboard refresh validation

The dashboard remained in Draft status. The following values were
observed during the 24 November review:

| Metric | Observed value |
|---|---:|
| Top monitored containers | 5 |
| Lower monitored containers (unfiltered) | 8 |
| Data freshness in SQL query | 260.52 hours |
| Data freshness displayed on dashboard | 260.58 to 260.75 hours |
| Container data quality | 100% |
| Active containers (last 24 hours) | 0 |
| Telemetry sampling consistency | 89.32% |

The freshness value advanced between SQL and dashboard observations.
Manual refresh and filter reset restored the unfiltered dashboard
presentation, but did not demonstrate new mart ingestion. The active
container KPI remained zero. The exact freshness KPI SQL, its source and
filter scope, and the scheduled mart refresh behaviour remain to be
confirmed.

The current data-quality and sampling-consistency values are recorded
as observed dashboard outputs; their definitions and thresholds still
require team approval.

## 5. Provisional Sampling-Consistency Calculation

The verified SQL logic classifies an observed interval as consistent
when its duration is at least 5 seconds and strictly below 10 seconds.

The provisional KPI is calculated as:

`Intervals with 5 <= gap_seconds < 10 / All observed intervals * 100`

The observed result was 90%.

**This is not an approved data-completeness measure.** The assumed interval
range requires team confirmation. Simulator downtime, observation-window
selection and timestamp tolerance must be considered before finalizing
a production metric.

## 6. Alert Configurations

Three alert configurations were reviewed and executed in Superset:

1. Container Data Quality Alert – checks the data-quality percentage
   against a 100% threshold.
2. AtmoSync Data Freshness Alert – checks whether the age of the latest
   ingested record exceeds 24 hours.
3. Coffee Price Spike Alert – checks the configured commodity-price
   condition using the Snowflake staging source.

### Alert execution and notification validation — 20 November 2026

Three alert configurations were reviewed and executed:
- Container Data Quality Alert.
- AtmoSync Data Freshness Alert.
- Coffee Price Spike Alert.

Gmail SMTP notification delivery was tested and actual email receipt was
confirmed. The Coffee Price Spike SQL was also corrected to use the verified
Snowflake staging source and commodity label.

Alert thresholds and notification behaviour remain subject to team review.
The dashboard is still in Draft status and has not been published.

## 7. Known Limitations and Pending Validation

- Confirm display units and chart labels against the approved data dictionary.
- Verify the source unit and interpretation of vibration measurements.
- Confirm timestamp display timezone.
- Confirm the expected telemetry cadence and acceptable sampling tolerance.
- Agree on simulator downtime handling.
- Finalize the data-completeness calculation.
- Review alert thresholds and notification behaviour with the team.
- Confirm whether synthetic test/integration topics should be excluded
  from production-facing dashboard charts and the latest-state mart.
- Investigate the mart refresh schedule and why its latest ingestion remains
  at 13 November 2026 despite later test-topic ingestion.
- Confirm the freshness KPI source, filters and expected production-data
  scope.
- Confirm one-row-per-container uniqueness and event-ID deduplication
  guarantees across future mart refreshes.
- Clarify the different five-container mart and eight-container staging
  KPI scopes in dashboard labels and descriptions.
- Approve data-quality metric definitions, sampling thresholds, cadence,
  downtime handling and alert thresholds.
- Review dashboard charts, filters and commodity comparisons with the team.
- Obtain approval before publishing the Draft dashboard.
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
