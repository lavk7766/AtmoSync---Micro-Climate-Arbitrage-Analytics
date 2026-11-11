-- Fails if the same commodity has two prices for the same month and unit.
select
    price_month,
    commodity,
    unit,
    count(*) as n
from {{ ref('stg_commodity_price_monthly') }}
group by price_month, commodity, unit
having count(*) > 1