-- Reviews enrichies : sentiment classifié + flags par topic (10 tags).
-- Le champ topics est semi-colon-separated; on l'éclate en booléens
-- pour que les agrégations downstream soient des SUMs simples.

with reviews as (
    select * from {{ ref('stg_customer_reviews') }}
)

select
    review_id,
    booking_id,
    customer_id,
    flight_id,
    review_date,
    rating,
    review_text,
    language,
    topics,

    case
        when rating >= 4 then 'Promoter'
        when rating <= 2 then 'Detractor'
        else 'Passive'
    end as sentiment_bucket,

    case when rating >= 4 then true else false end as is_promoter,
    case when rating <= 2 then true else false end as is_detractor,
    case when rating  = 3 then true else false end as is_passive,

    case when topics like '%punctuality%'     then true else false end as has_punctuality,
    case when topics like '%cabin_comfort%'   then true else false end as has_cabin_comfort,
    case when topics like '%food_beverage%'   then true else false end as has_food_beverage,
    case when topics like '%staff_service%'   then true else false end as has_staff_service,
    case when topics like '%cleanliness%'     then true else false end as has_cleanliness,
    case when topics like '%baggage%'         then true else false end as has_baggage,
    case when topics like '%value_for_money%' then true else false end as has_value_for_money,
    case when topics like '%boarding%'        then true else false end as has_boarding,
    case when topics like '%entertainment%'   then true else false end as has_entertainment,
    case when topics like '%communication%'   then true else false end as has_communication

from reviews