with source as (
    select * from {{ source('airci_raw', 'bookings') }}
),
renamed as (
    select
        booking_id,
        customer_id,
        flight_id,
        booking_date::date              as booking_date,
        fare_class,
        fare_family,
        booking_channel,
        booking_status,
        ticket_price_usd::double        as ticket_price_usd,
        ancillary_revenue_usd::double   as ancillary_revenue_usd
    from source
)
select * from renamed