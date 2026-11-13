
-- Clean and standardize container metadata from Snowflake RAW.

select
    upper(trim(container_id))       as container_id,
    lower(trim(product_name))       as product_name,
    quantity::float                 as quantity,
    lower(trim(quantity_unit))      as quantity_unit,
    trim(origin)                    as origin,
    trim(destination)               as destination,
    nullif(trim(batch_id), '')      as batch_id,
    lower(trim(source_type))        as source_type,
    ingested_at
from {{ source('raw', 'raw_container_metadata') }}
where container_id is not null
  and trim(container_id) != ''
