-- Banana must appear as two separate price series (Europe and US), not merged.
with banana as (
    select count(distinct commodity) as series_count
    from {{ ref('mart_product_price_status') }}
    where product_name = 'banana' and price_status = 'direct match'
)
select * from banana where series_count != 2