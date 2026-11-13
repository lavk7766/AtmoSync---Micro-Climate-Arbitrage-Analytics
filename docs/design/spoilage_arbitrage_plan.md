# Spoilage-Risk and Arbitrage Marts: Plan (Manash Mandal)

Status on 13 November 2026: metadata staging model and validation completed; spoilage-risk and arbitrage marts not started. The metadata schema remains proposed and requires team approval. 

## 1. Inputs and what is missing
| Input | Where | Status |
|---|---|---|
| Telemetry (temperature, humidity, latitude, longitude) | stg_container_telemetry | Exists. Aditya's simulator branch defines all nine event fields, including latitude and longitude (checked 13 Nov); not yet tested end to end with my loader |
| Product per container | stg_container_metadata | Staging model created and dbt run successful. One DEV_PLACEHOLDER row exists in Snowflake for development validation. Product spelling still needs team agreement: metadata example says "Tomatoes", spoilage CSV says "Tomato" |

| Spoilage thresholds and shelf life per product | stg_product_spoilage_reference | Exists (20 products) |
| Prices | int_commodity_price_latest | Exists for banana (Europe, US) and orange only; monthly, USD per kg |
| Candidate markets with coordinates | none | Missing. Only one route file exists (CONT001, Delhi to Lucknow via Agra, 533.88 km, about 6.6 hours) |
| Quantity, planned destination, transport cost | RAW_CONTAINER_METADATA, RAW_ROUTE_INFO | Metadata table has one development placeholder row; real container metadata and route information are still missing |

## 2. mart_spoilage_risk (proposed logic)
One row per container, from its readings in time order:
1. temp_excess_c = greatest(temperature_c - recommended_temp_max_c, 0)
2. aging_factor = 2 ^ (temp_excess_c / 10). The factor 2 per 10 C is an assumption to be confirmed.
3. interval_hours = hours since the previous reading of the same container
4. aged_hours = sum of interval_hours x aging_factor since the first reading
5. remaining_shelf_life_hours = shelf_life_min_hours - aged_hours (the conservative shelf life)
6. risk_level from remaining_shelf_life_hours / shelf_life_min_hours: above 50% low, 25 to 50% medium, 10 to 25% high, below 10% critical (thresholds are assumptions)
Also reported: humidity outside the recommended range, and temperature below the recommended minimum (chilling), both as flags.
Assumed values are marked in the model and in the output as assumption.

## 3. mart_arbitrage (proposed logic)
For each container at risk (high or critical) and each candidate market for its product:
1. distance_km: haversine distance from the container's current latitude and longitude to the market
2. travel_hours = distance_km / assumed average speed
3. arrives_in_time = travel_hours less than remaining_shelf_life_hours
4. expected_value = price per kg x quantity x remaining quality at arrival, minus transport cost
5. reroute_recommended when the best market that can be reached in time has a higher expected value than the planned destination
Limit: prices exist only for banana and orange, and are monthly, so arbitrage results for other products stay empty until the price decision is made.

## 4. Dependencies
| Needed | From | Needed by |
|---|---|---|
| Updated simulator events with latitude and longitude | Aditya | 14 Nov |
| Container list with product names, spelled as in the spoilage reference CSV | Aditya | 14 Nov |
| Approval of the spoilage logic, the 2 per 10 C factor and the risk thresholds | Lav | 14 Nov |
| Candidate markets with coordinates, quantity and transport cost per container | Lav | 17 Nov |
| Decision for the 18 products without a price (second source, assumed prices, or banana and orange only) | Lav | 17 Nov |

## 5. Expected completion
| Item | Date | If a dependency is late |
|---|---|---|
| GPS validation in the loader and dbt tests | 12 Nov (done, see evidence) | none |
| Container metadata staging model and tests | 13 Nov (done; 11 dbt models passed, 57 tests passed, 1 intentional warning) | none |
| GPS check against real simulator events | 1 day after Aditya's push | shifts with his push |
| mart_spoilage_risk version 1 | 18 Nov | shifts one day per day of delay |
| mart_arbitrage version 1 | 22 Nov | shifts one day per day of delay |
Week 3 of the plan runs 19 to 25 November and the mid-review is 27 to 30 November.

Open point: the only route file (CONT001) takes about 6.6 hours, while products such as tomato last 96 to 168 hours in the spoilage reference. With a real-time simulation, no container would approach spoilage during one trip. To show a spoilage alert in the demo, the simulator needs a time-acceleration factor, longer routes or injected temperature faults. To agree with Aditya and Lav.

## 6. Tests planned
Spoilage risk: one row per container, risk_level in the allowed set, remaining_shelf_life_hours not NULL for mapped products, every container has a product. Arbitrage: one recommendation per container, distance not negative, no recommendation without a price.

## 7. Container metadata staging validation (13 November)

- Registered RAW_CONTAINER_METADATA as a dbt source.
- Created stg_container_metadata to standardize container IDs, product names, quantity units and text fields.
- Added YAML tests for required fields and unique container IDs.
- Added a positive-quantity singular SQL test.
- Added a warning-level SQL test for development placeholder records.
- dbt run: PASS=11, WARN=0, ERROR=0.
- dbt test: PASS=57, WARN=1, ERROR=0.
- The single warning is expected because the DEV_PLACEHOLDER record is still present.
- Evidence: docs/evidence/2026-11-13_dbt_run.txt and docs/evidence/2026-11-13_dbt_test.txt.
- The placeholder is for development validation only and must not be treated as real shipment data.