-- Staging model for household refrigerator readings.
-- REFERENCE DATA ONLY: domestic refrigerator readings used for exploratory
-- threshold calibration. They are NOT validated shipping-container safety thresholds.

select
    fridge_number,
    upper(trim(fridge_type)) as fridge_type,
    time_minutes,
    t_amb, t_ms, t_ts, t_vd, t_ds, t_fc,
    rh_amb, rh_ms, rh_ts, rh_vd, rh_ds, rh_fc,
    tp,
    source_file,
    loaded_at
from {{ source('raw', 'raw_household_fridge_readings') }}