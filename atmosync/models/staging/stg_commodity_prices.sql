select
    lower(trim(commodity)) as commodity,
    market_name,
    market_lat             as latitude,
    market_lon             as longitude,
    price_per_kg,
    price_date
from {{ source('raw', 'raw_commodity_prices') }}