# Air Côte d'Ivoire — Data Enrichment Plan

The starter dataset gives us *exposure* (flights, bookings, customers) but
not *economics* (no costs), not *behavior beyond transactions* (no reviews,
no loyalty activity, no service interactions), and no *competitive context*.

This document explains every synthetic dataset we add, **why** it is needed
for the decision question, and the **rules** used to generate it. All
synthetic data is deterministic (seeded) so the pipeline is reproducible.

---

## 1. `aircraft_fleet` — fleet master with operating economics

**Why we need it.** No margin calculation is possible without cost per
block hour. Different aircraft types have very different unit economics: a
fully-loaded A330neo can be cheaper per seat than a half-empty A319 on the
same route.

**Schema**
```
aircraft_type (PK), manufacturer, seats_total, seats_business, seats_premium_eco,
seats_economy, fuel_burn_kg_per_hour, cost_per_block_hour_usd, crew_cost_per_hour_usd,
introduced_year, fleet_count
```

**Rules used**
- A319: 122 seats, 2,400 kg/hr fuel burn, $4,200 per block hour
- A320: 150 seats, 2,500 kg/hr, $4,500 per block hour
- A320neo: 165 seats, 2,100 kg/hr (newer, more efficient), $4,300 per block hour
- A330-900neo: 242 seats, 5,500 kg/hr, $9,500 per block hour

These approximate widely-published industry benchmarks; the absolute numbers
are less important than the *relative* economics, which drive routing
decisions. Cabin configurations are split realistic for a flag carrier.

## 2. `fuel_prices_monthly` — jet fuel price reference

**Why we need it.** Fuel is 25–35% of an airline's variable cost. A 10%
swing changes route P&L conclusions.

**Schema**
```
year_month (PK), jet_fuel_usd_per_kg, jet_fuel_usd_per_gallon
```

**Rules**
- Three months (Nov 2024 → Jan 2025) matching booking window
- Slight upward trend ($0.82 → $0.88 per kg)
- Static across routes (fuel cost varies by airport but we keep it simple)

## 3. `route_operating_costs` — per-flight cost components

**Why we need it.** Decomposing cost by component lets us attribute *why*
a route is unprofitable: fuel? airport fees? handling? Each suggests a
different action (sourcing vs negotiation vs frequency reshape).

**Schema**
```
flight_id (PK), fuel_cost_usd, crew_cost_usd, airport_fees_usd,
nav_fees_usd, handling_cost_usd, total_operating_cost_usd
```

**Rules** (derived from `flights` + `aircraft_fleet` + `fuel_prices`)
- `fuel_cost = block_hours × fuel_burn_kg_per_hour × fuel_price_per_kg`
- `crew_cost = block_hours × crew_cost_per_hour` (higher for long-haul)
- `airport_fees`:
  - Domestic ABJ: $450
  - Regional African: $1,200 (each way)
  - International CDG: $5,000
- `nav_fees = 0.15 × distance_km × (seat_capacity / 100)` (approx)
- `handling_cost = $250 × (seat_capacity / 100)` per turn

## 4. `ancillary_purchases` — itemized ancillary revenue

**Why we need it.** The starter has total ancillary revenue per booking
but no breakdown. Upsell strategy depends on *which* products convert.
A high baggage attach with zero seat-selection attach is a very different
opportunity than the inverse.

**Schema**
```
ancillary_purchase_id (PK), booking_id (FK), item_type, item_name,
quantity, unit_price_usd, total_price_usd
```

**Rules**
- Each booking's `ancillary_revenue_usd` is decomposed into 0–3 items
- Item probabilities depend on `fare_family`:
  - Basic: high baggage probability (no bag included)
  - Standard: medium across all
  - Flex: high lounge / priority probability
- Item prices drawn from `ancillary_catalog`

## 5. `ancillary_catalog` — product master

**Schema**
```
item_id (PK), item_type, item_name, base_price_usd, applies_to_route_type
```

Items: Extra Bag ($25–50), Seat Selection ($8–35), Meal Upgrade ($12–30),
Lounge Access ($35–80, regional/intl only), Priority Boarding ($10–15),
Cabin Upgrade ($80–600 depending on route).

## 6. `loyalty_transactions` — miles activity (THE retention signal)

**Why we need it.** The `loyalty_tier` field is static. We need *activity*
to flag truly engaged vs dormant members and to drive the at-risk rule.

