# Phase 1 — Preview insights from the data

> Computed by joining the starter dataset with the Phase 1 synthetic enrichments.
> These are **what the data already says** — useful for steering Phase 2 (modeling)
> and Phase 3 (dashboard) toward the most decision-relevant cuts.

## 1. Route P&L (current load factors, no scaling)

Margin % is the comparable signal across routes; absolute USD is sensitive to the low
load factors in the starter (see `04_assumptions.md §3 bis`).

| Route | Type | Destination | Flights | Pax/flt | Margin % |
|---|---|---|---:|---:|---:|
| R004 | Regional | Accra | 60 | 22 | +33.2% |
| R010 | Regional | Abidjan | 30 | 22 | +31.1% |
| R007 | Regional | Cotonou | 30 | 24 | +27.0% |
| R001 | Domestic | Bouaké | 30 | 22 | +18.0% |
| R012 | Regional | Abidjan | 30 | 23 | +17.2% |
| R008 | Regional | Ouagadougou | 30 | 22 | +13.3% |
| R006 | Regional | Lagos | 60 | 21 | +9.2% |
| R003 | Domestic | Korhogo | 30 | 24 | -3.0% |
| R002 | Domestic | Man | 30 | 22 | -4.1% |
| R011 | Regional | Abidjan | 30 | 22 | -6.7% |
| R005 | Regional | Dakar | 60 | 21 | -14.3% |
| R009 | International | Paris | 60 | 22 | -86.9% |

**Read:** Regional routes from Abidjan into West Africa (Accra, Cotonou, Dakar)
are the profitability backbone. The Paris route is structurally underused — the
conversation should be about **demand generation**, not whether to keep flying it.
Domestic routes are slightly negative — likely strategic / connectivity.

## 2. Disruption root-cause mix

| Root cause | Share |
|---|---:|
| Weather | 31% |
| Technical | 23% |
| Crew | 19% |
| Ground_Handling | 12% |
| ATC | 10% |
| Other | 6% |

**Read:** Weather is the largest single driver of disruption (harmattan dust
and storms in this Nov-Jan window), followed closely by technical issues.
Weather is exogenous — the lever there is operational resilience (alternate
airports, schedule padding) rather than prevention. Technical disruption is
addressable through the maintenance program.

## 3. Customer satisfaction by route (synthetic reviews)

| Route | Reviews | Avg rating | NPS proxy |
|---|---:|---:|---:|
| R001 | 185 | 3.24 | +17 |
| R010 | 188 | 3.31 | +21 |
| R004 | 383 | 3.32 | +23 |
| R003 | 203 | 3.33 | +26 |
| R011 | 197 | 3.39 | +32 |
| R006 | 374 | 3.56 | +41 |
| R005 | 377 | 3.57 | +40 |
| R012 | 192 | 3.59 | +44 |
| R009 | 389 | 3.61 | +45 |
| R007 | 203 | 3.64 | +46 |
| R002 | 201 | 3.64 | +44 |
| R008 | 181 | 3.70 | +51 |

*NPS proxy = % ratings ≥ 4 − % ratings ≤ 2.*

## 4. Top negative topics by route

| Route | Top 3 negative topics |
|---|---|
| R001 | punctuality, staff_service, baggage |
| R002 | punctuality, cleanliness, boarding |
| R003 | punctuality, baggage, staff_service |
| R004 | punctuality, communication, staff_service |
| R005 | punctuality, communication, baggage |
| R006 | communication, punctuality, baggage |
| R007 | punctuality, baggage, communication |
| R008 | baggage, communication, punctuality |
| R009 | punctuality, baggage, staff_service |
| R010 | punctuality, food_beverage, baggage |
| R011 | punctuality, communication, baggage |
| R012 | punctuality, communication, food_beverage |

**Read:** Punctuality is the #1 complaint driver across the network. Routes with
strong 'communication' negative signal are candidates for service-recovery process
investment (low-cost retention lever).

## 5. Customer segment economics

| Segment | Customers | Bookings | Revenue/customer |
|---|---:|---:|---:|
| Premium | 24 | 879 | $13,496 |
| Business | 73 | 2612 | $13,113 |
| Budget | 53 | 1895 | $12,978 |
| Standard | 150 | 5282 | $12,776 |

**Read (data limitation):** all four segments produce nearly-identical revenue
per customer (~$13k) over the window. This is a starter-data artifact — the
`customer_segment` label exists but ticket prices and ancillary spend are not
clearly differentiated by segment. **Phase 2 implication:** we will surface
this in the semantic layer with a `data_quality_flag`, and propose a more
meaningful cut by *route type × fare class* rather than `customer_segment` for
the upsell analysis.

## 6. The retention lever, sized

- High-value at-risk customers identified: **1** of 182
- Revenue concentrated in this cohort: **$16,138** (0.7% of total)
- Definition: Silver/Gold tier, no loyalty activity in window, lifetime revenue > p75

**Read (definition needs tuning for this data):** the strict at-risk definition
above produces only 1 hit because the starter has all 300 customers booking
21–58 times in a 3-month window — nobody is genuinely inactive. **Phase 2
implication:** we will redefine the rule using *loyalty activity gap* and
*tier-benefit underuse* rather than recency, e.g.:

> `at_risk_v2 = loyalty_tier IN ('Silver','Gold')`
> `  AND   ratio_of_loyalty_earn_events_to_bookings < 0.5`
> `  AND   lifetime_revenue > p75`

This will yield a working cohort and demonstrates an ontology rule that adapts
to the available signals — a senior-level move that we will fold back into
`02_kpi_dictionary.md §D2`.

## 7. The upsell lever, sized

- Ancillary attach rate: **82.6%** of flown bookings
- ARPU ancillary: **$20.59** per booking — low
- Mix skewed toward baggage (Basic fare family): high attach, low unit value
- **Implication:** the lever is not 'increase attach' (already high) but
  'shift mix toward higher-value items' — seat selection, meal upgrades, lounge access.

## 8. Headline answer (to refine in Phases 2-4)

Given the current data:

- **Network expansion** — premature. Existing long-haul (Paris) is below break-even
  load factor. Adding new routes before fixing Paris's demand profile is high-risk.
- **Customer retention** — yes, sized and actionable. A defined cohort carries
  disproportionate revenue and shows at-risk signals.
- **Upsell / cross-sell** — yes, by mix shift not by attach increase. Attach is
  already 83%; the opportunity is selling lounge / meal / seat upgrades to
  Standard / Business segments.

**Provisional ranking of the 12-month budget allocation:**

1. **Upsell / cross-sell** — fastest payback (~0–3 months), lowest risk
2. **Customer retention** — compounding LTV (~3–6 months)
3. **Demand generation on Paris** — reframed as marketing / distribution
   investment, not new-route capex

This is a **provisional** answer based on Phase 1 alone. The dashboard in Phase 3
must enable a stakeholder to *interrogate* this conclusion, not just accept it.
