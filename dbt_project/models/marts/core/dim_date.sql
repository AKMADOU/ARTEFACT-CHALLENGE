-- Spine de dates générée. DuckDB : generate_series.
-- Trino : remplacer par `sequence(date '2024-11-01', date '2025-01-31', interval '1' day)`

with date_spine as (
    select unnest(
        generate_series(date '2024-11-01', date '2025-01-31', interval 1 day)
    )::date as date_day
)

select
    date_day,
    extract(year   from date_day)        as year,
    extract(month  from date_day)        as month,
    extract(day    from date_day)        as day,
    extract(dow    from date_day)        as day_of_week,
    extract(doy    from date_day)        as day_of_year,
    extract(week   from date_day)        as iso_week,
    strftime(date_day, '%Y-%m')          as year_month,
    case
        when extract(dow from date_day) in (0, 6) then 'Weekend'
        else 'Weekday'
    end as day_type,
    case extract(month from date_day)
        when 11 then 'Nov 2024'
        when 12 then 'Dec 2024'
        when  1 then 'Jan 2025'
    end as month_label

from date_spine