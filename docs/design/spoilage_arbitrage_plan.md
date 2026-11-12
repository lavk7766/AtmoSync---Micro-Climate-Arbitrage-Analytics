# Spoilage-Risk and Arbitrage Marts: Plan (Manash Mandal)

Status on 12 November 2026: not started. This plan lists the proposed logic, assumptions, dependencies and dates. The model logic needs the Team Lead's approval before it is built.

## 1. Inputs and what is missing
| Input | Where | Status |
|---|---|---|
| Telemetry (temperature, humidity, latitude, longitude) | stg_container_telemetry | Exists; latitude and longitude come from the simulator update (Aditya) |
| Product per container | none | Missing: telemetry events carry no product. Needs a container list (container_id, product_name) or filled RAW_CONTAINER_METADATA |
| Spoilage thresholds and shelf life per product | stg_product_spoilage_reference | Exists (20 products) |
| Prices | int_commodity_price_latest | Exists for banana (Europe, US) and orange only; monthly, USD per kg |
| Candidate markets with coordinates | none | Missing |
| Quantity, planned destination, transport cost | RAW_CONTAINER_METADATA, RAW_ROUTE_INFO | Tables exist, no data |

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
| GPS check against real simulator events | 1 day after Aditya's push | shifts with his push |
| mart_spoilage_risk version 1 | 18 Nov | shifts one day per day of delay |
| mart_arbitrage version 1 | 22 Nov | shifts one day per day of delay |
Week 3 of the plan runs 19 to 25 November and the mid-review is 27 to 30 November.

## 6. Tests planned
Spoilage risk: one row per container, risk_level in the allowed set, remaining_shelf_life_hours not NULL for mapped products, every container has a product. Arbitrage: one recommendation per container, distance not negative, no recommendation without a price.