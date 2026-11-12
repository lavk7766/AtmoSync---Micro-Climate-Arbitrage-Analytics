-- One row per product and matched price series.
-- Products with no price series stay NULL (price_status = 'no price data').
-- Only direct matches are listed in the seed; any future proxy or estimated
-- price must be added with a different match_type so it is never mistaken for real data.

with products as (

    select distinct product_name
    from {{ ref('stg_product_spoilage_reference') }}

),

product_map as (

    select
        lower(trim(product_name)) as product_name,
        lower(trim(commodity))    as commodity,
        match_type
    from {{ ref('product_commodity_map') }}

),

latest as (

    select * from {{ ref('int_commodity_price_latest') }}

)

select
    p.product_name,
    m.commodity,
    m.match_type,
    l.unit,
    l.latest_price_month,
    l.latest_price_per_kg,
    case
        when m.commodity is null then 'no price data'
        when l.latest_price_per_kg is null then 'matched, not convertible to per kg'
        else 'direct match'
    end as price_status
from products p
left join product_map m on m.product_name = p.product_name
left join latest l on l.commodity = m.commodity