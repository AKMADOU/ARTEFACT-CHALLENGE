# Air Côte d'Ivoire — KPI Dictionary

This dictionary defines the metrics used in the analytics product. Each KPI has
a precise formula, granularity, and owner so it can be implemented in dbt
metrics, joined to dimensions consistently, and surfaced in the dashboard.

Granularity codes: **F** = per flight, **R** = per route, **C** = per customer,
**M** = per month, **G** = global.

---

## A. Network & Profitability

| # | KPI | Formula | Granularity | Why it matters |
|---|---|---|---|---|
| A1 | **Route Revenue** | `Σ(ticket_price_usd + ancillary_revenue_usd)` over bookings with `status IN ('Flown','Confirmed')` | R, M | Top-line per route |
| A2 | **Route Operating Cost** | `Σ(fuel_cost + crew_cost + airport_fees + nav_fees + handling) per flight on route` | R, M | Allocated cost base |
| A3 | **Route Margin USD** | `Route Revenue − Route Operating Cost` | R, M | Bottom-line per route |
| A4 | **Route Margin %** | `Route Margin USD / Route Revenue` | R, M | Profitability ratio, comparable across route scale |
| A5 | **ASK** (Available Seat Kilometers) | `Σ(seat_capacity × distance_km)` over flights | R, M | Capacity offered |
| A6 | **RPK** (Revenue Passenger Kilometers) | `Σ(pax_flown × distance_km)` | R, M | Capacity sold |
| A7 | **Load Factor** | `RPK / ASK` | R, F, M | % of seats sold; the single most-watched airline KPI |
| A8 | **Yield** | `Route Revenue / RPK` (USD per RPK) | R, M | Revenue per unit of carried demand |
| A9 | **RASK** | `Route Revenue / ASK` | R, M | Revenue per unit of capacity |
| A10 | **CASK** | `Route Operating Cost / ASK` | R, M | Cost per unit of capacity |
| A11 | **RASK − CASK spread** | `A9 − A10` | R, M | Unit profitability, the cleanest profitability signal |
| A12 | **On-Time Performance (OTP)** | `count(flights WHERE delay_min ≤ 15 AND status != 'Cancelled') / count(flights)` | R, F (rollup), M | Industry-standard 15-min threshold |
| A13 | **Cancellation Rate** | `count(flights WHERE status='Cancelled') / count(flights)` | R, M | Operational reliability |
| A14 | **Average Delay (min)** | `AVG(delay_min) WHERE status='Delayed'` | R, M | Severity of disruption |
| A15 | **Disruption-Driven Revenue Loss** | `Σ(cancelled_flights × avg_route_revenue_per_flight)` | R, M | Cost of unreliability |

## B. Customer & Retention

| # | KPI | Formula | Granularity | Why it matters |
|---|---|---|---|---|
| B1 | **Customer Lifetime Revenue** | `Σ(ticket_price + ancillary) per customer` | C | Proxy for LTV in absence of multi-year data |
| B2 | **Repeat Booking Rate** | `count(customers with ≥2 bookings) / count(customers)` | G, segment | Health of the base |
| B3 | **Active Loyalty Penetration** | `count(customers with loyalty_tier ≠ None AND any loyalty txn last 90d) / count(customers)` | G | Real engagement, not just sign-up |
| B4 | **Tier Mix** | `count(customers per tier) / count(customers)` | G | Distribution across Explorer / Silver / Gold |
| B5 | **Days Since Last Booking** | `today − MAX(booking_date) per customer` | C | Recency, input to at-risk flag |
| B6 | **At-Risk Customer Flag** | `loyalty_tier IN ('Silver','Gold') AND B5 > 120 AND lifetime_revenue > p75` | C | The retention lever's target list |
| B7 | **No-Show Rate** | `count(bookings status='No Show') / count(bookings status IN ('Flown','No Show'))` | R, segment | Both a behavior and a revenue leak |
| B8 | **NPS Proxy** | `(% reviews rating ≥ 4) − (% reviews rating ≤ 2)` | R, M | Net Promoter approximation from reviews |
| B9 | **Average Review Rating** | `AVG(rating) over reviews` | R, M, aircraft | Satisfaction signal |
| B10 | **Negative Review Topic Share** | `count(reviews with topic=X AND rating ≤ 2) / count(reviews rating ≤ 2)` | R, topic | What drives dissatisfaction |
| B11 | **Support Ticket Rate** | `count(tickets) / count(flown bookings)` | R, M | Service load per route |

