select sensor_id, reading_ts, count(*) as row_count
from {{ ref('stg_sensor_readings') }}
group by sensor_id, reading_ts
having count(*) > 1