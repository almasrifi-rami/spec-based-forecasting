with source as (
    select *
    from {{ source('raw_erp', 'customers') }}
),

cleaned_customers as (
    select
        customer_id,
        customer_name,
        case
            when customer_segment_raw ilike '%health%' or customer_segment_raw ilike '%hospital%'
                then 'HEALTHCARE_HOSPITAL'
            when customer_segment_raw ilike '%dental%' then 'DENTAL_CLINIC_DIST'
            when customer_segment_raw ilike '%industrial%' or customer_segment_raw ilike '%auto%'
                then 'INDUSTRIAL_AUTO'
            when customer_segment_raw ilike '%pharma%' or customer_segment_raw ilike '%lab%'
                then 'LAB_PHARMA'
            else null
        end as customer_segment,
        case country_raw
            when 'Hungary' then 'HU'
            when 'Germany' then 'DE'
            else country_raw
        end as country,
        upper(contract_tier_raw) as contract_tier,
        upper(preferred_substitute_rule) as preferred_substitute_rule,
        credit_limit_eur::double as credit_limit_eur,
        payment_terms_days::integer as payment_terms_days,
        created_date::date as created_date
    from source
)

select *
from cleaned_customers