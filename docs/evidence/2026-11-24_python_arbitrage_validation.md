# Python Arbitrage Validation Framework

Date: 24 November 2026
Developer: Aditya
Branch: Aditya-Singh-Bisht
Implementation commit: c551816

## Objective

Added an independent Python validation module implementing the
prototype calculations described in the spoilage-arbitrage design.

## Files

- simulator/arbitrage_validation.py
- tests/test_arbitrage.py

## Functionality tested

1. Haversine straight-line distance calculation.
2. Coordinate validation.
3. Estimated travel-time calculation.
4. Remaining shelf life at market arrival.
5. Quality-at-arrival calculation.
6. Expected net market value.
7. Reroute eligibility conditions.
8. Invalid or missing financial and sensor-quality inputs.

## Test evidence

- Dedicated arbitrage tests: 24 passed.
- Full project test suite: 310 passed.
- Full-suite execution time: 2.89 seconds.
- Python compile check: passed.
- Git whitespace check: passed.

## Limitations

- Haversine calculates straight-line distance, not actual road, rail
  or sea network distance.
- Transport speeds and expected aging factors are supplied inputs.
- The financial calculations use illustrative test values.
- No live commodity prices or candidate-market dataset is connected.
- Sensor data sufficiency is supplied by the caller; this module
  does not establish the team's final eligibility policy.
- This is not a live arbitrage engine and does not execute the dbt
  spoilage or arbitrage models.
- All calculations remain subject to coordinator approval of the
  project's prototype assumptions.

## Git

Implementation commit: c551816
