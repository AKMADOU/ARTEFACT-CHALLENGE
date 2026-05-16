with source as (
    select * from {{ source('airci_raw', 'routes') }}
),
renamed as (
    select
        route_id,
        origin_airport_code,
        destination_airport_code,
        route_type,
        distance_km::integer    as distance_km,
        block_time_min::integer as block_time_min
    from source
)
select * from renamed