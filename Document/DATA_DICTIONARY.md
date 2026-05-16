# Data Dictionary — Air CI Analytics

Couvre les couches **marts/core** (star schema) et **marts/analytics**
(ontology rules + BI aggregates). La couche staging est un reflet 1:1
des sources avec casts de type — non documentée ici en détail.

---

## Conventions

- `PK` = clé primaire (unique + not null)
- `FK` = clé étrangère
- Types : `string`, `integer`, `double`, `boolean`, `date`
- Monnaie : toujours en **USD** avec suffix `_usd`
- Pourcentages : stockés en **décimal** (0.0–1.0), formatés en % dans le BI
- Booléens : prefixe `is_` ou `has_`

---

## 1. DIMENSIONS

### `dim_route` — Routes servies par Air CI

| Colonne | Type | Description |
|---|---|---|
| `route_id` | string PK | Identifiant unique (R001–R012) |
| `route_label` | string | Label court : "ABJ → CDG" |
| `origin_airport_code` | string | Code IATA origine (ex: ABJ) |
| `origin_city` | string | Ville d'origine (ex: Abidjan) |
| `origin_country` | string | Pays d'origine |
| `destination_airport_code` | string | Code IATA destination |
| `destination_city` | string | Ville de destination |
| `destination_country` | string | Pays de destination |
| `route_type` | string | "Domestic" \| "Regional" \| "International" |
| `distance_km` | integer | Distance en kilomètres |
| `block_time_min` | integer | Durée de vol en minutes (block time) |

---

### `dim_aircraft` — Flotte Air CI

| Colonne | Type | Description |
|---|---|---|
| `aircraft_type` | string PK | Désignation (A319, A320, A320neo, A330-900neo) |
| `manufacturer` | string | Fabricant (Airbus) |
| `seats_total` | integer | Capacité totale (122–242) |
| `seats_business` | integer | Sièges en classe Business |
| `seats_premium_eco` | integer | Sièges en Premium Économique |
| `seats_economy` | integer | Sièges en Économique |
| `fuel_burn_kg_per_hour` | integer | Consommation carburant (kg/h) |
| `cost_per_block_hour_usd` | integer | Coût opérationnel par block hour (USD) |
| `crew_cost_per_hour_usd` | integer | Coût équipage par heure (USD) |
| `introduced_year` | integer | Année d'introduction dans la flotte |
| `fleet_count` | integer | Nombre d'appareils en flotte |
| `aircraft_class` | string | Classe dérivée : "Short-Haul" \| "Medium-Haul" \| "Long-Haul" |

---

### `dim_customer` — Customers Air CI (enrichi)

| Colonne | Type | Description |
|---|---|---|
| `customer_id` | string PK | Identifiant unique (CUST0001–CUST0300) |
| `customer_segment` | string | "Budget" \| "Standard" \| "Business" \| "Premium" |
| `loyalty_tier` | string | "None" \| "Explorer" \| "Silver" \| "Gold" |
| `country` | string | Pays de résidence |
| `signup_date` | date | Date d'inscription |
| `total_bookings` | integer | Nombre total de bookings (Flown + Confirmed) |
| `lifetime_revenue_usd` | double | Revenu cumulé (ticket + ancillary) |
| `lifetime_ticket_revenue_usd` | double | Revenu ticket uniquement |
| `lifetime_ancillary_revenue_usd` | double | Revenu ancillaire uniquement |
| `first_booking_date` | date | Premier booking |
| `last_booking_date` | date | Dernier booking (proxy recency) |
| `bookings_business` | integer | Bookings en Business class |
| `bookings_premium_eco` | integer | Bookings en Premium Éco |
| `bookings_economy` | integer | Bookings en Économique |
| `bookings_with_ancillary` | integer | Bookings avec au moins 1 ancillaire |
| `loyalty_txn_count` | integer | Nombre total de transactions loyalty |
| `earn_event_count` | integer | Nombre d'événements Earn miles |
| `redeem_event_count` | integer | Nombre d'événements Redeem miles |
| `miles_earned` | integer | Miles accumulés |
| `miles_redeemed` | integer | Miles dépensés |
| `last_loyalty_activity_date` | date | Dernière activité loyalty |
| `has_loyalty_activity` | boolean | Au moins 1 transaction loyalty |
| `support_ticket_count` | integer | Nombre de tickets support ouverts |
| `high_severity_tickets` | integer | Tickets de sévérité "High" |
| `earn_events_per_booking` | double | Ratio engagement loyalty : earn/bookings |
| `personal_ancillary_attach_rate` | double | Taux d'attach ancillaire personnel [0,1] |
| `is_premium_loyalty` | boolean | Tier Silver ou Gold |
| `is_high_value_segment` | boolean | Segment Business ou Premium |

