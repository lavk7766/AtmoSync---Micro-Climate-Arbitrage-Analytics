-- $/kg keeps its price, $/mt is divided by 1000, every other unit stays NULL.
select *
from {{ ref('stg_commodity_price_monthly') }}
where (unit = '$/kg' and (price_per_kg is null or price_per_kg != price))
   or (unit = '$/mt' and (price_per_kg is null or abs(price_per_kg - price / 1000) > 0.000000001))
   or (unit not in ('$/kg', '$/mt') and price_per_kg is not null)