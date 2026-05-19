# Air Côte d'Ivoire — Business Framing

## 1. Strategic context

Air Côte d'Ivoire (Air CI) is the flag carrier of Côte d'Ivoire, headquartered at
Abidjan Félix-Houphouët-Boigny International Airport (ABJ). The airline operates
in three concentric markets:

1. **Domestic** — connecting Abidjan to Bouaké, Man, and Korhogo. Low fares,
   high frequency expectations, sensitive to ground alternatives (road, rail).
2. **Regional (West Africa)** — Accra, Lagos, Dakar, Cotonou, Ouagadougou.
   Competition from ASKY, Air Sénégal, ECair, Brussels Airlines connections.
3. **International long-haul** — Paris (CDG) launched as the first long-haul
   route, operated with the newly delivered **A330-900neo**. Strategic ambition
   to extend to North Africa, the Middle East, and eventually North America.

The fleet renewal (A320neo and A330-900neo) signals a structural shift: Air CI
is moving from a regional feeder profile toward a hub carrier strategy with
Abidjan as a connecting point for West African passengers heading to Europe.

## 2. The decision question

> Where should Air CI invest a constrained **12-month budget** to maximize
> *profitable* growth: route expansion, customer retention, or upsell /
> cross-sell?

These three levers compete for the same capital but behave very differently:

| Lever | Capital intensity | Time to revenue | Risk profile | Upside |
|---|---|---|---|---|
| **Network expansion** | High (slots, fuel, fleet) | 6–18 months | Demand risk, regulatory | Step-change revenue |
| **Customer retention** | Low (CRM, loyalty, NPS) | 3–6 months | Limited downside | Compounding LTV |
| **Upsell / cross-sell** | Very low (config, pricing) | 0–3 months | Cannibalization | Margin lift on existing pax |

The right answer is almost certainly **a mix**, but the analytics product must
make the *trade-off* visible and defendable, not just list opportunities.

## 3. Decision makers and what they need

| Stakeholder | Primary decision | Needs from the product |
|---|---|---|
| **CEO** | Capital allocation across the 3 levers | Portfolio view, P&L per lever, sensitivity |
| **Chief Commercial Officer** | Fare strategy, channel mix | Revenue decomposition, channel margin |
| **Chief Network Officer** | Route opening / dropping / frequency | Route P&L, opportunity matrix, competitor share |
| **VP Loyalty & CRM** | Tier strategy, retention campaigns | At-risk customers, tier migration, churn proxy |
| **VP Customer Experience** | Service investments | NPS proxy, complaint themes by route |
| **VP Revenue Management** | Ancillary pricing, upgrade rules | Attach rate, upsell propensity, willingness to pay |

## 4. Business domains in scope

| Domain | Core entities | Why it matters here |
|---|---|---|
| **Network** | Routes, frequency, schedule | Drives capacity and reach |
| **Operations** | Flights, aircraft, disruptions | Drives cost and reliability |
| **Commercial** | Bookings, fares, channels | Drives revenue mix |
| **Customer** | Profiles, loyalty, segments | Drives retention and LTV |
| **Ancillary** | Bags, seats, meals, upgrades | Drives margin per passenger |

## 5. KPI tree (top-down)

```
                     PROFITABLE GROWTH (Net margin USD)
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
     REVENUE                      COST                     RISK / RETENTION
        │                          │                          │
   ┌────┴────┐               ┌────┴────┐               ┌────┴────┐
   │         │               │         │               │         │
 Route    Ancillary       Fuel     Crew /          Disruption  Churn
 Revenue  Revenue         (var)    Lease (fixed)   Rate        Proxy
   │         │               │                          │         │
   ▼         ▼               ▼                          ▼         ▼
 Yield    Attach rate    Fuel $/kg                  OTP %     Repeat
 RASK     ARPU ancil.   x burn x BH                            booking %
 Load     Upgrade conv.                                        At-risk
 factor                                                        customers
```

This tree is what the **Decision Layer** of the dashboard should mirror.

## 6. Working hypotheses

Before looking at data, we hold these hypotheses to test:

- **H1 — Route mix is imbalanced.** Paris (R009) and Lagos (R006) likely
  generate disproportionate revenue. Domestic routes likely lose money on a
  fully-allocated basis but are politically/strategically protected.
- **H2 — Operational reliability is uneven.** Delays and cancellations cluster
  on specific routes/aircraft combos, dragging satisfaction and creating
  hidden cost.
- **H3 — Loyalty is under-monetized.** A meaningful share of customers have
  `loyalty_tier = None` despite repeat bookings → untapped retention lever.
- **H4 — Ancillary attach is generic.** Attach rate is high (~83%) but ARPU
  is flat (~$20) → we're selling bags, not value (seat, lounge, upgrade).
- **H5 — Channel matters.** Corporate Desk and Travel Agency likely skew
  toward Business class but cost more in commission. Mobile App likely the
  cheapest acquisition channel.

We will validate or reject each in the dashboard and the recommendations.

## 7. Out of scope (and why)

- **Aircraft maintenance scheduling** — operationally critical but doesn't
  drive the 12-month allocation decision.
- **Crew rostering** — same logic.
- **Cargo P&L** — important business but separate decision.
- **Currency hedging** — finance scope, not analytics-engineer scope.

These can be mentioned as "adjacent" but not modeled in depth.
