with source as (
    select * from {{ source('airci_raw', 'airports') }}
),
renamed as (
    select
        airport_code,
        airport_name,
        city,
        country,
        timezone,
        latitude::double  as latitude,
        longitude::double as longitude
    from source
)
select * from renamed