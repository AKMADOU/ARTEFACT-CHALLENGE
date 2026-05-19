# Dashboard Air Côte d'Ivoire — Guide Utilisateur

> **Executive Growth Allocation Dashboard**
> Outil d'aide à la décision pour l'allocation budgétaire d'Air CI

---

## Lancement

```bash
# Depuis la racine du projet
streamlit run dashboard/app.py

# Avec un chemin DuckDB custom
DBT_DUCKDB_PATH=/chemin/vers/airci.duckdb streamlit run dashboard/app.py
```

Ouvre automatiquement **http://localhost:8501**

---

## Vue d'ensemble

Le dashboard répond à une seule question :

> *Où Air Côte d'Ivoire doit-elle investir son budget sur 12 mois pour maximiser la croissance rentable ?*

Il est structuré en **4 pages**, chacune couvrant un angle d'analyse différent, et converge vers une recommandation executive sur la page finale.

```
Réseau & Rentabilité  →  comprendre le P&L par route
       ↓
Clients & Rétention   →  identifier les clients à risque
       ↓
Upsell & Ancillaire   →  trouver les opportunités de revenus immédiates
       ↓
Décision & Allocation →  répondre à la question centrale
```

---

## Page 1 — 🗺️ Réseau & Rentabilité

### Objectif
Donner une vue complète de la santé financière et opérationnelle du réseau Air CI.

### KPIs en haut de page

| KPI | Définition | Pourquoi c'est important |
|---|---|---|
| **Revenu réseau** | Σ(ticket + ancillaire) sur tous les vols Flown/Confirmed | Top-line total du réseau |
| **Marge nette** | Revenu − coûts opérationnels (fuel + crew + aéroport + nav + handling) | Rentabilité réelle du réseau |
| **Load Factor moy.** | RPK / ASK = pax transportés × distance / sièges offerts × distance | % de sièges vendus — le KPI le plus suivi dans l'aérien |
| **OTP moyen** | Vols avec retard ≤ 15 min / total vols | Fiabilité opérationnelle (seuil IATA standard) |
| **Vols opérés** | Nombre total de vols sur la période | Volume de l'opération |

### Graphiques

#### Marge % par route (bar chart horizontal)
- Chaque barre représente une route
- **Vert** = route rentable, **Rouge** = route déficitaire
- Les valeurs sont affichées à l'extrémité de chaque barre
- **Lecture** : Accra (ABJ→ACC) est la meilleure route à +33%, Paris (ABJ→CDG) la pire à −87%

#### Mix statuts de vols (donut)
- Répartition On Time / Delayed / Cancelled sur tout le réseau
- **Lecture** : 70% OTP signifie que 30% des vols ont eu un problème → impact direct sur la satisfaction

#### Causes de disruption (bar horizontal)
- Cause racine de chaque retard/annulation (Weather, Technical, Crew, ATC, Ground Handling)
- **Lecture** : Technical (30%) est la principale cause adressable → levier maintenance

#### Route Opportunity Matrix (scatter plot)
Chaque bulle = une route. Axes :
- **X** : Load Factor (% de remplissage)
- **Y** : Marge %
- **Taille** : Revenu total de la route

| Quadrant | Signification | Action |
|---|---|---|
| Haut-droite (LF > 15%, Marge > 0) | Routes saines | Augmenter la fréquence |
| Haut-gauche (LF faible, Marge > 0) | Rentables mais sous-remplies | Yield management |
| Bas-droite | Non représenté avec cette data | — |
| **Bas-gauche (Paris)** | **Sous-remplie ET déficitaire** | **Demand generation** |

> ⚠️ **Note sur les données** : le starter couvre uniquement Janvier 2025 avec ~22 pax/vol
> en moyenne. Les Load Factors observés (9-17%) sont inférieurs à la réalité commerciale.
> La marge % reste un indicateur fiable car elle compare routes entre elles.
> Le break-even réel de Paris (A330neo) se situe autour de 65% LF.

---

## Page 2 — 👥 Clients & Rétention

### Objectif
Identifier les segments clients à forte valeur, mesurer leur satisfaction, et repérer ceux qui risquent de partir.

### KPIs en haut de page

| KPI | Définition |
|---|---|
| **Clients total** | Nombre de customers dans la base |
| **Loyalty actif** | Customers avec au moins 1 transaction loyalty (Earn/Redeem) sur la période |
| **LTV moyen** | Lifetime Value moyenne = Σ(ticket + ancillaire) par customer |
| **High-Value At-Risk** | Customers Silver/Gold dont l'engagement loyalty est sous la médiane de leurs pairs |

