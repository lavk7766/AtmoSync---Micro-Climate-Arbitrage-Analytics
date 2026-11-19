# Container Telemetry SQL Evidence

**Verification date:** 18 November 2026
**Database:** AtmoSync Snowflake
**Schema:** ATMOSYNC.STAGING
**Source:** STG_CONTAINER_TELEMETRY

All queries in this directory are read-only and were executed in
Superset SQL Lab against the source view.

## Files

| File | Purpose |
|---|---|
| `container_telemetry_profiling.sql` | Row counts, container counts, timestamp coverage, and sensor measurement statistics |
| `container_timestamp_gap_analysis.sql` | Consecutive-event interval distribution and percentage by gap category |
| `container_timestamp_gap_details.sql` | Container-level details for intervals of 60 seconds or longer |

## Verified profiling results

- Total telemetry rows: 105
- Distinct containers: 5
- Distinct event IDs: 105
- Null container IDs: 0
- Null event timestamps: 0
- Temperature: minimum 2.13°C, maximum 13.40°C, average 6.36°C
- Humidity: minimum 40.23%, maximum 89.99%, average 66.66%
- Vibration: minimum 0.010 g, maximum 0.985 g, average 0.497 g
- Null temperature, humidity, and vibration values: 0

## Verified timestamp-gap results

The 105 rows produce 100 consecutive-event intervals when calculated
independently within each container.

| Gap category | Intervals | Percentage |
|---|---:|---:|
| 5 to below 10 seconds | 90 | 90.00% |
| 1 to 60 minutes | 7 | 7.00% |
| Above 1 hour | 3 | 3.00% |
| Total | 100 | 100.00% |

The seven intervals in the 1-to-60-minute category consist of:
- Two intervals of exactly 60 seconds.
- Five intervals of approximately 44.45 minutes.

The three intervals above one hour are approximately 7 days and
20 hours each.

## Sampling consistency definition

The provisional sampling consistency percentage is:

`Intervals from 5 seconds inclusive to below 10 seconds / all observed intervals * 100`

Verified result: 90 / 100 * 100 = 90%.

The 5-to-below-10-second range is provisional and has not been approved
as the operational telemetry cadence.

## Interpretation limitations

- Sampling consistency is not the same as telemetry completeness.
- Long gaps may represent simulator downtime or an observation-window
  boundary; they are not proof of missing records.
- Estimated missing readings must not be reported as confirmed missing data.
- Final completeness assessment requires an agreed observation window,
  expected sampling cadence, tolerance, and downtime policy.
- No sensor-specific analysis is possible from this view because it
  does not expose a SENSOR_ID column.
- The previous November 14 gap breakdown should be superseded by the
  verified distribution above.

## Reproduction

1. Open Superset SQL Lab.
2. Select the AtmoSync Snowflake database.
3. Execute the relevant SQL file.
4. Compare the output with the verified results documented above.

The SQL files are reconstructed, reproducible evidence queries based
on the verified source schema and live query results. They are not
claimed to be the original historical SQL statements.
