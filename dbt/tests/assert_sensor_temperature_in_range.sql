select *
from {{ ref('stg_sensor_readings') }}
where temperature_c < -30 or temperature_c > 70