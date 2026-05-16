-- Ontology rule : routes stratégiques (international/regional avec part de
-- capacité > 5%) mais déficitaires (margin < 0).

with route_rollup as (
    select
        f.route_id,
        sum(f.ask)                      as route_ask,
        sum(f.rpk)                      as route_rpk,
        sum(f.total_revenue_usd)        as route_revenue_usd,
        sum(f.total_operating_cost_usd) as route_cost_usd,
        sum(f.margin_usd)               as route_margin_usd,
        count(*)                        as flights_count,
        sum(f.pax_count)                as total_pax
    from {{ ref('fct_flights') }} f
    group by f.route_id
),
network_total as (
    select sum(route_ask) as network_ask from route_rollup
),
enriched as (
    select
        d.route_id,
        d.route_label,
        d.origin_city,
        d.destination_city,
        d.route_type,
        d.distance_km,
        rr.flights_count,
        rr.total_pax,
        rr.route_revenue_usd,
        rr.route_cost_usd,
        rr.route_margin_usd,
        case when rr.route_revenue_usd > 0
             then rr.route_margin_usd / rr.route_revenue_usd
             else null
        end as margin_pct,
        rr.route_ask / nt.network_ask as ask_share,
        case when rr.route_ask > 0 then rr.route_rpk * 1.0 / rr.route_ask else 0 end as load_factor
    from {{ ref('dim_route') }} d
    left join route_rollup rr on d.route_id = rr.route_id
    cross join network_total nt
)

select
    route_id,
    route_label,
    origin_city,
    destination_city,
    route_type,
    flights_count,
    total_pax,
    route_revenue_usd,
    route_cost_usd,
    route_margin_usd,
    margin_pct,
    ask_share,
    load_factor,
    -- Evidence trail (auditabilité)
    case when route_type in ('International', 'Regional')      then true else false end as cond_strategic_route_type,
    case when ask_share > 0.05                                 then true else false end as cond_meaningful_capacity,
    case when margin_pct < 0                                   then true else false end as cond_unprofitable,
    true as is_strategic_underperforming_route

from enriched
where route_type in ('International', 'Regional')
  and ask_share > 0.05
  and margin_pct < 0