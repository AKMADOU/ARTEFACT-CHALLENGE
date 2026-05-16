-- Per-customer summary : bookings + loyalty activity + tickets.
-- Base table pour dim_customer et l'ontology rule at-risk.

with customers as (
    select * from {{ ref('stg_customers') }}
),
booking_agg as (
    select
        customer_id,
        count(*)                                            as total_bookings,
        sum(ticket_price_usd + ancillary_revenue_usd)       as lifetime_revenue_usd,
        sum(ticket_price_usd)                               as lifetime_ticket_revenue_usd,
        sum(ancillary_revenue_usd)                          as lifetime_ancillary_revenue_usd,
        max(booking_date)                                   as last_booking_date,
        min(booking_date)                                   as first_booking_date,
        sum(case when fare_class = 'Business'        then 1 else 0 end) as bookings_business,
        sum(case when fare_class = 'Premium Economy' then 1 else 0 end) as bookings_premium_eco,
        sum(case when fare_class = 'Economy'         then 1 else 0 end) as bookings_economy,
        sum(case when ancillary_revenue_usd > 0      then 1 else 0 end) as bookings_with_ancillary
    from {{ ref('stg_bookings') }}
    where booking_status in ('Flown', 'Confirmed')
    group by customer_id
),
loyalty_agg as (
    select
        customer_id,
        count(*)                                                              as loyalty_txn_count,
        sum(case when txn_type = 'Earn'   then 1 else 0 end)                  as earn_event_count,
        sum(case when txn_type = 'Redeem' then 1 else 0 end)                  as redeem_event_count,
        sum(case when txn_type = 'Earn'   then miles_amount else 0 end)       as miles_earned,
        sum(case when txn_type = 'Redeem' then abs(miles_amount) else 0 end)  as miles_redeemed,
        max(txn_date)                                                         as last_loyalty_activity_date
    from {{ ref('stg_loyalty_transactions') }}
    group by customer_id
),
ticket_agg as (
    select
        customer_id,
        count(*) as support_ticket_count,
        sum(case when severity = 'High' then 1 else 0 end) as high_severity_tickets
    from {{ ref('stg_support_tickets') }}
    group by customer_id
)

select
    c.customer_id,
    c.customer_segment,
    c.loyalty_tier,
    c.country,
    c.signup_date,

    coalesce(b.total_bookings,                  0) as total_bookings,
    coalesce(b.lifetime_revenue_usd,            0) as lifetime_revenue_usd,
    coalesce(b.lifetime_ticket_revenue_usd,     0) as lifetime_ticket_revenue_usd,
    coalesce(b.lifetime_ancillary_revenue_usd,  0) as lifetime_ancillary_revenue_usd,
    b.first_booking_date,
    b.last_booking_date,
    coalesce(b.bookings_business,        0) as bookings_business,
    coalesce(b.bookings_premium_eco,     0) as bookings_premium_eco,
    coalesce(b.bookings_economy,         0) as bookings_economy,
    coalesce(b.bookings_with_ancillary,  0) as bookings_with_ancillary,

    coalesce(l.loyalty_txn_count,    0) as loyalty_txn_count,
    coalesce(l.earn_event_count,     0) as earn_event_count,
    coalesce(l.redeem_event_count,   0) as redeem_event_count,
    coalesce(l.miles_earned,         0) as miles_earned,
    coalesce(l.miles_redeemed,       0) as miles_redeemed,
    l.last_loyalty_activity_date,
    case when l.loyalty_txn_count > 0 then true else false end as has_loyalty_activity,

    coalesce(t.support_ticket_count,   0) as support_ticket_count,
    coalesce(t.high_severity_tickets,  0) as high_severity_tickets,

    case
        when coalesce(b.total_bookings, 0) = 0 then null
        else coalesce(l.earn_event_count, 0) * 1.0 / b.total_bookings
    end as earn_events_per_booking,

    case
        when coalesce(b.total_bookings, 0) = 0 then null
        else coalesce(b.bookings_with_ancillary, 0) * 1.0 / b.total_bookings
    end as personal_ancillary_attach_rate

from customers c
left join booking_agg b on c.customer_id = b.customer_id
left join loyalty_agg l on c.customer_id = l.customer_id
left join ticket_agg  t on c.customer_id = t.customer_id