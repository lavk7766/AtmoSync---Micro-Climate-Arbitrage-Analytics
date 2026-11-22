# Product-Aware Simulator and Kafka Integration Evidence

**Project:** AtmoSync – Micro-Climate Arbitrage Analytics
**Execution date:** 20 November 2026
**Branch:** Aditya-Singh-Bisht
**Status:** Local integration verification passed; coordinator approval pending.

## 1. Objective

Verify the Python simulator using container metadata and product spoilage
reference data, demonstrate scheduled temperature fault injection, publish
telemetry to Kafka, consume the published events, and validate the events
using Manash's Kafka-to-Snowflake loader in dry-run mode.

## 2. Reference Data

The following files were copied locally from `origin/manash`:

- `data/reference/container_metadata.csv`
- `data/reference/product_spoilage_reference.csv`

Source commits:

- `4213ecc` – Add validated product spoilage reference CSV for review.
- `7e28911` – Add validated container metadata CSV for coordinator review.

Reported validation results:

- Container records: 5
- Unique containers: 5
- Product reference records: 20
- Unique products: 20
- Container metadata validation errors: 0
- Product reference validation errors: 0
- All five container products matched to a product reference.

**Approval qualification:** The container metadata review document
states that coordinator approval is pending. The product reference
document identifies its thresholds as unverified prototype assumptions.
These values are used for integration testing and are not represented
as independently verified food-safety limits.

## 3. Container-to-Product Mapping

| Container | Product | Quantity | Origin | Destination | Temperature reference |
|---|---|---:|---|---|---|
| CONT001 | Apple | 1000 kg | Delhi | Lucknow | -1 to 4 C |
| CONT002 | Banana | 1000 kg | Mumbai | Solapur | 13 to 14 C |
| CONT003 | Orange | 800 kg | Bengaluru | Kurnool | 3 to 9 C |
| CONT004 | Tomato | 500 kg | Kolkata | Patna | 13 to 15 C |
| CONT005 | Strawberry | 300 kg | Mumbai | Mangaluru | 0 to 0 C |

Local loader verification:

- Container metadata records loaded: 5
- Product reference records loaded: 20
- Active simulator containers: 5
- Successfully matched containers: 5

## 4. Python Test Results

Command:

`python -m pytest -q`

Result:

`163 passed in 2.13s`

Exit code: 0.

## 5. Temperature Fault Injection

Configured target: CONT001 (Apple)

- Recommended maximum temperature: 4.0 C
- Fault offset: +5.0 C
- Injected temperature: 9.0 C
- Scheduled start delay: 5 seconds
- Scheduled duration: 30 seconds

Observed fault window (UTC):

`2026-11-20T07:16:16.369630Z` to
`2026-11-20T07:16:46.369630Z`

The event at Kafka offset 5 had:

- Event ID: `46314320-04d0-4c71-ac8e-e0a484b1f891`
- Container: CONT001
- Timestamp: `2026-11-20T07:16:16.557630Z`
- Temperature: 9.0 C
- Latitude: 28.61397
- Longitude: 77.20789

The event timestamp falls inside the configured fault window.
The event passed the Python event validator and was published to Kafka.

## 6. Kafka Producer Verification

Temporary test topic:

`atmosync_product_aware_20261120`

Execution used the existing simulator with a temporary topic override
and an event limit of 10.

Results:

- Events generated: 10
- Events published: 10
- Kafka partition: 0
- Kafka offsets: 0 through 9
- Simulator exit code: 0

Two events were generated for each of the five containers.

## 7. Kafka Consumer Verification

The project's Python consumer was run against the temporary
product-aware topic using a separate consumer group.

Results:

- Correct topic consumed: yes
- Messages received: 10
- Messages processed: 10
- Messages rejected: 0

All ten consumed event IDs were reconciled with the producer output.
The CONT001 event containing the 9.0 C injected temperature was
successfully consumed.

## 8. Kafka-to-Snowflake Loader Dry-Run

Manash's isolated loader audit copy was used in dry-run mode against
the same temporary Kafka topic.

Results:

- Kafka topic subscription: successful
- Consumer group: `atmosync-snowflake-loader`
- Assigned partition: 0
- Valid events: 10
- Rejected events: 0
- Total loaded/validated in dry-run: 10

Dry-run mode performed validation only. It did not insert records
into Snowflake.

## 9. Route Qualification

CONT001 uses the generated OpenStreetMap-derived road route JSON.

CONT002 through CONT005 use the waypoint definitions in
`simulator/routes.py` and location interpolation. These should be
described as illustrative waypoint routes, not verified full road,
rail or maritime network routes.

## 10. Outstanding Work and Limitations

1. Obtain Lav's approval of the container-to-product assignments.
2. Confirm the product reference values and their intended use.
3. Complete actual Snowflake authentication and insertion.
4. Execute dbt models and tests against the live Snowflake environment.
5. Complete the final integration handoff.

The Snowflake connection check was blocked because neither the main
project directory nor the isolated audit directory contained the
required `.env` file. The loader raised `KeyError: SNOWFLAKE_ACCOUNT`.

No live Snowflake insertion was performed.

## 11. Conclusion

The local product-aware simulator-to-Kafka integration was verified:

- Reference data loaded successfully.
- All five containers matched to their products.
- 163 Python tests passed.
- Ten product-aware events were published.
- The same ten events were consumed successfully.
- The scheduled 9.0 C Apple temperature excursion was published
  and consumed.
- The Snowflake loader accepted all ten events in dry-run mode.

Coordinator approval and live Snowflake integration remain pending.

## 12. Supplemental Verification — 21 November 2026

### 12.1 Independent Reference CSV Validation

Manash's original validation scripts were retrieved from `origin/manash`
and executed against temporary copies of the local reference CSV files.

Container metadata validator:
- Total containers: 5
- Unique containers: 5
- Available product references: 20
- Validation errors: 0
- Exit code: 0
- Result: PASSED

Product reference validator:
- Total products: 20
- Unique products: 20
- Validation errors: 0
- Exit code: 0
- Result: PASSED

Both scripts ran successfully without modifying the original CSV files.

Coordinator approval remains pending.

### 12.2 Independent Route-to-Metadata Audit

A separate read-only route audit compared the five container metadata
records against the route definitions in `simulator/routes.py`.

| Container | Route | Mode | Waypoints | Calculated distance |
|---|---|---|---:|---:|
| CONT001 | Delhi to Lucknow | Road | 4874 | 534.01 km |
| CONT002 | Mumbai to Solapur | Rail | 3 | 357.01 km |
| CONT003 | Bengaluru to Kurnool | Road | 3 | 678.79 km |
| CONT004 | Kolkata to Patna | Rail | 3 | 575.06 km |
| CONT005 | Mumbai to Mangaluru | Sea | 6 | 906.50 km |

Results:
- Metadata container IDs matched all five route definitions.
- Origin and destination assignments matched.
- All five transport modes were configured.
- Route coordinates passed geographic range checks.
- Starting and ending coordinate gaps were 0.00 km for all five routes.
- Initial simulator positions matched route starting coordinates.
- All five calculated route distances were positive and finite.

Result: PASSED.

Route qualification:
CONT001 uses a generated OpenStreetMap-derived road route.
CONT002 through CONT005 use illustrative waypoint routes and
straight-line interpolation. Their calculated distances are not
verified network travel distances.

### 12.3 Supplemental Conclusion

The reference-data validation and route-to-metadata consistency
checks passed independently.

The reference CSVs remain subject to coordinator approval.
No live Snowflake insertion or dbt execution was performed.
