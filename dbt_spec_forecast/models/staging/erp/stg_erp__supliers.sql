with source as (
    select *
    from {{ source('raw_erp', 'suppliers') }}
),

cleaned_suppliers as (
    select
        supplier_id,
        supplier_name,
        case country_raw
            when 'Malaysia' then 'MY'
            when 'Hungary' then 'HU'
            else country_raw
        end as country,
        base_lead_time_days::integer as base_lead_time_days,
        moq_cases::integer as moq_cases,
        reliability_score::double as reliability_score,
        currency_code,
        updated_at::timestamp as updated_at
    from source
)

select *
from cleaned_suppliers