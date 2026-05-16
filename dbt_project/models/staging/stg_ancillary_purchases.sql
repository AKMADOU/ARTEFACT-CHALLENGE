with source as (
    select * from {{ source('airci_raw', 'ancillary_purchases') }}
),
renamed as (
    select
        ancillary_purchase_id,
        booking_id,
        item_id,
        item_type,
        item_name,
        quantity::integer        as quantity,
        unit_price_usd::double   as unit_price_usd,
        total_price_usd::double  as total_price_usd
    from source
)
select * from renamed