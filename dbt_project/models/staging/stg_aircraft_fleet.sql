with source as (
    select * from {{ source('airci_raw', 'aircraft_fleet') }}
),
renamed as (
    select
        aircraft_type,
        manufacturer,
        seats_total::integer             as seats_total,
        seats_business::integer          as seats_business,
        seats_premium_eco::integer       as seats_premium_eco,
        seats_economy::integer           as seats_economy,
        fuel_burn_kg_per_hour::integer   as fuel_burn_kg_per_hour,
        cost_per_block_hour_usd::integer as cost_per_block_hour_usd,
        crew_cost_per_hour_usd::integer  as crew_cost_per_hour_usd,
        introduced_year::integer         as introduced_year,
        fleet_count::integer             as fleet_count
    from source
)
select * from renamed