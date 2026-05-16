-- Booking + items ancillary décomposés (pivot par item_type)
-- Drive les item-level attach rates pour le levier upsell.

with bookings as (
    select * from {{ ref('stg_bookings') }}
),
purchases as (
    select * from {{ ref('stg_ancillary_purchases') }}
),
ancillary_pivot as (
    select
        booking_id,
        sum(case when item_type = 'baggage'  then total_price_usd else 0 end) as anc_baggage_usd,
        sum(case when item_type = 'seat'     then total_price_usd else 0 end) as anc_seat_usd,
        sum(case when item_type = 'meal'     then total_price_usd else 0 end) as anc_meal_usd,
        sum(case when item_type = 'lounge'   then total_price_usd else 0 end) as anc_lounge_usd,
        sum(case when item_type = 'priority' then total_price_usd else 0 end) as anc_priority_usd,
        sum(case when item_type = 'upgrade'  then total_price_usd else 0 end) as anc_upgrade_usd,
        count(*)                                                              as anc_item_count
    from purchases
    group by booking_id
)

select
    b.booking_id,
    b.customer_id,
    b.flight_id,
    b.booking_date,
    b.fare_class,
    b.fare_family,
    b.booking_channel,
    b.booking_status,
    b.ticket_price_usd,
    b.ancillary_revenue_usd,
    b.ticket_price_usd + b.ancillary_revenue_usd as total_booking_revenue_usd,

    coalesce(a.anc_baggage_usd,  0) as anc_baggage_usd,
    coalesce(a.anc_seat_usd,     0) as anc_seat_usd,
    coalesce(a.anc_meal_usd,     0) as anc_meal_usd,
    coalesce(a.anc_lounge_usd,   0) as anc_lounge_usd,
    coalesce(a.anc_priority_usd, 0) as anc_priority_usd,
    coalesce(a.anc_upgrade_usd,  0) as anc_upgrade_usd,
    coalesce(a.anc_item_count,   0) as anc_item_count,

    case when coalesce(a.anc_lounge_usd, 0)   > 0 then true else false end as bought_lounge,
    case when coalesce(a.anc_upgrade_usd, 0)  > 0 then true else false end as bought_upgrade,
    case when coalesce(a.anc_meal_usd, 0)     > 0 then true else false end as bought_meal,
    case when coalesce(a.anc_seat_usd, 0)     > 0 then true else false end as bought_seat_selection,
    case when b.ancillary_revenue_usd         > 0 then true else false end as has_any_ancillary

from bookings b
left join ancillary_pivot a on b.booking_id = a.booking_id