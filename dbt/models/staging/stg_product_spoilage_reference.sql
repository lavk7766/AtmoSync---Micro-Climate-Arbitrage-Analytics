select
    lower(trim(product_name))        as product_name,
    trim(product_stage_or_variety)   as product_stage,
    recommended_temp_min_c,
    recommended_temp_max_c,
    best_temp_c,
    humidity_min_pct,
    humidity_max_pct,
    shelf_life_min_hours,
    shelf_life_max_hours,
    data_source,
    source_url,
    notes,
    loaded_at
from {{ source('raw', 'product_spoilage_reference') }}