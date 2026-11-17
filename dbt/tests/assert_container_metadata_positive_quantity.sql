
-- Every container must have a positive quantity.
select *
from {{ ref('stg_container_metadata') }}
where quantity <= 0
   or quantity is null
