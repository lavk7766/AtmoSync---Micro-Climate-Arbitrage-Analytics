# 🌍 AtmoSync – Micro-Climate Arbitrage Analytics

**An IoT-powered analytics platform for container condition monitoring, spoilage-risk assessment, and alternative-market intelligence.**

---

## 1. Project Overview

AtmoSync is a data engineering and analytics project designed to monitor environmental conditions inside shipping containers and identify potential product-spoilage risks during transportation.

The platform combines IoT sensor telemetry, cold-chain reference datasets and historical commodity-price information to generate meaningful insights for logistics and supply-chain decision-making.

By integrating Python, Apache Kafka, Snowflake, dbt and Apache Superset, AtmoSync aims to transform environmental and market data into actionable analytics.

The system will help identify potentially unsafe environmental conditions, monitor container performance and evaluate alternative-market opportunities based on available price and logistics information.

## 2. Problem Statement

Perishable products transported over long distances can be exposed to changing environmental conditions such as temperature, humidity and vibration.

These changes may affect product quality and increase the possibility of spoilage and financial losses.

Traditional monitoring systems may not combine environmental conditions with market intelligence to support timely decisions.

AtmoSync aims to address this challenge by combining environmental monitoring, data engineering, risk analytics and market-price analysis in one integrated platform.

## 3. Project Objectives

- Monitor container temperature, humidity and vibration.
- Generate simulated IoT sensor telemetry.
- Develop a real-time event-streaming pipeline.
- Store sensor and reference data in Snowflake.
- Transform and validate data using dbt.
- Identify environmental anomalies.
- Develop an explainable spoilage-risk scoring system.
- Analyse historical commodity-price trends.
- Evaluate potential alternative-market opportunities.
- Build interactive dashboards and monitoring alerts.

## 4. Proposed System Architecture

```text
       DATA SOURCES
             |
     +-------+--------+
     |                |
 Sensor Datasets   Commodity Prices
     |                |
     +-------+--------+
             |
             v
   DATA EXPLORATION
   AND PREPROCESSING
             |
             v
     PYTHON IoT SIMULATOR
             |
             v
       APACHE KAFKA
       (Event Streaming)
             |
             v
        SNOWFLAKE
      (Data Warehouse)
             |
             v
           dbt
   (Data Transformation)
             |
             v
    ANALYTICS ENGINE
     /             \
Risk Scoring    Market Analysis
     \             /
             |
             v
    APACHE SUPERSET
       (Dashboard)
             |
             v
   ALERTS AND DECISION
        SUPPORT
```

## 5. Technology Stack

| Technology | Purpose |
|---|---|
| Python | IoT simulation, data processing and analytics |
| Apache Kafka | Real-time event streaming |
| Snowflake | Cloud data warehouse |
| dbt | Data transformation, modelling and testing |
| SQL | Data analysis and warehouse queries |
| Apache Superset | Interactive BI dashboards |
| Git | Version control |
| GitHub | Team collaboration and project management |

## 6. Dataset Description

The initial project includes five dataset files.

| Dataset | File | Intended use |
|---|---|---|
| Commodity Prices | `CMO-Historical-Data-Monthly.xlsx` | Historical commodity-price analysis |
| Household Cold Chain | `dataverse_files.zip` | Cold-storage reference data |
| Raw Sensor Data | `Raw.zip` | Sensor-data exploration |
| Preprocessed Sensor Data | `Preprocessed.zip` | Prepared sensor-data analysis |
| Dataset Overview | `overview.csv` | Dataset metadata and information |

### Dataset Directory

```text
data/
└── raw/
    ├── commodity_prices/
    │   └── CMO-Historical-Data-Monthly.xlsx
    │
    ├── household_cold_chain/
    │   └── dataverse_files.zip
    │
    └── sensor_data/
        ├── Raw.zip
        ├── Preprocessed.zip
        └── overview.csv
```

### Dataset Limitations and Considerations

- Household cold-chain data is a reference source, not direct shipping-container telemetry.
- Sensor datasets must be inspected to understand their variables, measurement units, sampling intervals and missing values.
- Historical commodity benchmark prices do not represent live local-market offers.
- Synthetic shipping-container telemetry will be generated using the Python simulator.
- Product-specific risk thresholds must be supported by suitable references and documented assumptions.
- Dataset licenses, attribution and redistribution requirements must be reviewed before public distribution.

## 7. Core Project Features

### 7.1 IoT Container Monitoring

Generate and monitor container-level environmental readings, including temperature, humidity and vibration, with timestamps and simulated route information.

### 7.2 Real-Time Data Streaming

Use Apache Kafka to transport sensor events from the Python simulator to the data ingestion pipeline.

### 7.3 Environmental Anomaly Detection

Identify unusual sensor readings and highlight environmental conditions that may require attention.

### 7.4 Spoilage-Risk Assessment

Develop an explainable risk-scoring mechanism using product-specific reference rules and documented assumptions.

Proposed risk categories:

- Low Risk
- Medium Risk
- High Risk
- Critical Risk

### 7.5 Commodity Price Analysis

Analyse historical commodity prices and identify price trends using available reference data.

