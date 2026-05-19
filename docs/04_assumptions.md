# Air Côte d'Ivoire — Assumptions

Every analytical artifact in this submission rests on a stack of assumptions.
Listing them here makes the work defensible and easy for a reviewer (or a
business stakeholder) to challenge specifically.

## 1. Time window

- **Operations window:** the starter dataset covers flights in **January 2025**
  only (480 flights). All margin / OTP analysis is computed over this window.
- **Booking window:** bookings span **2024-11-02 → 2025-01-29** (~3 months).
- **Loyalty / review window:** synthetic loyalty and review events are
  generated within the same window so all data is internally consistent.
- **Implication:** seasonal effects cannot be observed. We treat the window
  as "current state" and surface trade-offs accordingly. A 12-month dataset
  would be required to model true seasonality (e.g., harmattan vs rainy
  season impact on operations).

## 2. Currency, units, formatting

- All monetary values are in **USD**, including the starter `ticket_price_usd`
  and `ancillary_revenue_usd`. We assume Air CI uses USD as its commercial
  reporting currency for international routes; in reality, domestic and
  regional sales would be in XOF. This is a deliberate simplification — a
  production model would join a `dim_fx` table and convert at booking-date
  rates.
- Distances in **kilometers**, durations in **minutes**.
- Percentages stored as decimals; formatted in BI.

## 3. Cost economics (synthetic)

The cost benchmarks in `aircraft_fleet` and `route_operating_costs` are
**approximations based on publicly-published industry ranges**, not actual
Air CI figures. They are designed so that:

- Long-haul (Paris) has high absolute cost but the best unit economics
  *when load factor is healthy*.
- Domestic routes have the worst unit economics on a fully-allocated basis,
  consistent with industry reality for short-stage flag carriers.
- The A320neo shows a ~10–15% fuel advantage vs the A320, matching real
  fleet economics.

**Implication:** absolute margin numbers should be read as *relative
signals*, not commitments. A senior analyst reading this submission should
recognize the orders of magnitude are right but the precise values are
synthetic.

## 3 bis. Passenger volume limitation (IMPORTANT)

The starter dataset contains **~25 passengers per flight on average** (11,475
bookings across 480 flights). For aircraft with 122–242 seats, this implies
load factors of **5–20%**, which is **not commercially realistic** for a
flag carrier.

After running the cost model, this manifests as the Paris route (R009,
A330-900neo) showing ~$1.3M loss over the window — driven almost entirely
by underused capacity, not by structural unprofitability.

We make this explicit rather than synthesizing more bookings, for two
reasons:

1. **Defensibility.** A reviewer would notice that ~10,000 added bookings
   appeared out of nowhere. Honest framing is stronger than padded analysis.
2. **Analytical value.** Margin **percentage** (KPI A4) and unit metrics
   (RASK − CASK, KPI A11) remain comparable across routes regardless of
   absolute pax volume, and the route ranking they produce is robust.

**Where this matters in the recommendations:**

- We do NOT recommend pulling the Paris route based on this data. We frame
  the question as *"can demand be grown to fill the A330neo to 70%+?"* —
  which is the real-world question for a launched long-haul route.
- We propose a "load factor scenario" view in the dashboard: for each route,
  show actual margin and pro-forma margin at 65% / 75% load factor.

## 4. Customer base (starter)

- 300 customers, all with 21–58 bookings in the window. This is **not
  realistic** — a real flag carrier has a long tail of one-time customers.
- We do not modify the starter data, but we **introduce variance** via
  `loyalty_transactions`: ~20% of loyalty members have no activity, which
  gives us a realistic "dormant" cohort to flag as at-risk.
- The repeat-booking rate (100% by construction) is **not used** as a
  reported KPI — it would be misleading. Instead, we report
  `active_loyalty_penetration` and `days_since_last_booking`.

## 5. Reviews (synthetic, English-only)

- Rating distribution is conditioned on flight outcome (on-time vs
  delayed vs cancelled) and fare class. This is deliberate: it makes the
  sentiment signal *useful* — joining reviews to operations reveals
  causal patterns rather than random noise.
- Text is **template-blended**, not LLM-generated. The vocabulary is
  small but topic-tagged consistently, which makes downstream sentiment
  and topic modeling tractable in the time budget of this challenge.
- Reviews are **English only**. In production, ~40% of Air CI's customer
  base would write in French. The semantic-layer design assumes a
  `language` column so a multi-lingual extension is straightforward.

## 6. Loyalty mechanics

- Tier mapping (assumed):
  - **Explorer:** entry tier, 0–9,999 miles in last 12M
  - **Silver:** 10,000–49,999 miles
  - **Gold:** 50,000+ miles
- Earn multiplier: Explorer 1×, Silver 1.25×, Gold 1.5× per USD spent
- The starter has `loyalty_tier` as a static attribute. We treat it as
  the customer's current tier and reconstruct activity around it.

## 7. Ancillary decomposition

- The starter has `ancillary_revenue_usd` as a single number per booking.
- We assume each booking can be decomposed into 0–3 line items from the
  ancillary catalog, with item probabilities depending on `fare_family`.
- This decomposition is **reversible**: the sum of `total_price_usd` in
  `ancillary_purchases` per booking equals the original
  `ancillary_revenue_usd` (subject to small rounding).

## 8. Disruption attribution

- Every Delayed / Cancelled flight gets exactly one `disruption_log` row.
- Multi-cause disruptions are simplified to a single primary `root_cause`.
- The mix of root causes is calibrated to be realistic for a West African
  airline operating in tropical conditions during the harmattan season
  (December–February), where dust and visibility cause meaningful
  weather-driven disruption.

## 9. Out-of-scope simplifications

| Topic | Simplification | Real-world implication |
|---|---|---|
| Code-share / interline | Ignored | Real revenue mix would include partner-fare leakage |
| Tax & airport duties | Bundled into `airport_fees` | Real reporting separates them |
| Fuel hedging | Ignored | Could change route P&L by ±5% |
| Cargo revenue | Ignored | Significant for long-haul P&L in reality |
| Loyalty deferred revenue | Ignored | Real airlines defer revenue for unredeemed miles |
| Crew complement variation | Standard per aircraft type | Long-haul has multiple crews; we approximate |
| Multi-class ancillary mix | Coarse | Business-class buyers behave very differently |

## 10. Reproducibility

- All synthetic generation uses a fixed random seed (`SEED = 42`).
- Re-running `generate_synthetic_data.py` produces byte-identical output.
- The starter Excel file is **never written to**; outputs go to
  `data/synthetic/*.csv` (and a combined `enriched_dataset.xlsx`).