### Graphiques

#### LTV moyen par segment
- Revenu moyen par customer selon son segment (Budget / Standard / Business / Premium)
- **Lecture** : montre si la segmentation du starter est financièrement différenciée.
  Si les LTV sont proches entre segments, c'est une limitation des données (tickets peu différenciés)

#### NPS Proxy par route
- NPS Proxy = % Promoteurs (rating ≥ 4) − % Détracteurs (rating ≤ 2)
- Score positif = plus de clients satisfaits que mécontents
- **Lecture** : Paris a un NPS très bas → lié aux retards (corrélation rating × flight_status confirmée)

#### Plaintes les plus fréquentes (reviews négatives)
- Compte des topics mentionnés dans les reviews de rating ≤ 2
- Topics contrôlés : Ponctualité, Confort cabine, Restauration, Personnel, Bagages, Communication, etc.
- **Lecture** : La ponctualité est le 1er sujet de mécontentement → action directe sur l'OTP

#### Table Customers High-Value At-Risk
Liste des customers à cibler en priorité pour une campagne de rétention.

| Colonne | Signification |
|---|---|
| Client | Identifiant customer |
| Segment | Budget / Standard / Business / Premium |
| Tier | Niveau loyalty : Explorer / Silver / Gold |
| LTV ($) | Revenu cumulé de ce customer |
| Engagement | Ratio earn_events / total_bookings (signal d'activité loyalty) |
| Médiane peers | Seuil de la cohorte — en dessous = signal at-risk |

**Définition de l'ontology rule "at-risk" :**
```
Segment Business ou Premium
ET Tier Silver ou Gold
ET Engagement < médiane du peer group
ET LTV > p60 du peer group
```

> Pourquoi des seuils quantiles (médiane, p60) plutôt qu'absolus ?
> Le starter sur-échantillonne les customers actifs (tous bookent 21-58× en 3 mois).
> Un seuil absolu comme "engagement < 0.5" ne matcherait personne.
> Les quantiles identifient les outliers *relatifs* au sein de la cohorte.

---

## Page 3 — 💰 Upsell & Ancillaire

### Objectif
Analyser la performance des produits ancillaires et identifier les opportunités de mix shift (vendre des produits à plus forte valeur, pas juste vendre plus).

### KPIs en haut de page

| KPI | Définition |
|---|---|
| **Attach Rate global** | % de bookings avec au moins 1 ancillaire acheté |
| **ARPU Ancillaire** | Average Revenue Per User ancillaire = Σ ancillaire / nb bookings |
| **Revenu ancillaire total** | Revenu total généré par les produits au-delà du billet |
| **Clients Upsell-Ready** | Customers Economy sous-attachés vs leurs pairs |

> **Insight clé** : l'Attach Rate est déjà à ~83%.
> Le levier n'est pas "vendre plus d'ancillaires" mais "vendre des ancillaires plus chers".
> Lounge (2.1% attach) et Upgrade sont très sous-utilisés malgré une forte valeur unitaire ($45–80).

### Graphiques

#### Attach rate par produit et famille tarifaire
- Compare l'adoption de chaque produit (Lounge, Upgrade, Repas, Siège) selon la famille tarifaire (Basic / Standard / Flex)
- **Lecture** : Flex devrait acheter plus de Lounge et Upgrade — cible prioritaire pour les offres premium

#### Mix revenu ancillaire (donut)
- Répartition du revenu ancillaire entre Bagage, Siège, Repas, Lounge, Upgrade
- **Lecture** : Bagage domine (~68%) alors que c'est le produit le moins cher. Lounge et Upgrade = petits % mais marge unitaire élevée

#### ARPU par segment client
- Revenue ancillaire moyen selon le segment
- **Lecture** : si Business n'achète pas plus d'ancillaires que Budget, la proposition de valeur Premium n'est pas correctement packagée

#### Mix channels (revenus)
- Revenu total par canal de distribution (Web, Mobile App, Travel Agency, Corporate Desk)
- **Lecture** : Corporate Desk génère des tickets élevés mais est coûteux en commission → arbitrage à analyser

#### Table Clients Upsell-Ready
Clients Economy ciblés pour une campagne d'upgrade/ancillaire.

**Définition de l'ontology rule "upsell-ready" :**
```
Economy-dominant (plus de bookings Economy que Business+PremiumEco)
ET LTV > p60 du réseau
ET Attach Rate personnel < p25 des peers Economy
```

---

## Page 4 — 🎯 Décision & Allocation

### Objectif
C'est la page la plus importante. Elle synthétise les analyses des 3 pages précédentes pour répondre directement à la question de décision.

### Structure de la page

#### Recommandation headline (bandeau vert)
La réponse à la question centrale, visible immédiatement :
> Prioriser Upsell/cross-sell → Rétention → Demand gen Paris → Hold réseau

#### Allocation budget suggérée (donut)

| Levier | % budget | Justification |
|---|---|---|
| **Upsell / Cross-sell** | 40% | Payback 0–3 mois · Lounge attach 2.1% → potentiel +$45/booking |
| **Rétention client** | 30% | Payback 3–6 mois · 6 customers Silver/Gold à LTV $98K |
| **Demand gen Paris** | 20% | Payback 6–12 mois · Paris −87% marge, LF 9.3% |
| **Réserve opérationnelle** | 10% | Buffer disruptions · Hold nouvelles routes |

#### Signaux qui justifient ce ranking (6 métriques)
- Attach rate lounge actuel → signal upsell
- Nb clients at-risk + LTV concentrée → signal rétention
- Load Factor Paris → signal demand gen
- Marge réseau globale → contexte financier

#### 3 colonnes opérationnelles

**Routes**
- ✅ **À développer** : routes rentables avec capacité disponible (LF < 70%)
- 🔴 **À défendre** : routes stratégiques déficitaires (ontology rule Strategic Underperforming Route)

**Rétention**
- Liste des clients at-risk avec LTV, engagement, et ROI estimé de la campagne
- NPS proxy des 3 routes les plus insatisfaisantes

**Upsell**
- Liste des clients upsell-ready
- Comparaison attach rate Lounge/Upgrade/Repas par famille tarifaire

#### Synthèse executive (table finale)

| Colonne | Contenu |
|---|---|
| Priorité | Horizon temporel (court/moyen/long terme) |
| Levier | Le levier business concerné |
| Action | Ce qu'il faut concrètement faire |
| KPI succès | Comment mesurer si ça marche |
| ROI | Estimation du retour basée sur les données |

---

## Architecture technique

```
app.py        → Interface Streamlit (4 pages, charts Plotly)
db.py         → Connexion DuckDB + toutes les requêtes SQL cachées
config.py     → Palette de couleurs, constantes, labels
```

```
app.py  →  db.py  →  airci.duckdb  (généré par dbt)
               ↑
        auto-détection des schémas dbt
        (fonctionne sur toutes les machines)
```

### Tables DuckDB utilisées

| Table | Couche dbt | Usage dans le dashboard |
|---|---|---|
| `route_pnl_monthly` | analytics | P&L par route × mois (Page 1) |
| `fct_flights` | marts/core | Stats vols, disruptions (Page 1) |
| `fct_bookings` | marts/core | Attach rates, ARPU (Page 3) |
| `fct_reviews_sentiment` | marts/core | NPS, topics négatifs (Page 2) |
| `dim_customer` | marts/core | Segmentation, LTV (Page 2) |
| `dim_route` | marts/core | Labels routes (toutes pages) |
| `ontology_strategic_underperforming_route` | analytics | Routes à défendre (Page 4) |
| `ontology_highvalue_atrisk_customer` | analytics | Clients at-risk (Pages 2 & 4) |
| `ontology_upsell_ready_segment` | analytics | Clients upsell-ready (Pages 3 & 4) |

### Cache Streamlit
Toutes les requêtes DuckDB sont cachées avec `@st.cache_data(ttl=300)`.
Le cache expire toutes les 5 minutes pour rester frais sans surcharger la base.

---

## Dépendances

```bash
pip install streamlit plotly pandas duckdb
```

---

## Limitations connues

| Limitation | Impact | Ce qu'on fait |
|---|---|---|
| Données sur 30 jours (Janvier 2025) | Pas de saisonnalité | On traite comme un snapshot état actuel |
| ~22 pax/vol en moyenne | Load factors 9-17% (sous-estimés) | On utilise marge % plutôt que $ absolus |
| Coûts synthétiques | Valeurs absolues approximatives | Les rankings entre routes restent fiables |
| 300 customers très actifs | Cohorte at-risk petite (6 clients) | Seuils adaptatifs (quantiles peer group) |

---

*Dashboard construit dans le cadre du challenge Analytics Engineer — Artefact*
*Candidat : ADOU Kouamé Mathurin*