### 7.6 Alternative-Market Analysis

Evaluate potential alternative markets using available price information.

Future recommendations should consider transportation costs, route feasibility, delivery time, destination prices and expected product loss.

### 7.7 Interactive Dashboard

Develop an Apache Superset dashboard displaying:

- Container monitoring information.
- Temperature and humidity trends.
- Vibration readings.
- Environmental risk classifications.
- Sensor anomalies.
- Commodity-price trends.
- Alternative-market analysis.
- Important alerts and notifications.

## 8. Project Folder Structure

```text
AtmoSync-MicroClimate-Analytics/
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── simulator/
│   ├── config/
│   ├── sensor_generator.py
│   └── main.py
│
├── kafka/
│   ├── producer.py
│   ├── consumer.py
│   └── topics.md
│
├── snowflake/
│   ├── schemas/
│   └── ingestion/
│
├── dbt/
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/
│
├── analytics/
│   ├── risk_scoring.py
│   └── market_recommendation.py
│
├── dashboard/
│   └── documentation/
│
├── docs/
│   ├── architecture/
│   ├── dataset/
│   ├── setup/
│   ├── daily_tasks/
│   └── meetings/
│
├── reports/
│   ├── figures/
│   └── testing/
│
├── tests/
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Directories and implementation files will be added as their respective development phases begin.

## 9. Team Members and Responsibilities

| Team Member | Role | Responsibilities |
|---|---|---|
| Lav Kumar | Project Coordinator, Documentation and Integration Manager | Project coordination, documentation, integration and workflow management |
| Aditya Singh Bisht | Python IoT Simulator and Apache Kafka Developer | Sensor simulation, Kafka producers, consumers and event streaming |
| Manash Mandal | Snowflake, dbt and SQL Data Engineer | Warehouse setup, SQL transformations, dbt models and data validation |
| ANKUSH PAL | Apache Superset, BI Dashboard and Alerts Developer | Dashboard development, visualization, monitoring and alerts |

## 10. Development Roadmap

| Phase | Development activity | Status |
|---|---|---|
| 1 | Repository and project setup | In progress |
| 2 | Dataset exploration and documentation | Pending |
| 3 | Data cleaning and preprocessing | Pending |
| 4 | Python IoT simulator | Pending |
| 5 | Apache Kafka streaming pipeline | Pending |
| 6 | Snowflake integration | Pending |
| 7 | dbt transformations and testing | Pending |
| 8 | Risk-scoring analytics | Pending |
| 9 | Alternative-market analysis | Pending |
| 10 | Superset dashboard and alerts | Pending |
| 11 | End-to-end integration testing | Pending |
| 12 | Final documentation and presentation | Pending |

## 11. GitHub Collaboration Workflow

The project will use a branch-based development workflow.

| Branch | Assigned member |
|---|---|
| `main` | Stable integrated project |
| `lav-kumar` | Lav Kumar |
| `ankush-pal` | ANKUSH PAL |
| `manash` | Manash Mandal |

Aditya's branch assignment will be coordinated with the team before development.

### Development Process

1. Each member works on their assigned branch.
2. Changes are committed with meaningful commit messages.
3. Completed work is pushed to GitHub.
4. Pull requests are created for integration.
5. Changes are reviewed before merging into `main`.
6. Documentation is updated alongside implementation.

### Git Commands

```bash
# Check current branch
git branch

# Switch to your branch
git switch lav-kumar

# Check changes
git status

# Stage changes
git add .

# Commit changes
git commit -m "Describe your changes"

# Push changes
git push origin lav-kumar
```

## 12. Security and Data Management

- Never commit passwords, access tokens, API keys or private SSH keys.
- Keep environment variables in `.env` files.
- Maintain `.env.example` without real credentials.
- Keep virtual environments out of version control.
- Preserve original source datasets.
- Document data sources, licenses and assumptions.
- Store generated and processed datasets separately from raw data.

## 13. Current Project Status

**Current stage: Initial repository setup and dataset preparation.**

Current completed activities:

- [x] Created GitHub repository.
- [x] Established four project branches.
- [x] Cleaned previous branch history.
- [x] Restored the five initial dataset files locally.
- [x] Created `.gitignore`.
- [ ] Finalize and push updated README.
- [ ] Commit initial datasets to `lav-kumar`.
- [ ] Complete dataset exploration and data dictionary.
- [ ] Begin simulator and streaming development.

Implementation components will only be marked complete after they have been developed and tested.

## 14. Expected Project Outcome

The expected outcome is an integrated analytics prototype demonstrating how environmental sensor telemetry, cold-chain reference data and commodity-price information can be combined to monitor container conditions, assess potential spoilage risks and support alternative-market decisions.

The project will demonstrate practical applications of IoT simulation, real-time data streaming, cloud data warehousing, data transformation, analytics and business intelligence.

---

**Project Name:** AtmoSync – Micro-Climate Arbitrage Analytics

**Repository:** [AtmoSync – GitHub](https://github.com/lavk7766/AtmoSync---Micro-Climate-Arbitrage-Analytics)

**Team Size:** 4 Members

**Project Type:** IoT, Data Engineering, Analytics and Business Intelligence