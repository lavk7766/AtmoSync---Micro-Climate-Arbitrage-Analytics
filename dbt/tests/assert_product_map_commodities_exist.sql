-- Fails if the seed names a price series that does not exist (for example a typo).
select m.product_name, m.commodity
from {{ ref('product_commodity_map') }} m
left join {{ ref('int_commodity_price_latest') }} l
  on lower(trim(m.commodity)) = l.commodity
where l.commodity is null