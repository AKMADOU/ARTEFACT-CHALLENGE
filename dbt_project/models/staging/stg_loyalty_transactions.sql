with source as (
    select * from {{ source('airci_raw', 'loyalty_transactions') }}
),
renamed as (
    select
        loyalty_txn_id,
        customer_id,
        txn_date::date         as txn_date,
        txn_type,
        miles_amount::integer  as miles_amount,
        related_booking_id,
        description
    from source
)
select * from renamed