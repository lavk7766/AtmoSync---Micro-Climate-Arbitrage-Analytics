select *
from {{ ref('stg_container_telemetry') }}
qualify row_number() over (partition by container_id order by event_ts desc) = 1