with source as (
    select * from {{ source('airci_raw', 'ancillary_catalog') }}
),
renamed as (
    select
        item_id,
        item_type,
        item_name,
        base_price_usd::double as base_price_usd,
        applies_to_route_type
    from source
)
select * from renamed