---

### `dim_date` — Calendrier

| Colonne | Type | Description |
|---|---|---|
| `date_day` | date PK | Jour calendaire (Nov 2024 → Jan 2025) |
| `year` | integer | Année |
| `month` | integer | Mois (1–12) |
| `day` | integer | Jour du mois |
| `day_of_week` | integer | Jour de la semaine (0=Dimanche) |
| `iso_week` | integer | Semaine ISO |
| `year_month` | string | Format "YYYY-MM" |
| `day_type` | string | "Weekend" \| "Weekday" |
| `month_label` | string | Label lisible : "Nov 2024" |

---

## 2. FAIT — `fct_flights`

**Grain : une ligne par vol opéré.** Unité d'analyse du route P&L
et de la fiabilité opérationnelle.

| Colonne | Type | Description |
|---|---|---|
| `flight_id` | string PK | Identifiant unique du vol |
| `flight_number` | string | Numéro de vol (ex: HF201) |
| `route_id` | string FK→dim_route | Route opérée |
| `aircraft_type` | string FK→dim_aircraft | Type d'appareil |
| `flight_date` | date FK→dim_date | Date du vol |
| `seat_capacity` | integer | Nombre total de sièges |
| `flight_status` | string | "On Time" \| "Delayed" \| "Cancelled" |
| `delay_min` | integer | Retard en minutes (0 si On Time) |
| `is_on_time` | boolean | True si delay ≤ 15 min ET non annulé |
| `is_delayed` | boolean | True si Delayed ET delay > 15 min |
| `is_cancelled` | boolean | True si Cancelled |
| `disruption_root_cause` | string | Cause racine : Weather / Technical / Crew / ATC / Ground_Handling / Other |
| `disruption_sub_cause` | string | Description détaillée de la disruption |
| `pax_count` | integer | Nombre de passagers embarqués |
| `pax_with_ancillary` | integer | Passagers ayant acheté au moins 1 ancillaire |
| `ask` | double | Available Seat Kilometers = seat_capacity × distance_km |
| `rpk` | double | Revenue Passenger Kilometers = pax × distance_km |
| `load_factor` | double | RPK / ASK [0,1] |
| `ticket_revenue_usd` | double | Revenu ticket total du vol |
| `ancillary_revenue_usd` | double | Revenu ancillaire total du vol |
| `total_revenue_usd` | double | Revenu total = ticket + ancillary |
| `fuel_cost_usd` | double | Coût carburant |
| `crew_cost_usd` | double | Coût équipage |
| `airport_fees_usd` | double | Redevances aéroportuaires |
| `nav_fees_usd` | double | Frais de navigation |
| `handling_cost_usd` | double | Frais de handling |
| `total_operating_cost_usd` | double | Somme de tous les coûts |
| `margin_usd` | double | Revenue − Cost |
| `margin_pct` | double | margin_usd / total_revenue_usd [−∞, 1] |
| `rask` | double | Revenue / ASK (USD per seat-km) |
| `cask` | double | Cost / ASK (USD per seat-km) |

---

## 3. FAIT — `fct_bookings`

**Grain : une ligne par booking.** Unité d'analyse du levier upsell
et du revenu par passager.

