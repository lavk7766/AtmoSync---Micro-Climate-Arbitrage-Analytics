-- Fails if a product from the spoilage reference is missing from the mart.
select p.product_name
from (select distinct product_name from {{ ref('stg_product_spoilage_reference') }}) p
left join {{ ref('mart_product_price_status') }} m on m.product_name = p.product_name
where m.product_name is null