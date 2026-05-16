-- Grain : one row per booking.
-- Unité d'analyse pour le levier upsell.

with bookings_anc as (
    select * from {{ ref('int_booking_with_ancillary') }}
),
flight_ctx as (
    select
        flight_id,
        route_id,
        flight_date,
        flight_status,
        is_on_time,
        is_delayed,
        is_cancelled
    from {{ ref('int_flight_economics') }}
)

select
    b.booking_id,
    b.customer_id,
    b.flight_id,
    f.route_id,
    b.booking_date,
    f.flight_date,

    b.fare_class,
    b.fare_family,
    b.booking_channel,
    b.booking_status,

    b.ticket_price_usd,
    b.ancillary_revenue_usd,
    b.total_booking_revenue_usd,

    b.anc_baggage_usd,
    b.anc_seat_usd,
    b.anc_meal_usd,
    b.anc_lounge_usd,
    b.anc_priority_usd,
    b.anc_upgrade_usd,
    b.anc_item_count,
    b.has_any_ancillary,
    b.bought_lounge,
    b.bought_upgrade,
    b.bought_meal,
    b.bought_seat_selection,

    f.flight_status,
    f.is_on_time,
    f.is_delayed,
    f.is_cancelled

from bookings_anc b
left join flight_ctx f on b.flight_id = f.flight_id