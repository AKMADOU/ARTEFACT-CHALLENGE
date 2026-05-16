with source as (
    select * from {{ source('airci_raw', 'support_tickets') }}
),
renamed as (
    select
        ticket_id,
        customer_id,
        related_booking_id,
        related_flight_id,
        open_date::date         as open_date,
        close_date::date        as close_date,
        channel,
        category,
        severity,
        status,
        resolution_hours::double as resolution_hours
    from source
)
select * from renamed