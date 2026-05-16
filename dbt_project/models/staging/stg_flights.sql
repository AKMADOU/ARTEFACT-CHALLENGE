with source as (
    select * from {{ source('airci_raw', 'flights') }}
),
renamed as (
    select
        flight_id,
        flight_number,
        route_id,
        flight_date::date          as flight_date,
        scheduled_departure::time  as scheduled_departure,
        actual_departure::time     as actual_departure,
        scheduled_arrival::time    as scheduled_arrival,
        actual_arrival::time       as actual_arrival,
        aircraft_type,
        seat_capacity::integer     as seat_capacity,
        flight_status,
        delay_min::integer         as delay_min
    from source
)
select * from renamed