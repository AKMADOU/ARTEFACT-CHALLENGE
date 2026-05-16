-- Per-flight view : revenue (bookings) + cost (route_operating_costs)
-- + disruption cause. Single source for fct_flights et le P&L route.

with flights as (
    select * from {{ ref('stg_flights') }}
),
costs as (
    select * from {{ ref('stg_route_operating_costs') }}
),
routes as (
    select * from {{ ref('stg_routes') }}
),
booking_agg as (
    select
        flight_id,
        sum(ticket_price_usd)                              as ticket_revenue_usd,
        sum(ancillary_revenue_usd)                         as ancillary_revenue_usd,
        sum(ticket_price_usd + ancillary_revenue_usd)      as total_revenue_usd,
        count(*)                                           as pax_count,
        sum(case when ancillary_revenue_usd > 0 then 1 else 0 end) as pax_with_ancillary
    from {{ ref('stg_bookings') }}
    where booking_status in ('Flown', 'Confirmed')
    group by flight_id
),
disruption as (
    select flight_id, root_cause, sub_cause
    from {{ ref('stg_disruption_log') }}
)

select
    f.flight_id,
    f.flight_number,
    f.route_id,
    r.origin_airport_code,
    r.destination_airport_code,
    r.route_type,
    r.distance_km,
    r.block_time_min,
    f.flight_date,
    f.aircraft_type,
    f.seat_capacity,
    f.flight_status,
    f.delay_min,

    coalesce(b.ticket_revenue_usd,    0)  as ticket_revenue_usd,
    coalesce(b.ancillary_revenue_usd, 0)  as ancillary_revenue_usd,
    coalesce(b.total_revenue_usd,     0)  as total_revenue_usd,
    coalesce(b.pax_count,             0)  as pax_count,
    coalesce(b.pax_with_ancillary,    0)  as pax_with_ancillary,

    c.fuel_cost_usd,
    c.crew_cost_usd,
    c.airport_fees_usd,
    c.nav_fees_usd,
    c.handling_cost_usd,
    c.total_operating_cost_usd,

    coalesce(b.total_revenue_usd, 0) - c.total_operating_cost_usd as margin_usd,

    f.seat_capacity * r.distance_km                          as ask,
    coalesce(b.pax_count, 0) * r.distance_km                 as rpk,

    d.root_cause as disruption_root_cause,
    d.sub_cause  as disruption_sub_cause,

    case when f.flight_status = 'On Time'                          then true else false end as is_on_time,
    case when f.flight_status = 'Delayed' and f.delay_min > 15     then true else false end as is_delayed,
    case when f.flight_status = 'Cancelled'                        then true else false end as is_cancelled

from flights f
left join routes      r on f.route_id   = r.route_id
left join booking_agg b on f.flight_id  = b.flight_id
left join costs       c on f.flight_id  = c.flight_id
left join disruption  d on f.flight_id  = d.flight_id