with bounds as (

    select
        max(first_ts) as window_start,
        min(last_ts)  as window_end
    from (
        select
            sensor_id,
            min(reading_ts) as first_ts,
            max(reading_ts) as last_ts
        from {{ ref('stg_sensor_readings') }}
        group by sensor_id
    )

)

select s.*
from {{ ref('stg_sensor_readings') }} as s
cross join bounds as b
where s.reading_ts between b.window_start and b.window_end