# Part 1 — Business Understanding and Data Generation

> Response to the Artefact Analytics Engineer challenge for Air Côte d'Ivoire.
> This document maps 1-to-1 to the four bullets of Part 1 in the brief.

---

## 1.1 — Airline business domains relevant to the decision question

The decision question — *where to allocate 12-month budget across route
expansion, customer retention, or upsell* — touches **five business domains**
that operate together. Modeling fewer than these breaks the decision logic.

| Domain | Core entities | Why it matters for the decision |
|---|---|---|
| **Network** | Routes, frequencies, schedules, slots | Defines *where* we can compete; expansion lever lives here |
| **Operations** | Flights, aircraft assignment, disruptions | Translates the schedule into cost and reliability; broken ops kill margin and retention |
| **Commercial** | Bookings, fares, channels, fare families | Translates capacity into revenue; pricing and channel mix decisions |
| **Customer** | Profiles, segments, loyalty tiers, engagement | Defines *who* flies; retention lever lives here |
| **Ancillary** | Bag / seat / meal / lounge / upgrade products | Drives margin per passenger; upsell lever lives here |

The three competing levers in the brief map to these domains:

- **Network expansion** → Network + Operations + Commercial
- **Customer retention** → Customer + Operations (reliability drives churn)
- **Upsell / cross-sell** → Ancillary + Commercial + Customer

This is why all five domains have to be in the model simultaneously: the
levers cut across the domains, they don't sit inside one.

**Decision makers** the analytics product must serve:

- **CEO** — capital allocation across the 3 levers (portfolio view)
- **Chief Commercial Officer** — fare strategy, channel mix
- **Chief Network Officer** — route opening / dropping / frequency
- **VP Loyalty & CRM** — retention campaigns, tier strategy
- **VP Customer Experience** — service investments, NPS proxy
- **VP Revenue Management** — ancillary pricing, upgrade rules

Each of these has a *different question* and a *different cut* of the same
underlying model — which is why the semantic layer in Phase 2 matters.

---

## 1.2 — KPIs that should guide the decision

The KPIs are grouped by the three levers + a cross-cutting layer. Granularity
codes: **R** = per route, **C** = per customer, **F** = per flight, **M** =
per month, **G** = global.

### A. Network & Profitability (network-expansion lever)

| KPI | Formula | Granularity |
|---|---|---|
| Route Revenue (USD) | `Σ(ticket_price + ancillary)` over Flown/Confirmed bookings | R, M |
| Route Operating Cost (USD) | `Σ(fuel + crew + airport + nav + handling)` per flight | R, M |
| Route Margin USD / % | `Revenue − Cost`, then `/ Revenue` | R, M |
| Load Factor | `RPK / ASK` = `Σ(pax × distance) / Σ(seats × distance)` | R, F |
| Yield (USD / RPK) | `Revenue / RPK` | R, M |
| RASK vs CASK | `Revenue / ASK` minus `Cost / ASK` | R, M |
| On-Time Performance | `count(delay ≤ 15min AND not cancelled) / count(flights)` | R, F |
| Cancellation Rate | `count(cancelled) / count(flights)` | R, M |
| Average Delay (min) | `AVG(delay_min) WHERE status='Delayed'` | R, M |

### B. Customer & Retention (retention lever)

| KPI | Formula | Granularity |
|---|---|---|
| Customer Lifetime Revenue (USD) | `Σ(ticket + ancillary)` per customer | C |
| Repeat Booking Rate | `customers with ≥2 bookings / total customers` | G |
| Active Loyalty Penetration | `loyalty_tier ≠ None AND any loyalty txn in last 90d / total` | G |
| Days Since Last Booking | `today − MAX(booking_date)` | C |
| **At-Risk Customer Flag** | `Silver/Gold tier AND no recent loyalty activity AND lifetime_rev > p75` | C |
| Average Review Rating | `AVG(rating)` over reviews | R, M |
| NPS Proxy | `% ratings ≥ 4 − % ratings ≤ 2` | R, M |
| Negative-Topic Share | `count(reviews topic=X AND rating ≤ 2) / count(negative reviews)` | R, topic |
| Support Ticket Rate | `count(tickets) / count(flown bookings)` | R, M |

### C. Upsell & Cross-Sell (upsell lever)

| KPI | Formula | Granularity |
|---|---|---|
| Ancillary Attach Rate | `count(bookings with ancillary > 0) / count(bookings)` | R, segment |
| ARPU Ancillary (USD) | `Σ(ancillary_revenue) / count(bookings)` | R, segment |
| Item-Level Attach | `count(bookings with item X) / count(bookings)` for X ∈ {bag, seat, meal, lounge, priority, upgrade} | item |
| Upgrade Conversion | `count(Economy → Business upsells) / count(eligible Economy)` | R |
| Premium Cabin Share | `count(Premium Eco + Business bookings) / count(bookings)` | R |
| Channel Margin Proxy | `(Revenue − channel commission) / Revenue` | channel |

### D. Cross-cutting / strategic (ontology rules)

