with source as (

    select *
    from {{ source('raw', 'raw_container_telemetry') }}
    where event_payload:container_id is not null

),

deduped as (

    select
        *,
        row_number() over (
            partition by event_payload:event_id::string
            order by ingested_at desc
        ) as rn
    from source

)

select
    event_payload:event_id::string       as event_id,
    event_payload:container_id::string   as container_id,
    event_payload:timestamp::timestamp_tz as event_ts,
    event_payload:temperature_c::float   as temperature_c,
    event_payload:humidity_pct::float    as humidity_pct,
    event_payload:vibration_g::float     as vibration_g,
    event_payload:latitude::float        as latitude,
    event_payload:longitude::float       as longitude,
    event_payload:source_type::string    as source_type,
    kafka_topic,
    kafka_partition,
    kafka_offset,
    ingested_at
from deduped
where rn = 1