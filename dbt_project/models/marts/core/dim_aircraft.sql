with fleet as (
    select * from {{ ref('stg_aircraft_fleet') }}
)

select
    aircraft_type,
    manufacturer,
    seats_total,
    seats_business,
    seats_premium_eco,
    seats_economy,
    fuel_burn_kg_per_hour,
    cost_per_block_hour_usd,
    crew_cost_per_hour_usd,
    introduced_year,
    fleet_count,
    case
        when seats_total >= 200 then 'Long-Haul'
        when seats_total >= 150 then 'Medium-Haul'
        else 'Short-Haul'
    end as aircraft_class

from fleet