| KPI | Definition |
|---|---|
| **Strategic but Underperforming Route** | `route_type IN ('International','Regional') AND ASK_share > 5% AND Margin% < 0` |
| **High-Value At-Risk Customer** | `at_risk_flag = TRUE AND customer_segment IN ('Business','Premium')` |
| **Upsell-Ready Segment** | `fare_class = 'Economy' AND lifetime_revenue > p60 AND ancillary_attach < 50%` |

These four "rule-defined" concepts are what allows the AI assistant (Phase 4)
to answer questions like *"which customers are high-value and at risk?"* with
a single, auditable definition — rather than asking the user to specify
thresholds every time.

The full dictionary with naming conventions, dbt tests, and join keys is in
`docs/02_kpi_dictionary.md`.

---

## 1.3 — Synthetic data generated (including the unstructured source)

The starter dataset gives us **exposure** (flights, bookings, customers) but
not **economics** (no costs), not **behavior beyond transactions** (no
reviews, no loyalty activity, no service interactions). The decision question
cannot be answered without those, so we add nine synthetic datasets.

**All generation is deterministic** (`SEED = 42`) — re-running the script
produces byte-identical CSVs.

| Dataset | Rows | Type | Lever served | Why we need it |
|---|---:|---|---|---|
| `aircraft_fleet` | 4 | Static reference | Network | Cost per block hour, fuel burn — no margin without this |
| `fuel_prices_monthly` | 3 | Static reference | Network | Fuel is 25–35% of variable cost |
| `ancillary_catalog` | 14 | Static reference | Upsell | Item master for cross-sell analysis |
| `route_operating_costs` | 480 | Derived (per flight) | Network | Per-flight cost decomposition → route P&L |
| `ancillary_purchases` | 11,731 | Derived (per booking) | Upsell | Decomposes bookings.ancillary into items |
| `loyalty_transactions` | 3,953 | Behavioral | Retention | Engagement signal, ~20% dormant cohort |
| `disruption_log` | 145 | Operational | Network + Retention | Root cause for each delayed / cancelled flight |
| `support_tickets` | 35 | Behavioral | Retention | Mid-journey friction signal |
| **`customer_reviews`** | **3,073** | **Unstructured ⭐** | All three | Sentiment + topic themes by route |

### The unstructured source: `customer_reviews`

This is the dataset that makes the brief's requirement of *"at least one
unstructured dataset"* count for real, because:

1. It links directly to operations via `flight_id` — we can join a complaint
   to the disruption that caused it.
2. It supports both **sentiment** (rating 1–5) and **topic** analysis
   (controlled vocabulary tags: punctuality, cabin_comfort, food_beverage,
   staff_service, cleanliness, baggage, value_for_money, boarding,
   entertainment, communication).
3. It feeds the Phase 4 MCP server with semantic-search material: "what are
   customers complaining about on the Dakar route?" becomes answerable.

**Generation logic:**

- ~35% of `Flown` bookings receive a review (industry-realistic response rate).
- Rating is **conditioned on flight outcome and fare class**:

  | Scenario | Mean rating | Std |
  |---|---:|---:|
  | On-time + Business class | 4.2 | 0.7 |
  | On-time + Premium Economy | 4.0 | 0.8 |
  | On-time + Economy | 3.8 | 0.9 |
  | Delayed flight | 2.5 | 1.0 |
  | Cancelled flight (rebooked) | 1.8 | 0.8 |

- Topics are drawn from a route-aware pool (long-haul mentions cabin/food,
  regional mentions punctuality), with negative ratings biased toward
  complaint-heavy topics.
- Review text is **template-blended**: each topic has positive and negative
  sentence pools; the composer picks based on the rating then adds a closing.

**Validation evidence** that the signal is meaningful (not noise):

- `Σ ancillary_purchases.total_price_usd` ≡ `Σ bookings.ancillary_revenue_usd`
  exactly ($236,616, zero diff). Internal consistency holds.
- Rating × flight_status correlation: On-Time mean **3.85★**, Delayed mean
  **2.53★** — clean separation, not random noise.
- Top complaint topics (rating ≤ 2): punctuality (260), baggage (153),
  staff_service (140), communication (130) — realistic airline complaint mix.

### Sample reviews

A 1-star and a 5-star review from the generated set:

> **[rating=1] topics=[punctuality]**
> *"Departed over an hour late and I missed my connection. Will avoid this
> airline next time."*

> **[rating=5] topics=[staff_service; entertainment; baggage]**
> *"Cabin crew were friendly and professional. IFE worked well throughout the
> flight. Bags arrived quickly at the carousel. Highly recommend this airline."*

The full generation logic and rules per dataset are in
`docs/03_data_enrichment_plan.md`.

---

## 1.4 — Assumptions and why the added data is useful

### 1.4.a — The assumptions that matter

Every analytical claim in this submission rests on these:

1. **Time window.** Starter flights cover Jan 2025 only (30 days, 480 flights);
   bookings span Nov 2024 → Jan 2025. Seasonal effects cannot be observed. We
   treat the window as "current state" and don't extrapolate annual figures.

