with source as (

    select *
    from {{ source('raw_sensor', 'raw_sensor_readings') }}
    where sensor_id is not null
      and reading_ts is not null

),

deduped as (

    select
        *,
        row_number() over (
            partition by sensor_id, reading_ts
            order by loaded_at desc
        ) as rn
    from source

)

select
    sensor_id,
    reading_ts,
    temperature_c,
    humidity_pct,
    source_file,
    loaded_at
from deduped
where rn = 1