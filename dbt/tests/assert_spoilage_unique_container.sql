
-- Every container must appear only once in the spoilage-risk mart.

select
    container_id,
    count(*) as row_count
from {{ ref('mart_spoilage_risk') }}
group by container_id
having count(*) > 1
