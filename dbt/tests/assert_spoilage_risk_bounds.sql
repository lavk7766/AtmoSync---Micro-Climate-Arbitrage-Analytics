
-- Fail if any spoilage-risk result violates basic bounds.

select *
from {{ ref('mart_spoilage_risk') }}
where initial_shelf_life_hours <= 0
   or initial_shelf_life_hours is null
   or cumulative_aged_hours < 0
   or cumulative_aged_hours is null
   or remaining_shelf_life_hours < 0
   or remaining_shelf_life_hours > initial_shelf_life_hours
   or remaining_shelf_life_hours is null
   or remaining_shelf_life_pct < 0
   or remaining_shelf_life_pct > 100
   or remaining_shelf_life_pct is null
