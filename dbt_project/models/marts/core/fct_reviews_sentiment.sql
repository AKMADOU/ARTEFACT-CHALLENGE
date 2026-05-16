-- Grain : one row per customer review.
-- Le signal non-structuré rendu structuré : sentiment + 10 flags topic.

with reviews as (
    select * from {{ ref('int_review_sentiment') }}
),
flight_ctx as (
    select flight_id, route_id, flight_status, is_on_time, is_delayed, is_cancelled
    from {{ ref('int_flight_economics') }}
)

select
    r.review_id,
    r.booking_id,
    r.customer_id,
    r.flight_id,
    f.route_id,
    r.review_date,

    r.rating,
    r.review_text,
    r.language,
    r.topics,

    r.sentiment_bucket,
    r.is_promoter,
    r.is_detractor,
    r.is_passive,

    r.has_punctuality,
    r.has_cabin_comfort,
    r.has_food_beverage,
    r.has_staff_service,
    r.has_cleanliness,
    r.has_baggage,
    r.has_value_for_money,
    r.has_boarding,
    r.has_entertainment,
    r.has_communication,

    f.flight_status,
    f.is_on_time,
    f.is_delayed,
    f.is_cancelled

from reviews r
left join flight_ctx f on r.flight_id = f.flight_id