2. **Currency.** Everything in USD. In reality, domestic and regional sales
   would be in XOF; a production model would join `dim_fx` and convert at
   booking-date rates.

3. **Cost benchmarks (synthetic) are calibrated to industry ranges, not
   Air CI actuals.** The A330neo at $9,500/block hour and the A320neo at
   ~10% fuel advantage over the A320 are publicly-published orders of
   magnitude. Margin **rankings** are robust; absolute USD should be read
   as relative signals.

4. **Load factor caveat (important).** The starter has ~22 passengers per
   flight on average, which implies load factors of 5–20% for these aircraft.
   This is not commercially realistic. We do not synthesize additional
   bookings because:
   - A reviewer would notice ~10,000 fictional bookings.
   - Margin **%** (not absolute USD) and unit metrics (RASK − CASK) are
     comparable across routes regardless of pax volume.

   This shows up in the Paris route appearing at −87% margin: the issue is
   underused capacity on a brand-new long-haul, not structural unprofitability.
   The recommendation reframes accordingly: *demand generation* before
   network expansion.

5. **All 300 customers in the starter have 21–58 bookings.** That's not a
   real customer base — it's an over-sampled active cohort. We don't modify
   it, but we introduce realistic variance via `loyalty_transactions`:
   ~20% of loyalty members get no activity, giving us a defensible "dormant"
   cohort for the at-risk flag.

6. **Reviews are English-only and template-blended.** A production system
   would need French support (~40% of the customer base) and would benefit
   from LLM-generated diversity. The schema has a `language` column so a
   multi-lingual extension is straightforward.

7. **Disruption attribution is simplified to one root cause per flight.**
   Real disruptions often have cascading causes; we collapse to the primary.

Full list in `docs/04_assumptions.md`.

### 1.4.b — Why the added data matters

Each added dataset *unlocks an answer* that the starter alone cannot provide:

| Without the added data | With the added data |
|---|---|
| We know which routes carry the most pax | We know which routes **make money** (cost decomposition) |
| We know flights are delayed | We know **why** they're delayed (weather vs technical vs crew) |
| We know loyalty tier as a label | We know who is **engaged** vs **dormant** (activity) |
| We know total ancillary $ per booking | We know **which products** sell (baggage vs lounge vs upgrade) |
| We have no satisfaction signal | We have **rated, topic-tagged reviews** linked to operations |
| We have no service-load signal | We have **support tickets** by category and severity |

The two highest-leverage additions are:

- **Cost data** — turns a revenue chart into a profitability chart. Without
  it, the entire network-expansion conversation is uninformed.
- **Customer reviews** — turns operations data into a *customer-perceived*
  view. The same OTP drop has very different business meaning depending on
  whether customers complain about "delay" vs "communication during the
  delay" — the second is a low-cost retention fix.

### 1.4.c — Headline answer (provisional, to refine in later phases)

Joining the starter with the enrichments already reveals:

- Regional routes (Accra, Cotonou, Dakar at scale) are the profitability
  backbone (+9% to +33% margin).
- Paris is structurally underused — the lever is demand generation, not
  network expansion.
- Punctuality is the #1 complaint driver network-wide; communication during
  disruptions is the #2 → low-cost retention investment.
- Ancillary attach is already high (83%), so the upsell lever is **mix
  shift** (toward lounge / meal / seat) rather than attach-rate growth.

**Provisional ranking of the 12-month budget allocation:**

1. **Upsell / cross-sell** — fastest payback (~0–3 months), lowest risk
2. **Customer retention** — compounding LTV (~3–6 months)
3. **Demand generation on Paris** — reframed as marketing / distribution,
   not new-route capex

Network expansion to new destinations is **premature** until Paris is filled.

The dashboard in Phase 3 must let stakeholders interrogate this conclusion,
not just accept it.

---

## Reproducibility

The full synthetic dataset is regenerated by a single command from the
starter file:

```bash
python scripts/generate_synthetic_data.py \
    --starter data/starter/air_cote_divoire_starter_dataset.xlsx \
    --out-dir data/synthetic/
```

The script is documented inline. All randomness uses `SEED = 42`. Total
runtime: ~10 seconds on a laptop.

## Supporting documents

| File | Content |
|---|---|
| `docs/01_business_framing.md` | Long-form strategic context, hypotheses, decision-maker matrix |
| `docs/02_kpi_dictionary.md` | Full KPI dictionary with joins, naming conventions, dbt tests |
| `docs/03_data_enrichment_plan.md` | Per-dataset rationale and generation rules |
| `docs/04_assumptions.md` | Every assumption, including the load-factor caveat |
| `docs/05_phase1_preview_insights.md` | What the data already reveals (P&L, NPS, at-risk sizing) |
| `scripts/generate_synthetic_data.py` | Deterministic synthetic-data generator |
| `data/synthetic/enriched_dataset.xlsx` | All sheets in one file (starter + synthetic) |
