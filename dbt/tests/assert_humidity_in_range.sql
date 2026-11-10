select *
from {{ ref('stg_container_telemetry') }}
where humidity_pct < 0 or humidity_pct > 100