| Colonne | Type | Description |
|---|---|---|
| `booking_id` | string PK | Identifiant unique |
| `customer_id` | string FK→dim_customer | Customer |
| `flight_id` | string FK→fct_flights | Vol associé |
| `route_id` | string FK→dim_route | Route (dénormalisé pour performance) |
| `booking_date` | date FK→dim_date | Date de réservation |
| `flight_date` | date | Date du vol (dénormalisé) |
| `fare_class` | string | "Economy" \| "Premium Economy" \| "Business" |
| `fare_family` | string | "Basic" \| "Standard" \| "Flex" |
| `booking_channel` | string | "Web" \| "Mobile App" \| "Travel Agency" \| "Corporate Desk" |
| `booking_status` | string | "Flown" \| "Confirmed" \| "Cancelled" \| "No Show" \| "Changed" |
| `ticket_price_usd` | double | Prix du billet |
| `ancillary_revenue_usd` | double | Total ancillaire de ce booking |
| `total_booking_revenue_usd` | double | ticket + ancillary |
| `anc_baggage_usd` | double | Revenu baggage |
| `anc_seat_usd` | double | Revenu sélection de siège |
| `anc_meal_usd` | double | Revenu repas |
| `anc_lounge_usd` | double | Revenu accès lounge |
| `anc_priority_usd` | double | Revenu embarquement prioritaire |
| `anc_upgrade_usd` | double | Revenu upgrade cabine |
| `anc_item_count` | integer | Nombre d'items ancillaires achetés |
| `has_any_ancillary` | boolean | Au moins 1 ancillaire acheté |
| `bought_lounge` | boolean | A acheté l'accès lounge |
| `bought_upgrade` | boolean | A acheté un upgrade cabine |
| `bought_meal` | boolean | A acheté un repas |
| `bought_seat_selection` | boolean | A acheté une sélection de siège |
| `flight_status` | string | Statut du vol (dénormalisé depuis fct_flights) |
| `is_on_time` | boolean | Vol à l'heure |
| `is_delayed` | boolean | Vol retardé |
| `is_cancelled` | boolean | Vol annulé |

---

## 4. FAIT — `fct_reviews_sentiment`

**Grain : une ligne par review client.** La source non-structurée
rendue structurée. Connecte le signal de satisfaction au contexte
opérationnel.

| Colonne | Type | Description |
|---|---|---|
| `review_id` | string PK | Identifiant unique |
| `booking_id` | string FK→fct_bookings | Booking associé |
| `customer_id` | string FK→dim_customer | Customer |
| `flight_id` | string FK→fct_flights | Vol concerné |
| `route_id` | string FK→dim_route | Route |
| `review_date` | date FK→dim_date | Date de publication |
| `rating` | integer | Note 1–5 |
| `review_text` | string | Texte libre de la review |
| `language` | string | Langue (actuellement "en") |
| `topics` | string | Tags semi-colon séparés (ex: "punctuality;staff_service") |
| `sentiment_bucket` | string | "Promoter" (≥4) \| "Passive" (3) \| "Detractor" (≤2) |
| `is_promoter` | boolean | Rating ≥ 4 |
| `is_detractor` | boolean | Rating ≤ 2 |
| `is_passive` | boolean | Rating = 3 |
| `has_punctuality` | boolean | Topic "punctuality" présent |
| `has_cabin_comfort` | boolean | Topic "cabin_comfort" présent |
| `has_food_beverage` | boolean | Topic "food_beverage" présent |
| `has_staff_service` | boolean | Topic "staff_service" présent |
| `has_cleanliness` | boolean | Topic "cleanliness" présent |
| `has_baggage` | boolean | Topic "baggage" présent |
| `has_value_for_money` | boolean | Topic "value_for_money" présent |
| `has_boarding` | boolean | Topic "boarding" présent |
| `has_entertainment` | boolean | Topic "entertainment" présent |
| `has_communication` | boolean | Topic "communication" présent |
| `flight_status` | string | Statut du vol au moment de la review |
| `is_on_time` | boolean | Vol était à l'heure |
| `is_delayed` | boolean | Vol était retardé |
| `is_cancelled` | boolean | Vol était annulé |

---

## 5. ANALYTICS — Ontology rules

### `ontology_strategic_underperforming_route`

Routes qui sont stratégiquement importantes (international/régional avec
part de capacité > 5% du réseau) mais déficitaires.

**Règle** : `route_type IN ('International','Regional')
AND ask_share > 5% AND margin_pct < 0`

| Colonne | Type | Description |
|---|---|---|
| `route_id` | string PK | Route identifiée |
| `route_label` | string | Label court |
| `margin_pct` | double | Marge % (négatif par construction) |
| `ask_share` | double | Part des ASK réseau [0,1] |
| `load_factor` | double | Load factor actuel |
| `cond_strategic_route_type` | boolean | Evidence : type stratégique |
| `cond_meaningful_capacity` | boolean | Evidence : ASK share > 5% |
| `cond_unprofitable` | boolean | Evidence : margin < 0 |
| `is_strategic_underperforming_route` | boolean | Toujours TRUE dans cette vue |

