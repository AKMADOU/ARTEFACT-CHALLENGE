with source as (
    select * from {{ source('airci_raw', 'customer_reviews') }}
),
renamed as (
    select
        review_id,
        booking_id,
        customer_id,
        flight_id,
        review_date::date  as review_date,
        rating::integer    as rating,
        review_text,
        language,
        topics
    from source
)
select * from renamed