**Schema**
```
loyalty_txn_id (PK), customer_id (FK), txn_date, txn_type (Earn/Redeem),
miles_amount, related_booking_id (nullable), description
```

**Rules**
- For customers with `loyalty_tier ≠ None`: generate Earn events for
  ~70% of their bookings (1 mile per $1 spent, scaled by tier multiplier)
- Generate occasional Redeem events (5–10% of customers per quarter)
- ~20% of loyalty customers receive NO activity in our window → these
  are the "dormant" cohort, the target of retention campaigns

## 7. `customer_reviews` ⭐ — the unstructured source

**Why we need it.** The brief explicitly requires at least one
unstructured dataset, and reviews are the highest-value choice because
they (a) link directly to operations via `flight_id`, (b) drive customer
satisfaction analysis at route granularity, and (c) provide rich material
for the MCP server's RAG / semantic search demo.

**Schema**
```
review_id (PK), booking_id (FK), customer_id (FK), flight_id (FK),
review_date, rating (1-5), review_text, language, topics
```

**Generation rules**
- ~35% of `Flown` bookings receive a review (industry-realistic response rate)
- Rating distribution is **conditional on flight outcome**:
  - On-time flight + Business class → mean 4.2, std 0.7
  - On-time flight + Economy → mean 3.8, std 0.9
  - Delayed (≥30min) → mean 2.5, std 1.0
  - Cancelled (rebook later) → mean 1.8, std 0.8
- Review text composed from topic-keyed templates blended with route-aware
  modifiers (long-haul mentions cabin/food, regional mentions punctuality,
  domestic mentions value-for-money)
- Each review tagged with 1–3 topics from a controlled vocabulary:
  `punctuality, cabin_comfort, food_beverage, staff_service, cleanliness,
  baggage, value_for_money, boarding, entertainment, communication`
- Language: 100% English for tractable downstream NLP. (Note: in
  production, French support would be required given the customer base.)

**Why this is the highest-leverage dataset.** It is the only one that
lets us answer questions like *"why does route X have low NPS even though
its OTP is good?"* — the answer might be "because food is rated poorly,"
which is invisible in structured data alone. This is also the dataset that
drives the strongest MCP demo (semantic search over text).

## 8. `support_tickets` — service interactions

**Why we need it.** Reviews capture post-flight sentiment; tickets capture
mid-journey friction. The two together give a much richer satisfaction
view. Tickets also expose *channel cost* of poor operations.

**Schema**
```
ticket_id (PK), customer_id (FK), related_booking_id (FK, nullable),
related_flight_id (FK, nullable), open_date, close_date, channel,
category, severity, status, resolution_hours
```

**Rules**
- ~8% of customers raise at least one ticket in the window
- Categories: `Baggage` (35%), `Schedule_Change` (25%), `Refund_Request`
  (15%), `Loyalty` (10%), `Booking_Issue` (10%), `Other` (5%)
- Severity tied to category (Baggage tends to be Medium; Refund tends to
  be High)
- Resolution hours drawn from log-normal, faster for high-severity

## 9. `disruption_log` — root cause for delays/cancellations

**Why we need it.** Knowing *why* a flight was disrupted is essential
to the recommendations. A route delayed by weather is a different problem
than one delayed by aircraft availability.

**Schema**
```
disruption_id (PK), flight_id (FK), root_cause, sub_cause,
description, recovery_action
```

**Rules**
- Generated for every flight with `status IN ('Delayed','Cancelled')`
- Root causes weighted realistic for tropical West African ops:
  - `Weather` (25%) — storms, harmattan dust season
  - `Technical` (30%) — aircraft availability
  - `Crew` (15%) — duty time, illness
  - `ATC` (10%) — congestion at CDG / LOS
  - `Ground_Handling` (15%) — baggage, fuel truck
  - `Other` (5%)

---

## Datasets considered but not generated

| Dataset | Why we skipped (for mid-level scope) |
|---|---|
| Weather observations | Could enrich disruption analysis, but the `disruption_log.root_cause` field captures the signal directly. Adding weather adds modeling complexity without changing recommendations. |
| Crew rosters | Out of scope per `01_business_framing.md` §7. |
| Competitor capacity | Would strengthen the network-expansion recommendation. Worth adding if time permits — listed as a "next step". |
| Multi-currency / FX | All values stay in USD. |
| Multi-year history | The starter window is 3 months; extending requires re-modeling seasonality. Listed as a "next step". |
