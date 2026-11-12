# AtmoSync Integration Plan

## 1. Project Overview

AtmoSync – Micro-Climate Arbitrage Analytics is designed to combine environmental sensor telemetry, commodity-price reference data and market information to support spoilage-risk analysis and alternative-market decision support.

The proposed architecture uses Python, Apache Kafka, Snowflake, dbt and Apache Superset.

## 2. Team Responsibilities

### Lav Kumar – Project Coordinator and Integration Manager

Responsibilities:
- Coordinate integration activities across team members.
- Maintain project documentation and repository structure.
- Track daily progress and dependencies.
- Review interface compatibility between components.
- Coordinate integration testing and final documentation.

Repository areas:
- docs/
- tests/integration/
- reports/

### Aditya Singh Bisht – Python IoT Simulator and Kafka Developer

Responsibilities:
- Develop simulated sensor telemetry.
- Define temperature, humidity and vibration event fields.
- Implement Kafka producer and event publishing.
- Maintain Kafka topic and schema documentation.
- Test event delivery and message structure.

Repository areas:
- simulator/
- kafka/
- kafka/schema/

### Manash Mandal – Snowflake, dbt and SQL Data Engineer

Responsibilities:
- Configure Snowflake data storage.
- Define raw and structured data layers.
- Develop dbt staging and transformation models.
- Integrate sensor events with relevant reference data.
- Validate transformed datasets and SQL models.

Repository areas:
- snowflake/
- dbt/models/
- analytics/

### ANKUSH PAL – Superset Dashboard and Alerts Developer

Responsibilities:
- Connect analytics datasets to Apache Superset.
- Develop project dashboards and visualizations.
- Display sensor conditions and spoilage-risk indicators.
- Implement alert logic and dashboard reporting.
- Validate dashboard data against transformed outputs.

Repository areas:
- dashboard/
- alerts/

## 3. Proposed Data Flow

1. Reference datasets are stored and documented.
2. The Python simulator generates synthetic container telemetry.
3. Kafka receives and transports telemetry events.
4. Snowflake stores incoming and reference data.
5. dbt transforms and validates data.
6. Analytics models calculate relevant risk and market indicators.
7. Superset presents dashboards and decision-support information.
8. Alerts communicate configured conditions.

## 4. Component Integration Contracts

### Simulator to Kafka

Expected interface:
- Agreed event schema.
- Container identifier.
- Event timestamp.
- Temperature.
- Humidity.
- Vibration.
- Sensor or event identifier.

The exact field names and units must be agreed by the team before implementation.

### Kafka to Snowflake

Expected interface:
- Agreed topic names.
- Consistent event schema.
- Event timestamp and source information.
- Defined ingestion method.
- Error and duplicate-event handling.

### Snowflake to dbt

Expected interface:
- Raw ingestion tables.
- Defined column names and data types.
- Agreed source table naming.
- Documented transformation rules.

### dbt to Analytics and Superset

Expected interface:
- Validated transformed tables or views.
- Documented metric definitions.
- Consistent timestamp and measurement units.
- Clear distinction between simulated telemetry and historical reference data.

## 5. Integration Testing

The following checks are planned:

- [ ] Simulator generates events using the agreed schema.
- [ ] Kafka receives and publishes events.
- [ ] Event fields and data types are validated.
- [ ] Snowflake receives the expected data.
- [ ] dbt models execute successfully.
- [ ] Transformed data passes quality checks.
- [ ] Analytics calculations are validated.
- [ ] Superset dashboards display the expected results.
- [ ] Alert conditions are tested.
- [ ] End-to-end flow is documented.

## 6. Data and Interpretation Rules

- Synthetic telemetry must be labelled as simulated.
- Historical sensor data must retain its source and context.
- Household refrigerator measurements must not be described as container measurements.
- Monthly commodity benchmarks must not be described as live local market offers.
- Risk indicators must have documented assumptions and calculation logic.
- Do not present unvalidated thresholds as certified food-safety limits.

## 7. Integration Dependencies

| Dependency | Responsible members |
|---|---|
| Event schema agreement | Lav and Aditya |
| Kafka event publishing | Aditya |
| Snowflake ingestion design | Manash |
| dbt model definitions | Manash |
| Analytics output definitions | Lav and Manash |
| Dashboard data contract | Manash and Ankush |
| Dashboard and alerts | Ankush |
| End-to-end integration review | All members, coordinated by Lav |

## 8. Current Status

This document describes the proposed integration plan. It does not imply that the components have already been implemented or connected.

Update this document as interfaces are finalized and integration tests are completed.
