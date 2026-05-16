-- Ontology rule : customers high-value montrant un signal de désengagement.
-- Seuils ADAPTATIFS (quantiles de la cohorte) plutôt qu'absolus — voir
-- Phase 1 §6 sur la limitation du starter (tous les customers actifs).

with base as (
    select * from {{ ref('dim_customer') }}
),
cohort as (
    -- Calcul des seuils restreint au peer group : Business/Premium + Silver/Gold
    select
        quantile_cont(earn_events_per_booking, 0.50) as cohort_median_engagement,
        quantile_cont(lifetime_revenue_usd,    0.60) as cohort_p60_revenue
    from base
    where is_high_value_segment
      and is_premium_loyalty
      and earn_events_per_booking is not null
)

select
    b.customer_id,
    b.customer_segment,
    b.loyalty_tier,
    b.country,
    b.total_bookings,
    b.lifetime_revenue_usd,
    b.earn_event_count,
    b.earn_events_per_booking,
    b.last_loyalty_activity_date,
    b.high_severity_tickets,
    c.cohort_median_engagement,
    c.cohort_p60_revenue,

    case when b.is_high_value_segment                                  then true else false end as cond_high_value_segment,
    case when b.is_premium_loyalty                                     then true else false end as cond_premium_loyalty,
    case when coalesce(b.earn_events_per_booking, 0)
              < c.cohort_median_engagement                             then true else false end as cond_below_median_engagement,
    case when b.lifetime_revenue_usd > c.cohort_p60_revenue            then true else false end as cond_above_p60_revenue,

    true as is_highvalue_atrisk_customer

from base b
cross join cohort c
where b.is_high_value_segment
  and b.is_premium_loyalty
  and coalesce(b.earn_events_per_booking, 0) < c.cohort_median_engagement
  and b.lifetime_revenue_usd > c.cohort_p60_revenue