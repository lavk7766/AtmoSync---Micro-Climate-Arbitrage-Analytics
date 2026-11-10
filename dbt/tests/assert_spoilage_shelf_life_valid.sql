select *
from {{ ref('stg_product_spoilage_reference') }}
where shelf_life_min_hours <= 0
   or shelf_life_max_hours <= 0
   or shelf_life_min_hours > shelf_life_max_hours