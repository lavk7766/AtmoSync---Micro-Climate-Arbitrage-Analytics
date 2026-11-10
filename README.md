# AtmoSync — Micro-Climate Arbitrage Analytics

## 1. Project Overview

AtmoSync is a collaborative data engineering and analytics project focused on monitoring environmental conditions during transportation and identifying opportunities related to climate-sensitive commodity logistics.

The project combines IoT sensor telemetry, geographic location tracking, commodity price information and analytical workflows to investigate environmental risks, potential spoilage and micro-climate arbitrage opportunities.

## 2. Project Objectives

- Monitor temperature, humidity and vibration conditions during simulated transportation.
- Generate and validate container-level IoT telemetry.
- Track container movement using geographic coordinates and transport routes.
- Stream sensor telemetry through Apache Kafka.
- Explore environmental spoilage risks and commodity price differences.
- Develop analytical outputs and dashboards to support data-driven decisions.

## 3. Available Datasets

The repository contains the following supporting datasets:

| Dataset | Description |
|---|---|
| Raw sensor data | Original temperature and humidity recordings from nine sensors |
| Preprocessed sensor data | Processed sensor measurements with aligned timestamps |
| Sensor overview | Sensor-level statistics and recording metadata |
| Commodity price data | Historical monthly commodity prices |
| Household cold-chain data | Supporting cold-chain research dataset |

### Sensor Dataset Details

The supplied sensor dataset contains nine sensor streams, identified as SENSOR01 through SENSOR09.

The measured variables include:

- Temperature, recorded in degrees Celsius (°C).
- Relative humidity, recorded as a percentage (%).
- Date and time of each measurement.

The most common sampling interval observed across the supplied sensor recordings is five seconds.

**Note:** Vibration measurements are not present in the inspected raw or preprocessed sensor CSV files. Vibration readings are generated separately as synthetic telemetry by the IoT simulator.

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Simulator development and data processing |
| Pandas and NumPy | Data manipulation and numerical operations |
| Apache Kafka | Telemetry streaming and message processing |
| Snowflake | Cloud data storage and analytics |
| dbt | Data transformation |
| Apache Superset | Dashboarding and visualization |
| Git and GitHub | Version control and collaborative development |

## 5. Project Workflow

1. Sensor dataset inspection and analysis.
2. Synthetic IoT telemetry generation.
3. Sensor event validation.
4. Kafka-based telemetry publishing and consumption.
5. Data ingestion and storage.
6. Environmental risk and spoilage analysis.
7. Commodity price and arbitrage analysis.
8. Dashboard development and reporting.

## 6. Collaborative Development

AtmoSync is developed collaboratively, with team members contributing to Python simulation, data engineering, Snowflake integration, analytics and dashboard development.

Project source code, documentation, automated tests and supporting evidence are maintained in this repository.

## 7. Repository Structure

The project is organized into dedicated directories for:

- `data/` — Supporting datasets.
- `simulator/` — IoT simulation components.
- `kafka_client/` — Kafka producer and consumer components.
- `ingestion/` — Data ingestion workflows.
- `analytics/` — Analytical processing.
- `snowflake/` — Database and schema scripts.
- `tests/` — Automated tests.
- `docs/` — Project documentation and technical evidence.
- `dashboard/` — Dashboard requirements and related materials.