{{ config(materialized='view', schema='intermediate') }}

-- Latest available price for each commodity series.
-- price_per_kg stays NULL where the unit cannot be converted exactly (no estimated values).
-- The latest month differs by series, because some series stop earlier than others.

select
    commodity,
    unit,
    price_month  as latest_price_month,
    price        as latest_price,
    price_per_kg as latest_price_per_kg
from {{ ref('stg_commodity_price_monthly') }}
qualify row_number() over (partition by commodity order by price_month desc) = 1
