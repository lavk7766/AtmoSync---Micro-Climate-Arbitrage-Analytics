# Container Metadata — Coordinator Review

**Date:** 19 November 2026

**Project:** AtmoSync – Micro-Climate Arbitrage Analytics

**Status:** Validation passed; coordinator approval pending.

## 1. Objective

Prepare container metadata connecting simulated sensor telemetry with product spoilage reference values, shipment quantities and route information.

## 2. Proposed Container Assignments

| Container | Product | Quantity (kg) | Origin | Destination | Mode |
|---|---|---:|---|---|---|
| CONT001 | Apple | 1000 | Delhi | Lucknow | Road |
| CONT002 | Banana | 1000 | Mumbai | Solapur | Rail |
| CONT003 | Orange | 800 | Bengaluru | Kurnool | Road |
| CONT004 | Tomato | 500 | Kolkata | Patna | Rail |
| CONT005 | Strawberry | 300 | Mumbai | Mangaluru | Sea |

## 3. Data Sources and Decisions

- Route endpoints are based on the existing simulator route configurations.
- CONT001 uses the existing OpenStreetMap-derived road route.
- CONT002–CONT005 use illustrative simulator waypoints.
- Product names match the product spoilage reference CSV.
- CONT001's proposed product and quantity follow the simulator test fixture.
- Other product assignments and quantities are proposed synthetic values.
- Banana and Orange were included to support testing with available commodity price series.
- All quantities are expressed in kilograms.
- All records use source_type = synthetic_simulated.

## 4. Validation Results

- Total containers: 5
- Unique container IDs: 5
- Available reference products: 20
- Duplicate container IDs: 0
- Invalid quantities: 0
- Unknown products: 0
- Configured route mismatches: 0
- Validation errors: 0
- Result: PASSED

## 5. Supporting Files

- data/reference/container_metadata.csv
- data/reference/product_spoilage_reference.csv
- scripts/validate_container_metadata.py
- docs/evidence/2026-11-19_container_metadata_validation.txt

## 6. Approval and Limitations

The CSV conforms to the required simulator metadata structure and Snowflake reference table schema.

The product assignments and shipment quantities remain proposals until approved by the project coordinator. Passing validation confirms structural consistency and matching against configured route endpoints, not real shipment accuracy.

Actual CSV-backed simulator execution, Kafka integration and Snowflake ingestion remain to be verified.

The proposed assignments must not be presented as approved canonical data until coordinator approval is received.