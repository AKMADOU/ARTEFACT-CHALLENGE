-- Ontology rule : customers Economy-dominant, top 40% en lifetime revenue,
-- mais sous-attachés vs leurs pairs (attach < p25 du peer group Economy).

with base as (
    select * from {{ ref('dim_customer') }}
),
economy_dominant as (
    select
        customer_id,
        case when bookings_economy > (bookings_business + bookings_premium_eco)
             then true else false end as is_economy_dominant
    from base
),
cohort_thresholds as (
    select
        quantile_cont(b.lifetime_revenue_usd,           0.60) as p60_revenue_all,
        quantile_cont(b.personal_ancillary_attach_rate, 0.25) as p25_attach_economy
    from base b
    join economy_dominant e on b.customer_id = e.customer_id
    where e.is_economy_dominant
      and b.personal_ancillary_attach_rate is not null
)

select
    b.customer_id,
    b.customer_segment,
    b.loyalty_tier,
    b.country,
    b.total_bookings,
    b.bookings_economy,
    b.bookings_business + b.bookings_premium_eco as bookings_above_economy,
    b.lifetime_revenue_usd,
    b.lifetime_ancillary_revenue_usd,
    b.personal_ancillary_attach_rate,
    t.p60_revenue_all,
    t.p25_attach_economy,

    case when e.is_economy_dominant                                       then true else false end as cond_economy_dominant,
    case when b.lifetime_revenue_usd > t.p60_revenue_all                  then true else false end as cond_above_p60_revenue,
    case when coalesce(b.personal_ancillary_attach_rate, 0)
              < t.p25_attach_economy                                      then true else false end as cond_low_attach_vs_peers,

    true as is_upsell_ready_segment

from base b
join economy_dominant e on b.customer_id = e.customer_id
cross join cohort_thresholds t
where e.is_economy_dominant
  and b.lifetime_revenue_usd > t.p60_revenue_all
  and coalesce(b.personal_ancillary_attach_rate, 0) < t.p25_attach_economy