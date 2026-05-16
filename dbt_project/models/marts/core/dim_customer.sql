with engagement as (
    select * from {{ ref('int_customer_engagement') }}
)

select
    customer_id,
    customer_segment,
    loyalty_tier,
    country,
    signup_date,

    total_bookings,
    lifetime_revenue_usd,
    lifetime_ticket_revenue_usd,
    lifetime_ancillary_revenue_usd,
    first_booking_date,
    last_booking_date,

    bookings_business,
    bookings_premium_eco,
    bookings_economy,
    bookings_with_ancillary,

    loyalty_txn_count,
    earn_event_count,
    redeem_event_count,
    miles_earned,
    miles_redeemed,
    last_loyalty_activity_date,
    has_loyalty_activity,

    support_ticket_count,
    high_severity_tickets,

    earn_events_per_booking,
    personal_ancillary_attach_rate,

    case when loyalty_tier in ('Silver', 'Gold')          then true else false end as is_premium_loyalty,
    case when customer_segment in ('Business', 'Premium') then true else false end as is_high_value_segment

from engagement