---

### `ontology_highvalue_atrisk_customer`

Customers Business/Premium + Silver/Gold avec engagement loyalty
en dessous de la médiane de leur peer group.

**Règle** : `is_high_value_segment AND is_premium_loyalty
AND earn_events_per_booking < cohort_median
AND lifetime_revenue > cohort_p60`

| Colonne | Type | Description |
|---|---|---|
| `customer_id` | string PK | Customer identifié |
| `lifetime_revenue_usd` | double | LTV total |
| `earn_events_per_booking` | double | Ratio engagement réel |
| `cohort_median_engagement` | double | Seuil : médiane du peer group |
| `cohort_p60_revenue` | double | Seuil : p60 du peer group |
| `cond_high_value_segment` | boolean | Evidence : segment Business/Premium |
| `cond_premium_loyalty` | boolean | Evidence : tier Silver/Gold |
| `cond_below_median_engagement` | boolean | Evidence : sous la médiane |
| `cond_above_p60_revenue` | boolean | Evidence : top 40% LTV |
| `is_highvalue_atrisk_customer` | boolean | Toujours TRUE dans cette vue |

---

### `ontology_upsell_ready_segment`

Customers Economy-dominant, top 40% en LTV, avec attach rate
ancillaire inférieur au p25 de leurs pairs Economy.

**Règle** : `is_economy_dominant AND lifetime_rev > p60
AND ancillary_attach < p25_of_economy_peers`

| Colonne | Type | Description |
|---|---|---|
| `customer_id` | string PK | Customer identifié |
| `personal_ancillary_attach_rate` | double | Taux d'attach personnel |
| `p25_attach_economy` | double | Seuil : p25 du peer group Economy |
| `cond_economy_dominant` | boolean | Evidence : plus de bookings Economy |
| `cond_above_p60_revenue` | boolean | Evidence : LTV dans top 40% |
| `cond_low_attach_vs_peers` | boolean | Evidence : attach < p25 pairs |
| `is_upsell_ready_segment` | boolean | Toujours TRUE dans cette vue |

---

### `route_pnl_monthly`

Agrégat BI-ready : route × mois avec tous les KPIs headline.
Alimente directement la page Network & Profitability du dashboard
et l'outil `query_route_metrics` du MCP.

| Colonne | Type | Description |
|---|---|---|
| `route_id` | string FK→dim_route | Route |
| `year_month` | string | Période (ex: "2025-01") |
| `flights_count` | integer | Vols opérés |
| `pax_count` | integer | Passagers transportés |
| `on_time_performance` | double | OTP [0,1] (seuil 15 min) |
| `cancellation_rate` | double | Taux d'annulation [0,1] |
| `load_factor` | double | RPK / ASK [0,1] |
| `total_revenue_usd` | double | Revenu total |
| `total_operating_cost_usd` | double | Coût total |
| `margin_usd` | double | Marge absolue |
| `margin_pct` | double | Marge % |
| `yield_usd_per_rpk` | double | Yield : revenue / RPK |
| `rask` | double | Revenue / ASK |
| `cask` | double | Cost / ASK |

---

## 6. KPI Glossaire

| KPI | Formule | Unité | Interprétation |
|---|---|---|---|
| **Load Factor** | RPK / ASK | % | % de sièges vendus. Standard industrie. Break-even Air CI ~65%. |
| **RASK** | Revenue / ASK | USD/seat-km | Revenu par unité de capacité offerte. Compare des routes de tailles différentes. |
| **CASK** | Cost / ASK | USD/seat-km | Coût par unité de capacité. RASK−CASK = spread de rentabilité unitaire. |
| **Yield** | Revenue / RPK | USD/pax-km | Revenu par km effectivement vendu. |
| **OTP** | On-time flights / total | % | Seuil 15 min standard IATA. |
| **NPS Proxy** | % Promoters − % Detractors | points | Approximation du Net Promoter Score depuis les ratings reviews. |
| **Ancillary Attach Rate** | Bookings avec ancillaire / total | % | 83% dans la donnée actuelle → levier = mix shift, pas volume. |
| **ARPU Ancillaire** | Σ ancillary / bookings | USD | Revenu ancillaire moyen par passager. |
| **Earn/Booking Ratio** | Earn events / total bookings | ratio | Signal d'engagement loyalty. Sous la médiane peer group → at-risk flag. |
