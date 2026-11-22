
-- Check risk classifications against the proposed thresholds.

select *
from {{ ref('mart_spoilage_risk') }}
where risk_level is null
   or risk_level != case
       when remaining_shelf_life_pct <= 25
           then 'HIGH_RISK'
       when remaining_shelf_life_pct <= 50
           then 'WARNING'
       else 'NORMAL'
   end
