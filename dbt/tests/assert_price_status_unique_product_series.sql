-- One row per product and price series in the mart.
select product_name, commodity, count(*) as row_count
from {{ ref('mart_product_price_status') }}
group by product_name, commodity
having count(*) > 1