## C. Upsell & Cross-sell

| # | KPI | Formula | Granularity | Why it matters |
|---|---|---|---|---|
| C1 | **Ancillary Attach Rate** | `count(bookings with ancillary_revenue > 0) / count(bookings)` | R, segment | % of pax buying anything beyond ticket |
| C2 | **ARPU Ancillary** | `Σ(ancillary_revenue) / count(bookings)` | R, segment | Avg ancillary $ per booking |
| C3 | **Item Attach Rate by Type** | `count(bookings buying item X) / count(bookings)` per item in `{bag, seat, meal, lounge, priority, upgrade}` | item, segment | Which ancillaries actually sell |
| C4 | **Upgrade Conversion** | `count(bookings with fare_class='Business' AND original_fare='Economy') / count(eligible Economy bookings)` | R, segment | Premium upsell efficiency |
| C5 | **Premium Cabin Share** | `count(bookings fare_class IN ('Premium Economy','Business')) / count(bookings)` | R | Mix of high-yield seats |
| C6 | **Revenue per Passenger Segment** | `Σ(ticket + ancillary) / count(unique pax) by segment` | segment | Where to target offers |
| C7 | **Channel Margin Proxy** | `(Revenue − channel_commission) / Revenue` by channel | channel | Net contribution by channel |

## D. Cross-cutting / strategic

| # | KPI | Formula | Granularity | Why it matters |
|---|---|---|---|---|
| D1 | **Strategic but Underperforming Route** *(ontology rule)* | `route_type IN ('International','Regional') AND ASK_share > 5% AND Margin% < 0` | R | Senior reasoning signal |
| D2 | **High-Value At-Risk Customer** *(ontology rule)* | `B6 = TRUE AND customer_segment IN ('Business','Premium')` | C | Priority retention list |
| D3 | **Upsell-Ready Segment** *(ontology rule)* | `fare_class='Economy' AND lifetime_revenue > p60 AND ancillary_attach < 50%` | C | Priority upsell list |
| D4 | **Competitor Capacity Share** *(when competitor data joined)* | `air_ci_seats / total_seats_on_route` | R, M | Strategic market position |

---

## Joins & key relationships

| From | To | Key | Notes |
|---|---|---|---|
| `bookings` | `flights` | `flight_id` | Each booking → exactly one flight |
| `flights` | `routes` | `route_id` | Each flight → exactly one route |
| `flights` | `aircraft` | `aircraft_type` | Looks up cost per block hour |
| `bookings` | `customers` | `customer_id` | Each booking → exactly one customer |
| `routes` | `airports` (origin) | `origin_airport_code = airport_code` | For geo joins |
| `routes` | `airports` (destination) | `destination_airport_code = airport_code` | For geo joins |
| `reviews` | `bookings` | `booking_id` | One review may exist per flown booking |
| `loyalty_txn` | `customers` | `customer_id` | Many txns per customer |
| `support_tickets` | `customers` | `customer_id` | Many tickets per customer |
| `disruption_log` | `flights` | `flight_id` | One log per disrupted flight |

## Naming conventions

- All KPIs in **snake_case** in SQL: `route_revenue_usd`, `load_factor_pct`.
- All monetary values stored in **USD** with `_usd` suffix.
- All percentages stored as **decimals** (0.0–1.0), formatted to % in BI.
- All date columns end in `_date`; timestamps end in `_at`.
- Boolean flags prefixed with `is_` or suffixed with `_flag`.
- Fact tables prefixed `fct_`, dimensions `dim_`, intermediates `int_`,
  staging `stg_`.

## Quality contracts (dbt tests to implement)

- `not_null` on every primary key column
- `unique` on every primary key
- `accepted_values` on `fare_class`, `fare_family`, `booking_status`,
  `flight_status`, `loyalty_tier`, `customer_segment`, `route_type`
- `relationships` between every FK and its parent table
- `dbt_utils.expression_is_true` for:
  - `pax_flown ≤ seat_capacity` per flight
  - `load_factor_pct BETWEEN 0 AND 1`
  - `ticket_price_usd ≥ 0` and `ancillary_revenue_usd ≥ 0`
