select *
from {{ ref('stg_product_spoilage_reference') }}
where humidity_min_pct < 0
   or humidity_max_pct > 100
   or humidity_min_pct > humidity_max_pct