-- AtmoSync Container Telemetry: Data Profiling
-- Source: ATMOSYNC.STAGING.STG_CONTAINER_TELEMETRY
-- Verified: 2026-11-18
-- Read-only query.

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT CONTAINER_ID) AS distinct_containers,
    COUNT(DISTINCT EVENT_ID) AS distinct_event_ids,
    COUNT_IF(CONTAINER_ID IS NULL) AS null_container_ids,
    COUNT_IF(EVENT_TS IS NULL) AS null_event_timestamps,
    MIN(EVENT_TS) AS first_event_ts,
    MAX(EVENT_TS) AS last_event_ts,
    MIN(TEMPERATURE_C) AS min_temperature_c,
    MAX(TEMPERATURE_C) AS max_temperature_c,
    ROUND(AVG(TEMPERATURE_C), 2) AS avg_temperature_c,
    COUNT_IF(TEMPERATURE_C IS NULL) AS null_temperature,
    MIN(HUMIDITY_PCT) AS min_humidity_pct,
    MAX(HUMIDITY_PCT) AS max_humidity_pct,
    ROUND(AVG(HUMIDITY_PCT), 2) AS avg_humidity_pct,
    COUNT_IF(HUMIDITY_PCT IS NULL) AS null_humidity,
    MIN(VIBRATION_G) AS min_vibration_g,
    MAX(VIBRATION_G) AS max_vibration_g,
    ROUND(AVG(VIBRATION_G), 3) AS avg_vibration_g,
    COUNT_IF(VIBRATION_G IS NULL) AS null_vibration
FROM STAGING.STG_CONTAINER_TELEMETRY;
