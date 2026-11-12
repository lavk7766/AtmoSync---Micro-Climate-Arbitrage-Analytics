-- Fails if any humidity reading is outside 0-100 %.
select *
from {{ ref('stg_household_fridge_readings') }}
where rh_amb not between 0 and 100
   or rh_ms  not between 0 and 100
   or rh_ts  not between 0 and 100
   or rh_vd  not between 0 and 100
   or rh_ds  not between 0 and 100
   or rh_fc  not between 0 and 100