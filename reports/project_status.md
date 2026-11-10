# AtmoSync – Overall Project Status

**Last Updated:** 10 November 2026

## 1. Project Objective

AtmoSync – Micro-Climate Arbitrage Analytics aims to monitor environmental conditions in simulated shipping containers and identify potential spoilage risks. It combines sensor telemetry, commodity-price information and analytics to support alternative-market and rerouting decisions.

## 2. Proposed Architecture

1. Python IoT Simulator – generates environmental telemetry.
2. Apache Kafka – streams sensor events.
3. Snowflake – stores raw and processed data.
4. dbt – performs data cleaning, transformation and modelling.
5. Analytics – calculates climate, spoilage-risk and market indicators.
6. Apache Superset – presents KPIs and monitoring dashboards.
7. Alerts and Decision Support – highlights conditions requiring attention and supports alternative-market analysis.

## 3. Project Progress

### Repository and Documentation

**Completed or prepared:**
- Common repository structure established.
- Project overview and team responsibilities documented.
- Architecture and event-schema documentation initiated.
- Dataset README and inventory prepared locally.
- Data quality checklist prepared locally.
- Integration plan prepared locally.
- Daily task allocation prepared locally.

**Pending:**
- Publish local documentation to GitHub.
- Review and merge approved contributions.

### Dataset Analysis

**Completed or submitted:**
- World Bank monthly commodity-price dataset reviewed.
- Household cold-chain dataset reviewed.
- Raw and preprocessed sensor datasets reviewed.
- Data limitations and potential uses documented.
- Commodity coverage gaps identified for 18 target products.

**Pending:**
- Complete outstanding sensor-data analysis.
- Resolve missing commodity-price coverage using reliable sources or documented proxies.
- Define consistent data-quality and provenance rules.

### Python IoT Simulator and Kafka

**Evidence submitted by Aditya:**
- Sensor event schema documentation.
- Simulator and Kafka integration documentation.
- Broker, producer and consumer evidence files under `docs/evidence/`.
- Kafka repeatability test report dated 9 November 2026.
- Reported controlled test: 25 events published, 25 processed, zero rejected and zero consumer lag.
- Reported automated test suite: 25 tests passed.

**Pending:**
- Review screenshots.
- Finalize the shared event schema.
- Independently verify execution where practical.
- Test error recovery, throughput, latency and duplicate-event behaviour.
- Integrate with downstream storage.

### Snowflake and dbt

**Submitted by Manash:**
- Commodity and household dataset analysis.
- Dataset profiling scripts.
- Snowflake RAW, STAGING, INTERMEDIATE and MARTS design.
- SQL design for commodity and household raw tables.
- Commodity-price loader code.
- Proposed dbt staging, intermediate and mart models, cleaning rules and tests.

**Pending:**
- Complete sensor-data work.
- Develop and test remaining loaders.
- Execute Snowflake table creation and ingestion.
- Develop and execute dbt models.
- Run data-quality tests.
- Confirm shared dbt directory integration.
- Review and approve a Pull Request.

### Dashboard and Alerts

**Submitted by Ankush:**
- Dashboard KPI list.
- Dashboard wireframe.
- Temperature and humidity alert design.

**Pending:**
- Implement the functional Superset dashboard.
- Connect the processed data source.
- Build KPI cards, charts and filters.
- Implement and test alerts.
- Submit working screenshots or test evidence.

## 4. Team Responsibilities

| Member | Responsibility | Current evidence-based status |
|---|---|---|
| Lav Kumar | Project coordination, documentation and integration | Documentation prepared locally; publishing and coordination ongoing |
| Aditya Singh Bisht | Python simulator and Kafka | Implementation and test evidence submitted; visual and independent verification pending |
| Manash Mandal | Snowflake, dbt and SQL | Dataset analysis, design and loader code submitted; execution and models pending |
| ANKUSH PAL | Superset dashboard and alerts | KPI, wireframe and alert design submitted; functional implementation not yet verified |

## 5. Important Data Limitations

- Commodity prices are historical monthly global benchmark prices, not live local market offers.
- Only banana and orange among the 20 target products currently match the identified commodity-price series.
- Household cold-chain readings are from domestic refrigerators in Bangkok, not shipping containers.
- Historical sensor datasets contain temperature and humidity readings; simulator vibration and GPS fields are synthetic.
- Household data may support exploratory calibration, but must not be treated as validated shipping-container safety thresholds.
- Missing product prices must not be silently replaced with invented values.

## 6. Remaining Major Deliverables

### Streaming
- Finalize event schema.
- Verify simulator event generation.
- Verify Kafka producer and consumer.
- Test error handling and recovery.
- Integrate telemetry with storage.

### Data Engineering
- Complete data loaders.
- Create and validate Snowflake raw tables.
- Develop dbt staging, intermediate and mart models.
- Add and execute data-quality tests.

### Analytics
- Define climate-monitoring indicators.
- Develop spoilage-risk analysis with documented assumptions.
- Combine telemetry and commodity-price information.
- Develop alternative-market comparison logic.

### Dashboard and Alerts
- Configure Superset.
- Connect processed data.
- Implement KPI cards, charts and filters.
- Implement and test alerts.

### Integration and Delivery
- Integrate modules incrementally.
- Test each component independently.
- Complete end-to-end testing.
- Review and merge Pull Requests.
- Prepare final documentation and demonstration evidence.

## 7. Next Integration Milestones

1. Finalize data-source decisions and the telemetry event contract.
2. Verify simulator-to-Kafka execution.
3. Complete Snowflake loaders and dbt models.
4. Develop analytics and risk indicators.
5. Build the Superset dashboard and alerts.
6. Complete end-to-end integration testing.
7. Finalize documentation and project demonstration.

## 8. Overall Assessment

The project has progressed through repository setup, dataset analysis, architecture planning and initial component development. Individual implementation and documentation evidence is available across team branches.

The complete integrated system has not yet been verified.

**Overall status: Development in progress – integration and functional validation pending.**
