with source as (
    select * from {{ source('airci_raw', 'route_operating_costs') }}
),
renamed as (
    select
        flight_id,
        fuel_cost_usd::double            as fuel_cost_usd,
        crew_cost_usd::double            as crew_cost_usd,
        airport_fees_usd::double         as airport_fees_usd,
        nav_fees_usd::double             as nav_fees_usd,
        handling_cost_usd::double        as handling_cost_usd,
        total_operating_cost_usd::double as total_operating_cost_usd
    from source
)
select * from renamed