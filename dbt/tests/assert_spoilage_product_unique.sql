select product_name, product_stage, count(*) as row_count
from {{ ref('stg_product_spoilage_reference') }}
group by product_name, product_stage
having count(*) > 1