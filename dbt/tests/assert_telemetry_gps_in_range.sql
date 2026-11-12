-- Latitude must be between -90 and 90, longitude between -180 and 180.
select *
from {{ ref('stg_container_telemetry') }}
where (latitude is not null and (latitude < -90 or latitude > 90))
   or (longitude is not null and (longitude < -180 or longitude > 180))