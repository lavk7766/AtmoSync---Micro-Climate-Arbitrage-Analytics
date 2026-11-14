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

Status: Proposed, awaiting project coordinator approval.
All formulas, tolerances and risk thresholds are prototype
assumptions, not validated food-safety standards.

### 2.1 Spoilage calculation

One row per container, using telemetry in chronological order.

1. initial_shelf_life_hours = shelf_life_min_hours
2. temp_excess_c = greatest(temperature_c - recommended_temp_max_c, 0)
3. aging_factor = power(2, temp_excess_c / 10)
4. interval_hours = elapsed seconds between readings / 3600
5. effective_aging_hours = interval_hours * aging_factor
6. cumulative_aged_hours = sum(effective_aging_hours)
7. remaining_shelf_life_hours = greatest(
   initial_shelf_life_hours - cumulative_aged_hours, 0)
8. remaining_shelf_life_pct =
   remaining_shelf_life_hours / initial_shelf_life_hours * 100

### 2.2 Aging factor assumptions

- Normal storage conditions: aging factor = 1.
- Temperature 10 C above the recommended maximum: factor = 2.
- Temperature 20 C above the recommended maximum: factor = 4.
- The model assumes full reference shelf life at the first reading.
- The factor of 2 per 10 C is a prototype assumption.
- Humidity and low-temperature excursions are reported separately
  and do not directly modify the aging factor in version 1.
- The staging reference model must expose shelf_life_min_hours
  before implementation.

### 2.3 Risk classification

| Remaining shelf life | Risk level |
|---|---|
| Above 50% | NORMAL |
| Above 25% and up to 50% | WARNING |
| 25% or below | HIGH_RISK |

These thresholds require coordinator approval.
Excursion percentages are separate diagnostic indicators.

### 2.4 Temperature and humidity excursions

An excursion occurs when a measurement falls outside the
product-specific recommended range.

| Excursion | Continuous duration | Alert |
|---|---|---|
| Temperature | 5 minutes | WARNING |
| Temperature | 30 minutes | PROLONGED_EXCURSION |
| Humidity | 15 minutes | WARNING |
| Humidity | 60 minutes | PROLONGED_EXCURSION |

All duration thresholds are proposed assumptions.

- Expected telemetry interval: 5 seconds.
- Maximum valid interval: 15 seconds, subject to simulator confirmation.
- Intervals above 15 seconds are unknown exposure periods.
- Missing readings must not be treated as normal conditions.
- Missing readings and excessive gaps break continuous excursion tracking.
- Report observed exposure and unknown exposure separately.
- Incomplete coverage makes the shelf-life estimate uncertain.
- Proposed temperature tolerance: 0.5 C for zero-width ranges.
- Sensor tolerance and accelerated simulation timing require approval.
- Use the previous valid temperature reading to calculate aging
  for each valid interval.
- Intervals with missing temperature or gaps above 15 seconds
  must be excluded from observed aging and reported as unknown.
- Incomplete exposure coverage produces a provisional shelf-life
  estimate. Data-quality eligibility requires coordinator approval.

### 2.5 Example calculation

Product: Tomato
Recommended temperature: 13-15 C
Initial reference shelf life: 96 hours
Observed temperature: 25 C
Observed exposure duration: 12 hours

Temperature excess = 25 - 15 = 10 C
Aging factor = 2^(10/10) = 2
Effective aging = 12 * 2 = 24 hours
Remaining shelf life = 96 - 24 = 72 hours
Remaining shelf life percentage = 75%
Shelf-life risk = NORMAL

A prolonged temperature excursion alert is also active.

### 2.6 Expected output columns

- container_id
- product_name
- latest_temperature_c
- latest_humidity_pct
- initial_shelf_life_hours
- cumulative_aged_hours
- remaining_shelf_life_hours
- remaining_shelf_life_pct
- risk_level
- temperature_excursion_minutes
- humidity_excursion_minutes
- temperature_alert
- humidity_alert
- unknown_exposure_hours
- data_quality_status
- latitude
- longitude
- last_reading_at
- is_assumption_based



## 3. mart_arbitrage (proposed logic)

Status: Proposed, awaiting project coordinator approval.

### 3.1 Objective

Recommend an alternative market when a container is at high
spoilage risk and rerouting can reduce potential financial loss.

### 3.2 Required inputs

- Container ID and product name
- Current latitude and longitude
- Remaining shelf life from mart_spoilage_risk
- Product quantity in kilograms
- Planned destination
- Candidate markets and their coordinates
- Product price at each market
- Estimated transport speed and transport cost

### 3.3 Recommendation logic

1. Select containers classified as HIGH_RISK.
2. Identify candidate markets that accept the container's product.
3. Calculate distance using the Haversine formula.
4. Estimate travel time:

   travel_hours = distance_km / average_speed_kmph

