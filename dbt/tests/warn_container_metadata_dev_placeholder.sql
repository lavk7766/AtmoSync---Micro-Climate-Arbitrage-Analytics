
{{ config(severity='warn') }}

-- Development placeholder records should be reviewed
-- and replaced with real container metadata.
select *
from {{ ref('stg_container_metadata') }}
where source_type = 'dev_placeholder'
