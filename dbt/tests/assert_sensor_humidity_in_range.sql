select *
from {{ ref('stg_sensor_readings') }}
where humidity_pct < 0 or humidity_pct > 100