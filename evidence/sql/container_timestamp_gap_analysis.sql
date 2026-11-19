-- AtmoSync Container Telemetry: Timestamp Gap Analysis
-- Source: ATMOSYNC.STAGING.STG_CONTAINER_TELEMETRY
-- Verified: 2026-11-18
-- Gaps are calculated between consecutive EVENT_TS values per container.
-- Sampling consistency uses the provisional 5-to-below-10-second range.
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
),
intervals AS (
    SELECT
        DATEDIFF(
            MILLISECOND,
            PREVIOUS_EVENT_TS,
            EVENT_TS
        ) / 1000.0 AS GAP_SECONDS
    FROM ordered_events
    WHERE PREVIOUS_EVENT_TS IS NOT NULL
),
bucketed AS (
    SELECT
        CASE
            WHEN GAP_SECONDS < 5 THEN 'Below 5 seconds'
            WHEN GAP_SECONDS < 10 THEN '5 to below 10 seconds'
            WHEN GAP_SECONDS < 60 THEN '10 to below 60 seconds'
            WHEN GAP_SECONDS <= 3600 THEN '1 to 60 minutes'
            ELSE 'Above 1 hour'
        END AS GAP_CATEGORY,
        CASE
            WHEN GAP_SECONDS < 5 THEN 1
            WHEN GAP_SECONDS < 10 THEN 2
            WHEN GAP_SECONDS < 60 THEN 3
            WHEN GAP_SECONDS <= 3600 THEN 4
            ELSE 5
        END AS SORT_ORDER
    FROM intervals
)
SELECT
    GAP_CATEGORY,
    COUNT(*) AS INTERVAL_COUNT,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS PERCENTAGE
FROM bucketed
GROUP BY GAP_CATEGORY, SORT_ORDER
ORDER BY SORT_ORDER;
