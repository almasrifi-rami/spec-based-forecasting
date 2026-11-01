with source as (
    select *
    from {{ source('raw_erp', 'items') }}
),

deduplicated_items as (
    select *
    from source
    qualify
        row_number() over (partition by item_id order by erp_extracted_at desc)
        = 1
),

extracted_weights as (
    select
        regexp_extract(
            replace(weight_raw, ',', '.'),
            '\d+(\.\d+)?'
        )::double as extracted_weight,
        *
    from deduplicated_items
),

cleaned_items as (
    select
        case
            when material_raw ilike '%latex%' then 'LATEX'
            when material_raw ilike '%nitrile%' then 'NITRILE'
            when material_raw ilike '%vinyl%' then 'VINYL'
            else null
        end as material,
        case
            when size_raw = 'Extra Small' or size_raw like '%XS%' then 'XS'
            when size_raw = 'm' or size_raw like '%M%' then 'M'
            when size_raw like '%XL%' then 'XL'
            when size_raw like '%L%' then 'L'
            when size_raw like '%S%' then 'S'
            else null
        end as size,
        upper(trim(color_raw)) as color,
        case
            when weight_raw ilike '%mg%' then extracted_weight / 1000
            else extracted_weight
        end as weight_grams,
        concat('BOX_', regexp_extract(order_uom_raw, '\d+'))
            as order_uom,
        regexp_extract(order_uom_raw, '\d+')::integer
            as pieces_per_order_uom,
        *
    from extracted_weights
),

cleaned_items_w_description as (
    select
        item_id,
        sku_code,
        concat(
            material,
            ' GLOVE ',
            color,
            ' (',
            size,
            ') - ',
            weight_grams,
            ' G [',
            order_uom,
            ']'
        ) as item_description,
        primary_supplier_id as supplier_id,
        material,
        size,
        color,
        weight_grams,
        order_uom,
        pieces_per_order_uom,
        cases_per_pallet::integer as cases_per_pallet,
        boxes_per_case::integer as boxes_per_case,
        unit_cost_eur::double as unit_cost_eur,
        list_price_eur::double as list_price_eur,
        launch_date::date as launch_date,
        is_active_raw::bool as is_active,
        erp_extracted_at::timestamp as erp_extracted_at
    from cleaned_items
)

select *
from cleaned_items_w_description
