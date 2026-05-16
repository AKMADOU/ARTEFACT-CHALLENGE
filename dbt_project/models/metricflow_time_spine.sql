-- Time spine requis par le dbt Semantic Layer (MetricFlow).
{{ config(materialized='table') }}

with days as (
    select unnest(
        generate_series(date '2024-11-01', date '2025-01-31', interval 1 day)
    )::date as date_day
)

select date_day from days