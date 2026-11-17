-- Every container's product must exist in the spoilage reference (same spelling).
select m.container_id, m.product_name
from {{ ref('stg_container_metadata') }} as m
left join {{ ref('stg_product_spoilage_reference') }} as r
    on r.product_name = m.product_name
where r.product_name is null