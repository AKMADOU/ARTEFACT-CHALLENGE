with source as (
    select * from {{ source('airci_raw', 'disruption_log') }}
),
renamed as (
    select
        disruption_id,
        flight_id,
        root_cause,
        sub_cause,
        description,
        recovery_action
    from source
)
select * from renamed