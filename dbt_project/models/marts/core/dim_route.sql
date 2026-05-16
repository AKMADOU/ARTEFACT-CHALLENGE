with routes as (
    select * from {{ ref('stg_routes') }}
),
airports as (
    select * from {{ ref('stg_airports') }}
)

select
    r.route_id,
    r.origin_airport_code,
    o.city           as origin_city,
    o.country        as origin_country,
    r.destination_airport_code,
    d.city           as destination_city,
    d.country        as destination_country,
    r.route_type,
    r.distance_km,
    r.block_time_min,
    r.origin_airport_code || ' → ' || r.destination_airport_code as route_label

from routes r
left join airports o on r.origin_airport_code      = o.airport_code
left join airports d on r.destination_airport_code = d.airport_code