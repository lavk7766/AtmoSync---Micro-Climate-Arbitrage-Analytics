-- AtmoSync Container Telemetry: Detailed Timestamp Gap Investigation
-- Source: ATMOSYNC.STAGING.STG_CONTAINER_TELEMETRY
-- Verified: 2026-11-18
-- Returns intervals of 60 seconds or longer.
-- Read-only query.

WITH ordered_events AS (
    SELECT
        CONTAINER_ID,
        EVENT_TS,
        LAG(EVENT_TS) OVER (
            PARTITION BY CONTAINER_ID
            ORDER BY EVENT_TS
        ) AS PREVIOUS_EVENT_TS
    FROM STAGING.STG_CONTAINER_TELEMETRY
)
SELECT
    CONTAINER_ID,
    PREVIOUS_EVENT_TS,
    EVENT_TS,
    ROUND(
        DATEDIFF(
            MILLISECOND,
            PREVIOUS_EVENT_TS,
            EVENT_TS
        ) / 1000.0,
        3
    ) AS GAP_SECONDS,
    ROUND(
        DATEDIFF(
            MILLISECOND,
            PREVIOUS_EVENT_TS,
            EVENT_TS
        ) / 60000.0,
        3
    ) AS GAP_MINUTES
FROM ordered_events
WHERE PREVIOUS_EVENT_TS IS NOT NULL
  AND DATEDIFF(
      MILLISECOND,
      PREVIOUS_EVENT_TS,
      EVENT_TS
  ) >= 60000
ORDER BY GAP_SECONDS DESC;
