-- Fails if a fridge has two readings at the same time.
select fridge_number, time_minutes, count(*) as n
from {{ ref('stg_household_fridge_readings') }}
group by fridge_number, time_minutes
having count(*) > 1