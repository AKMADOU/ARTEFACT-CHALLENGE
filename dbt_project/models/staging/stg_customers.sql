with source as (
    select * from {{ source('airci_raw', 'customers') }}
),
renamed as (
    select
        customer_id,
        customer_segment,
        loyalty_tier,
        country,
        signup_date::date as signup_date
    from source
)
select * from renamed