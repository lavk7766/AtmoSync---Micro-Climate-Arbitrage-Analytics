select *
from {{ ref('stg_product_spoilage_reference') }}
where recommended_temp_min_c > recommended_temp_max_c
   or best_temp_c < recommended_temp_min_c
   or best_temp_c > recommended_temp_max_c