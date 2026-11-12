-- Staging model for the monthly commodity price series.
-- Only $/kg and $/mt can be converted to a per-kg price exactly.
-- Every other unit keeps price_per_kg as NULL (no guessing or estimating).

with source as (

    select *
    from {{ source('raw', 'raw_commodity_price_monthly') }}

)

select
    price_month,
    lower(trim(commodity)) as commodity,
    trim(unit)             as unit,
    price,
    case
        when trim(unit) = '$/kg' then price
        when trim(unit) = '$/mt' then price / 1000
    end                    as price_per_kg,
    source_file,
    loaded_at
from source