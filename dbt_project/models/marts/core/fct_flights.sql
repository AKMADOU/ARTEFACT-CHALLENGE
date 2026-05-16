-- Grain : one row per operated flight.
-- Unité d'analyse pour le route P&L et la fiabilité opérationnelle.

with flight_econ as (
    select * from {{ ref('int_flight_economics') }}
)

select
    flight_id,
    flight_number,
    route_id,
    aircraft_type,
    flight_date,

    seat_capacity,
    flight_status,
    delay_min,
    is_on_time,
    is_delayed,
    is_cancelled,
    disruption_root_cause,
    disruption_sub_cause,

    pax_count,
    pax_with_ancillary,
    ask,
    rpk,
    case when ask > 0 then rpk * 1.0 / ask else 0 end as load_factor,

    ticket_revenue_usd,
    ancillary_revenue_usd,
    total_revenue_usd,

    fuel_cost_usd,
    crew_cost_usd,
    airport_fees_usd,
    nav_fees_usd,
    handling_cost_usd,
    total_operating_cost_usd,

    margin_usd,
    case when total_revenue_usd > 0 then margin_usd / total_revenue_usd else null end as margin_pct,

    case when ask > 0 then total_revenue_usd        / ask else null end as rask,
    case when ask > 0 then total_operating_cost_usd / ask else null end as cask

from flight_econ