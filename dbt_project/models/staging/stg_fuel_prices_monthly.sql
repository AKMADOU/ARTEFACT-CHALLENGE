with source as (
    select * from {{ source('airci_raw', 'fuel_prices_monthly') }}
),
renamed as (
    select
        year_month,
        jet_fuel_usd_per_kg::double     as jet_fuel_usd_per_kg,
        jet_fuel_usd_per_gallon::double as jet_fuel_usd_per_gallon
    from source
)
select * from renamed