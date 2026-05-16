-- BI-ready : route × month avec tous les KPIs.
-- Drive la page Network & Profitability du dashboard Phase 3.

with flight_monthly as (
    select
        f.route_id,
        date_trunc('month', f.flight_date)::date as month_start,
        strftime(f.flight_date, '%Y-%m')         as year_month,

        count(*)                                                    as flights_count,
        sum(case when f.is_cancelled then 1 else 0 end)             as cancelled_count,
        sum(case when f.is_delayed   then 1 else 0 end)             as delayed_count,
        sum(case when f.is_on_time   then 1 else 0 end)             as on_time_count,
        sum(f.pax_count)                                            as pax_count,
        sum(f.ask)                                                  as ask,
        sum(f.rpk)                                                  as rpk,

        sum(f.ticket_revenue_usd)                                   as ticket_revenue_usd,
        sum(f.ancillary_revenue_usd)                                as ancillary_revenue_usd,
        sum(f.total_revenue_usd)                                    as total_revenue_usd,

        sum(f.fuel_cost_usd)                                        as fuel_cost_usd,
        sum(f.crew_cost_usd)                                        as crew_cost_usd,
        sum(f.airport_fees_usd)                                     as airport_fees_usd,
        sum(f.nav_fees_usd)                                         as nav_fees_usd,
        sum(f.handling_cost_usd)                                    as handling_cost_usd,
        sum(f.total_operating_cost_usd)                             as total_operating_cost_usd,
        sum(f.margin_usd)                                           as margin_usd
    from {{ ref('fct_flights') }} f
    group by 1, 2, 3
)

select
    r.route_id,
    r.route_label,
    r.origin_city,
    r.destination_city,
    r.route_type,
    r.distance_km,
    m.month_start,
    m.year_month,

    m.flights_count,
    m.cancelled_count,
    m.delayed_count,
    m.on_time_count,
    m.pax_count,

    case when m.flights_count > 0
         then m.on_time_count   * 1.0 / m.flights_count else null end as on_time_performance,
    case when m.flights_count > 0
         then m.cancelled_count * 1.0 / m.flights_count else null end as cancellation_rate,

    m.ask,
    m.rpk,
    case when m.ask > 0 then m.rpk * 1.0 / m.ask else 0 end as load_factor,

    m.ticket_revenue_usd,
    m.ancillary_revenue_usd,
    m.total_revenue_usd,
    case when m.rpk > 0 then m.total_revenue_usd / m.rpk else null end as yield_usd_per_rpk,
    case when m.ask > 0 then m.total_revenue_usd / m.ask else null end as rask,

    m.fuel_cost_usd,
    m.crew_cost_usd,
    m.airport_fees_usd,
    m.nav_fees_usd,
    m.handling_cost_usd,
    m.total_operating_cost_usd,
    case when m.ask > 0 then m.total_operating_cost_usd / m.ask else null end as cask,

    m.margin_usd,
    case when m.total_revenue_usd > 0
         then m.margin_usd / m.total_revenue_usd
         else null end as margin_pct

from flight_monthly m
left join {{ ref('dim_route') }} r on m.route_id = r.route_id