5. Estimate remaining shelf life at arrival:

   remaining_at_arrival_hours = greatest(
   remaining_shelf_life_hours -
   travel_hours * expected_aging_factor, 0)

6. Estimate remaining quality at arrival:

   quality_at_arrival = remaining_at_arrival_hours /
   initial_shelf_life_hours

7. Calculate expected net value:

   expected_net_value = product_price_per_kg *
   quantity_kg * quality_at_arrival - transport_cost

8. Compare the expected net value of each reachable
   candidate market with the planned destination.

9. Recommend rerouting only when:

   - Remaining shelf life at arrival is greater than zero.
   - The alternative market has a higher expected net value.
   - Required market, price and transport data are available.
   - Sensor data quality is sufficient for the recommendation.

### 3.4 Example scenario

Illustrative assumptions, not actual market data:

Product: Banana
Quantity: 1000 kg
Remaining shelf life: 4 hours
Initial shelf life: 2352 hours

Planned destination:
- Estimated travel time: 6 hours
- Arrival before estimated spoilage: No

Alternative market:
- Estimated travel time: 2 hours
- Arrival before estimated spoilage: Yes
- Expected aging factor during travel: 1
- Remaining shelf life at arrival: 2 hours

Recommendation:
Evaluate the alternative market if its expected net value
is higher than the planned destination.

### 3.5 Assumptions and limitations

- Haversine distance is straight-line distance, not road distance.
- Average travel speed requires coordinator approval.
- Future temperature conditions are assumed, not guaranteed.
- Remaining quality is a simplified shelf-life proxy,
  not a measured product quality score.
- The relationship between remaining quality and selling
  price is a prototype assumption.
- Current commodity price coverage is limited to banana
  and orange.
- Monthly commodity prices are not live local market prices.
- No recommendation is generated for missing prices,
  missing coordinates or insufficient data quality.
- Real candidate markets, local prices and transport costs
  are required for operational recommendations.
- Recommendations are decision support, not automatic
  rerouting instructions or food-safety certification.

### 3.6 Expected output columns

- container_id
- product_name
- risk_level
- remaining_shelf_life_hours
- planned_destination
- recommended_market
- distance_km
- estimated_travel_hours
- remaining_at_arrival_hours
- quality_at_arrival
- expected_net_value
- planned_destination_net_value
- estimated_financial_benefit
- reroute_recommended
- recommendation_reason
- data_quality_status
- is_assumption_based



## 4. Dependencies and approval requirements

| Requirement | Responsible | Status |
|---|---|---|
| Spoilage calculation and aging factor approval | Lav | Pending |
| Risk classification thresholds approval | Lav | Pending |
| Temperature and humidity excursion durations approval | Lav | Pending |
| Sensor tolerance and maximum valid reading interval | Lav and Aditya | Pending |
| Updated simulator telemetry and container metadata | Aditya | Pending confirmation |
| Accelerated simulation and temperature fault scenarios | Aditya | Pending confirmation |
| Expose shelf_life_min_hours in staging model | Manash | Pending |
| Candidate market coordinates and transport costs | Lav | Pending |
| Product price coverage and market price assumptions | Lav | Pending |
| Spoilage and arbitrage mart implementation | Manash | Awaiting approval |
| Dashboard integration | Ankush | Awaiting mart output |

Implementation must follow the approved rules.
All prototype assumptions must be documented.


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

### 6.1 Spoilage-risk tests

- One row per container.
- Container product exists in the spoilage reference.
- Initial shelf life is greater than zero.
- Aging factor is greater than or equal to one.
- Remaining shelf life is not negative.
- Remaining shelf life does not exceed initial shelf life.
- Remaining shelf life percentage is between 0 and 100.
- Risk level matches the approved classification thresholds.
- Missing readings are not treated as normal conditions.
- Excessive timestamp gaps break continuous excursion tracking.
- Temperature and humidity alerts follow approved durations.
- Development placeholder data is clearly identified.

### 6.2 Arbitrage tests

- Market distance is not negative.
- Estimated travel time is not negative.
- Quality at arrival is between 0 and 1.
- No recommendation without valid product prices.
- No recommendation without valid market coordinates.
- No recommendation with insufficient sensor data quality.
- Recommended market is reachable before estimated spoilage.
- Alternative market net value exceeds planned destination net value.
- Maximum one final recommendation per container.

### 6.3 Simulation scenarios

| Scenario | Expected behaviour |
|---|---|
| Normal temperature | Aging factor equals 1 |
| Temperature 10 C above maximum | Aging factor equals 2 |
| Temperature 20 C above maximum | Aging factor equals 4 |
| Prolonged temperature excursion | Temperature alert |
| Prolonged humidity excursion | Humidity alert |
| Missing sensor readings | Data-quality flag |
| Shelf life exhausted | HIGH_RISK |
| Alternative market offers higher net value | Reroute recommendation if all eligibility conditions pass |

All tests are planned and have not yet been executed.


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