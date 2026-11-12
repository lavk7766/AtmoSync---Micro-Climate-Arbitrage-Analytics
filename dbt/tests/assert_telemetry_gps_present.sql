-- Every telemetry event must carry a position.
select *
from {{ ref('stg_container_telemetry') }}
where latitude is null or longitude is null