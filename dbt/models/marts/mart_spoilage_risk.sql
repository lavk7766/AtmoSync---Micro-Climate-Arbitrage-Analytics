
{{ config(materialized='table') }}

with metadata as (

    select
        container_id,
        product_name,
        source_type,
        row_number() over (
            partition by container_id
            order by ingested_at desc
        ) as rn
    from {{ ref('stg_container_metadata') }}

),

products as (

    select
        product_name,
        recommended_temp_min_c,
        recommended_temp_max_c,
        humidity_min_pct,
        shelf_life_min_hours
    from {{ ref('stg_product_spoilage_reference') }}

),

readings as (

    select
        upper(trim(t.container_id)) as container_id,
        t.event_ts,
        t.event_id,
        t.temperature_c,
        t.humidity_pct,
        t.latitude,
        t.longitude,
        m.product_name,
        m.source_type as metadata_source_type,
        p.recommended_temp_min_c,
        p.recommended_temp_max_c,
        p.humidity_min_pct,
        p.shelf_life_min_hours
    from {{ ref('stg_container_telemetry') }} t

    inner join metadata m
        on upper(trim(t.container_id)) = m.container_id
       and m.rn = 1

    inner join products p
        on m.product_name = p.product_name

    where t.event_ts is not null
      and t.temperature_c is not null
      and p.shelf_life_min_hours > 0

),

ordered_readings as (

    select
        *,
        lead(event_ts) over (
            partition by container_id
            order by event_ts, event_id
        ) as next_event_ts
    from readings

),

intervals as (

    select
        *,
        datediff(
            'second',
            event_ts,
            next_event_ts
        ) as interval_seconds,

        greatest(
            temperature_c - recommended_temp_max_c,
            0
        ) as temp_excess_c,

        power(
            2,
            greatest(
                temperature_c - recommended_temp_max_c,
                0
            ) / 10.0
        ) as aging_factor
    from ordered_readings

),

calculated as (

    select
        *,
        case
            when interval_seconds between 1 and 15
            then interval_seconds / 3600.0
            else 0
        end as observed_interval_hours,

        case
            when interval_seconds > 15
            then interval_seconds / 3600.0
            else 0
        end as unknown_interval_hours
    from intervals

),

aggregated as (

    select
        container_id,
        max(product_name) as product_name,
        max(shelf_life_min_hours) as initial_shelf_life_hours,

        sum(
            observed_interval_hours * aging_factor
        ) as cumulative_aged_hours,

        sum(unknown_interval_hours) as unknown_exposure_hours,

        count(*) as reading_count,

        max(case
            when metadata_source_type = 'dev_placeholder'
            then 1 else 0
        end) as is_dev_placeholder

    from calculated
    group by container_id

),

latest as (

    select
        container_id,
        temperature_c as latest_temperature_c,
        humidity_pct as latest_humidity_pct,
        latitude,
        longitude,
        event_ts as last_reading_at
    from readings

    qualify row_number() over (
        partition by container_id
        order by event_ts desc, event_id desc
    ) = 1

),

remaining as (

    select
        a.*,
        l.latest_temperature_c,
        l.latest_humidity_pct,
        l.latitude,
        l.longitude,
        l.last_reading_at,

        greatest(
            a.initial_shelf_life_hours -
            a.cumulative_aged_hours,
            0
        ) as remaining_shelf_life_hours

    from aggregated a
    join latest l
        on a.container_id = l.container_id

)

select
    container_id,
    product_name,
    latest_temperature_c,
    latest_humidity_pct,
    initial_shelf_life_hours,
    cumulative_aged_hours,
    remaining_shelf_life_hours,

    remaining_shelf_life_hours
        / nullif(initial_shelf_life_hours, 0)
        * 100 as remaining_shelf_life_pct,

    case
        when remaining_shelf_life_hours
             / nullif(initial_shelf_life_hours, 0) * 100 <= 25
            then 'HIGH_RISK'
        when remaining_shelf_life_hours
             / nullif(initial_shelf_life_hours, 0) * 100 <= 50
            then 'WARNING'
        else 'NORMAL'
    end as risk_level,

    unknown_exposure_hours,
    reading_count,

    case
        when is_dev_placeholder = 1
            then 'DEV_PLACEHOLDER'
        when reading_count < 2
            then 'INSUFFICIENT_READINGS'
        when unknown_exposure_hours > 0
            then 'INCOMPLETE_COVERAGE'
        else 'OBSERVED'
    end as data_quality_status,

    latitude,
    longitude,
    last_reading_at,
    true as is_assumption_based

from remaining
