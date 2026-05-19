# ✈️ Air Côte d'Ivoire — Growth Allocation Analytics

> **Artefact Analytics Engineer Challenge — Soumission complète**

---

## Question de décision

> *Où Air Côte d'Ivoire doit-elle allouer son budget contraint des 12 prochains mois pour maximiser la croissance rentable : expansion réseau, rétention client, ou upsell / cross-sell ?*

**Réponse (ancrée dans la donnée) :**

| Priorité | Levier | Payback | Signal data |
|---|---|---|---|
| 🥇 1 | Upsell / Cross-sell | 0–3 mois | Attach lounge 2.1% · ARPU $20 → potentiel $45+ |
| 🥈 2 | Rétention client | 3–6 mois | 6 customers Silver/Gold désengagés · $98K LTV |
| 🥉 3 | Demand gen Paris | 6–12 mois | Load Factor 9.3% · L'A330neo est en place |
| ✋ Hold | Network expansion | Pas maintenant | Paris sous break-even · risque élevé |

---

## Stack technique

```
Python 3.10+ · dbt-core 1.11 · dbt-duckdb 1.10 · DuckDB
Streamlit · Plotly · FastMCP 1.27 · Claude Desktop
```

---

## Installation

```bash
git clone <repo_url>
cd airci_challenge

pip install dbt-core dbt-duckdb duckdb pandas openpyxl \
            streamlit plotly "mcp[cli]"
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  PHASE 1 — Business understanding + données                      │
│  Starter Excel (5 feuilles) + 9 datasets synthétiques            │
│  └── scripts/generate_synthetic_data.py  (SEED=42)              │
└───────────────────────────┬──────────────────────────────────────┘
                            │ 14 CSV seeds
┌───────────────────────────▼──────────────────────────────────────┐
│  PHASE 2 — Pipeline dbt + DuckDB                                 │
│  stg (14) → int (4) → marts/core (7) → marts/analytics (4)      │
│  30 modèles · 73 tests · Semantic Layer MetricFlow               │
└────────────────┬─────────────────────────┬───────────────────────┘
                 │ airci.duckdb            │ airci.duckdb
  ┌──────────────▼────────────┐ ┌──────────▼─────────────────────┐
  │  PHASE 3 — Streamlit      │ │  PHASE 4 — MCP Server          │
  │  Dashboard 4 pages        │ │  5 outils · Claude Desktop     │
  └───────────────────────────┘ └────────────────────────────────┘
```

---

## Phases

---

### Phase 1 — Business Understanding & Data Generation

#### Lancer la génération

```bash
# Générer les 9 datasets synthétiques
python scripts/generate_synthetic_data.py \
  --starter air_cote_divoire_starter_dataset.xlsx \
  --out-dir data/synthetic/
```

#### Ce que ça produit

| Dataset | Lignes | Rôle |
|---|---:|---|
| `aircraft_fleet.csv` | 4 | Coût par block hour — indispensable pour le P&L |
| `fuel_prices_monthly.csv` | 3 | Prix carburant Nov 2024–Jan 2025 |
| `ancillary_catalog.csv` | 14 | Référentiel produits ancillaires |
| `route_operating_costs.csv` | 480 | Décomposition coût par vol |
| `ancillary_purchases.csv` | 11 731 | Ancillaire décomposé par item |
| `loyalty_transactions.csv` | 3 953 | Activité loyalty (signal engagement) |
| `disruption_log.csv` | 145 | Cause racine des disruptions |
| `support_tickets.csv` | 35 | Interactions service client |
| **`customer_reviews.csv`** ⭐ | **3 073** | **Source non-structurée — texte + topics** |

#### Données starter (5 feuilles Excel)

| Feuille | Lignes | Description |
|---|---:|---|
| Airports | 10 | Aéroports (ABJ, CDG, ACC, LOS…) |
| Routes | 12 | Définitions routes R001–R012 |
| Customers | 300 | Profils clients avec segment + tier loyalty |
| Flights | 480 | Vols opérés — Janvier 2025 |
| Bookings | 11 475 | Réservations Nov 2024–Jan 2025 |

#### Validation des données synthétiques

```
✅ Ancillary reconciliation : Σ purchases = Σ bookings.ancillary_revenue ($236 616, 0 d'écart)
✅ Rating × flight_status   : On-Time 3.85★ vs Delayed 2.53★ (signal réaliste)
✅ Disruption mix           : Weather 25%, Technical 30%, Crew 15% (réaliste Afrique de l'Ouest)
✅ Reproductibilité         : SEED=42 → output identique à chaque exécution
```

#### KPIs définis (30+)

Groupés en 4 familles : Network/Profitability · Customer/Retention · Upsell/Cross-sell · Cross-cutting (ontology rules).

Voir [`docs/02_kpi_dictionary.md`](docs/02_kpi_dictionary.md) pour les formules complètes.

---

### Phase 2 — Pipeline dbt + DuckDB

#### Préparer les seeds puis lancer le pipeline

```bash
# 1. Copier les CSVs dans seeds/ (starter + synthétiques)
python scripts/setup_seeds.py \
  --starter air_cote_divoire_starter_dataset.xlsx \
  --synthetic data/synthetic/ \
  --seeds dbt_project/seeds/

# 2. Lancer le pipeline complet
cd dbt_project
export DBT_PROFILES_DIR=.

dbt seed    # Charge les 14 CSV dans DuckDB
dbt run     # Construit les 30 modèles
dbt test    # Exécute les 73 tests de qualité
```

#### Résultats attendus

```
dbt seed  →  PASS=14   WARN=0  ERROR=0  (~3s)
dbt run   →  PASS=30   WARN=0  ERROR=0  (~2s)
dbt test  →  PASS=73   WARN=0  ERROR=0  (~2s)
```

#### Commandes utiles

```bash
# Lancer uniquement une couche
dbt run --select stg_*                 # staging
dbt run --select marts.core            # dims + facts
dbt run --select marts.analytics       # ontology + BI

# Lancer un modèle + ses dépendances
dbt run --select +fct_flights+

# Voir le SQL compilé sans l'exécuter
dbt compile --select route_pnl_monthly
cat target/compiled/airci/models/marts/analytics/route_pnl_monthly.sql

# Générer la documentation interactive
dbt docs generate && dbt docs serve --port 8080
```

#### Architecture des modèles

```
seeds/           → 14 CSV (sources)
  │
  ▼
staging/         → 14 vues  (casts + renames, 1:1 avec les sources)
  │
  ▼
intermediate/    → 4 vues   (joins + logique métier)
  │
  ▼
marts/core/      → 7 tables (star schema publié)
  │               ├── dim_route, dim_aircraft, dim_customer, dim_date
  │               ├── fct_flights     (grain : 1 vol)
  │               ├── fct_bookings    (grain : 1 booking)
  │               └── fct_reviews_sentiment  (grain : 1 review)
  │
  ▼
marts/analytics/ → 4 tables (BI + ontology)
                  ├── route_pnl_monthly
                  ├── ontology_strategic_underperforming_route
                  ├── ontology_highvalue_atrisk_customer
                  └── ontology_upsell_ready_segment
```

#### Semantic Layer (MetricFlow)

Défini dans `models/_semantic.yml` — 27 métriques :

```
15 simple metrics  (total_revenue_usd, ask, rpk, bookings_count…)
11 ratio  metrics  (load_factor, route_margin_pct, rask, cask, otp, attach_rate…)
 1 derived metric  (nps_proxy = promoter_share − detractor_share)
```

#### Ontology rules — les 3 classifications métier

```sql
-- 1. Route stratégique mais déficitaire
route_type IN ('International','Regional')
AND ask_share > 5%      -- part de capacité significative
AND margin_pct < 0      -- non rentable
-- Résultat : 2 routes (Paris −87%, Dakar −14%)

-- 2. Customer high-value à risque de churn
is_high_value_segment   -- Business ou Premium
AND is_premium_loyalty  -- Silver ou Gold
AND earn_events_per_booking < cohort_median  -- sous-engagé vs peers
AND lifetime_revenue > cohort_p60
-- Résultat : 6 customers, $98K LTV

-- 3. Segment upsell-ready
is_economy_dominant
AND lifetime_revenue > p60 réseau
AND ancillary_attach_rate < p25 peers Economy
-- Résultat : 30 customers, $524K LTV
```

> **Choix de seuils adaptatifs (quantiles) :** le starter sur-échantillonne
> les customers actifs (tous bookent 21-58× en 3 mois). Des seuils absolus
> (ex: attach < 50%) ne matcheraient personne. Les quantiles de la cohorte
> peer group sont plus robustes et plus défendables.

#### Portabilité Trino

Le SQL est ANSI-standard. Points de divergence commentés inline :

| DuckDB | Trino équivalent |
|---|---|
| `x::type` | `CAST(x AS type)` |
| `generate_series(…)` | `sequence(…)` |
| `quantile_cont(x, 0.5)` | `approx_percentile(x, 0.5)` |
| `strftime(d, '%Y-%m')` | `date_format(d, '%Y-%m')` |

---

### Phase 3 — Dashboard Streamlit

#### Lancer le dashboard

```bash
# Depuis la racine du projet
streamlit run dashboard/app.py

# Avec un DuckDB custom (ex: prod)
DBT_DUCKDB_PATH=/path/to/airci.duckdb streamlit run dashboard/app.py
```

Ouvre **http://localhost:8501**

#### 4 pages

| Page | Contenu |
|---|---|
| 🗺️ **Network & Profitability** | Route P&L · Load factor · OTP · Cancellation rate · Route opportunity matrix |
| 👥 **Customer & Retention** | NPS proxy · Thèmes négatifs reviews · Cohorte at-risk |
| 💰 **Upsell & Cross-sell** | Attach rates par item · ARPU par segment · Upsell-ready customers |
| 🎯 **Decision Layer** | Réponse à la question centrale · Budget allocation · Evidence trail |

#### Dépendances

```bash
pip install streamlit plotly pandas duckdb
```

---

### Phase 4 — MCP Server (Agentic AI)

#### Tester sans Claude Desktop

```bash
cd mcp_server
python demo.py
```

Répond à 8 questions business avec les vraies données DuckDB.

#### 5 outils exposés

| Outil | Description |
|---|---|
| `query_route_metrics` | P&L + Load Factor + OTP par route, filtrable |
| `get_at_risk_customers` | Liste Silver/Gold à faible engagement loyalty |
| `search_reviews_by_route` | Recherche reviews par route + topic + sentiment + texte libre |
| `recommend_budget_allocation` | Recommandation budget 12 mois avec ROI estimé |
| `explain_route_pnl` | Rapport narratif complet d'une route (P&L + ops + NPS + diagnostic) |

#### Connecter à Claude Desktop

**1. Trouver le chemin Python**

```bash
which python
# ex: /Applications/anaconda3/bin/python
```

**2. Modifier la config Claude Desktop**

```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Ajouter `mcpServers` (garder les préférences existantes) :

```json
{
  "preferences": { ... },
  "mcpServers": {
    "airci-analytics": {
      "command": "/Applications/anaconda3/bin/python",
      "args": [
        "/chemin/absolu/vers/mcp_server/server.py"
      ],
      "env": {
        "DBT_DUCKDB_PATH": "/chemin/absolu/vers/dbt_project/airci.duckdb"
      }
    }
  }
}
```

**3. Redémarrer Claude Desktop**

```bash
pkill -f "Claude" ; sleep 2 ; open -a Claude
```

**4. Vérifier la connexion**

```bash
cat ~/Library/Logs/Claude/mcp-server-airci-analytics.log
# Doit contenir : "Server started and connected successfully"
```

Le marteau 🔨 apparaît dans la barre de saisie de Claude Desktop.

#### Questions de démo à poser à Claude

```
1. Quelles routes d'Air CI méritent plus de budget au prochain trimestre ?
   Justifie avec les données.

2. Explique pourquoi la route Paris (R009) est déficitaire et que faire.

3. Quels customers high-value sont à risque de churn ?
   Quel est le revenue que l'on risque de perdre ?

4. Que disent les clients mécontents sur la route Dakar ?
   Cite des reviews réels.

5. Compare les routes Accra (R004) et Dakar (R005) sur les dimensions
   financières ET satisfaction client.

6. Donne la recommandation d'allocation budgétaire pour les 12 prochains
   mois avec les données qui la justifient.
```

#### Dépendances

```bash
pip install "mcp[cli]" duckdb pandas
```

---

### Phase 5 — Livrables

| Fichier | Description |
|---|---|
| `deliverables/README.md` | Ce fichier |
| `deliverables/DATA_DICTIONARY.md` | Dictionnaire complet de toutes les tables et colonnes |
| `deliverables/WRITE_UP.md` | Hypothèses, choix d'architecture, limitations, next steps |
| `deliverables/VIDEO_SCRIPTS.md` | Scripts des deux vidéos de démo |
| `airci_presentation.pptx` | Présentation 21 slides (toutes les phases) |

---

## Structure complète du projet

```
airci_challenge/
│
├── README.md                          ← ce fichier
├── air_cote_divoire_starter_dataset.xlsx
│
├── scripts/
│   ├── generate_synthetic_data.py     ← Phase 1 : génération SEED=42
│   └── setup_seeds.py                 ← copie les CSVs dans seeds/
│
├── data/
│   └── synthetic/                     ← 9 CSVs + enriched_dataset.xlsx
│
├── docs/                              ← documentation Phase 1
│   ├── 01_business_framing.md
│   ├── 02_kpi_dictionary.md
│   ├── 03_data_enrichment_plan.md
│   ├── 04_assumptions.md
│   └── 05_phase1_preview_insights.md
│
├── dbt_project/                       ← Phase 2
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/                         ← 14 CSV (starter + synthétiques)
│   ├── models/
│   │   ├── staging/                   ← 14 vues stg_*
│   │   ├── intermediate/              ← 4 vues int_*
│   │   ├── marts/
│   │   │   ├── core/                  ← 4 dims + 3 facts
│   │   │   └── analytics/             ← 3 ontology + route_pnl_monthly
│   │   ├── _semantic.yml              ← MetricFlow : 27 métriques
│   │   └── _time_spine.yml
│   └── airci.duckdb                   ← généré par dbt seed && dbt run
│
├── dashboard/                         ← Phase 3
│   ├── app.py                         ← Streamlit 4 pages
│   ├── db.py                          ← connexion DuckDB + queries
│   ├── config.py                      ← palette, labels
│   └── requirements.txt
│
├── mcp_server/                        ← Phase 4
│   ├── server.py                      ← 5 outils FastMCP (autonome)
│   ├── demo.py                        ← test sans Claude Desktop
│   └── README.md                      ← guide connexion Claude Desktop
│
└── deliverables/                      ← Phase 5
    ├── README.md
    ├── DATA_DICTIONARY.md
    ├── WRITE_UP.md
    ├── VIDEO_SCRIPTS.md
    └── airci_presentation.pptx
```

---

## Résultats headline

| Métrique | Valeur |
|---|---|
| Revenue réseau (Jan 2025) | $4.1M |
| Marge réseau | −$992K (−24.2%) |
| Meilleure route | ABJ→ACC (Accra) +33.2% |
| Pire route | ABJ→CDG (Paris) −86.9% |
| Load Factor Paris | 9.3% (break-even ~65%) |
| OTP réseau | 70.3% |
| Customers at-risk identifiés | 6 (LTV $98 728) |
| Customers upsell-ready | 30 (LTV $524 302) |
| Reviews générées | 3 073 |
| Modèles dbt | 30 (PASS=30) |
| Tests qualité | 73 (PASS=73) |

---

## Choix techniques justifiés

### Pourquoi DuckDB + dbt ?

DuckDB est zéro-infrastructure (un fichier `.duckdb`), ce qui permet un
pipeline reproductible en 3 commandes sans serveur ni cloud. dbt apporte
la couche de transformation versionnée, testée, et documentée. Le SQL
est écrit en style ANSI compatible Trino pour la portabilité en production.

### Pourquoi 3 fact tables séparées ?

`fct_flights` (grain : vol), `fct_bookings` (grain : booking),
`fct_reviews_sentiment` (grain : review) ont des grains distincts.
Les combiner créerait des fan traps et du count inflation.
Référence : Kimball *Data Warehouse Toolkit* §15.

### Pourquoi des seuils quantiles dans les ontology rules ?

Le starter sur-échantillonne les customers actifs (tous bookent 21-58× en
3 mois, attach rate uniforme à ~83%). Des seuils absolus matcheraient tout
le monde ou personne. Les quantiles de la cohorte peer group identifient
les outliers *relatifs* — ce qui est sémantiquement correct pour "at-risk"
et "upsell-ready".

### Pourquoi Streamlit et pas Superset / Metabase ?

Cohérence Python end-to-end avec le pipeline dbt. Itération rapide pour
un prototype analytique orienté décision. Compatible avec le DuckDB local.

### Pourquoi FastMCP ?

Standard open-protocol Anthropic. L'agent (Claude) reçoit des réponses
ancrées dans les données réelles du DuckDB — pas d'hallucination possible
sur les chiffres métier exposés via les outils.

---

## Limitations honnêtes

| Limitation | Impact | Mitigation |
|---|---|---|
| Fenêtre 30 jours (vols) | Pas de signal saisonnalité | Traiter comme snapshot état actuel |
| ~22 pax/vol (load factor irréaliste) | Marges USD sous-estimées | Utiliser margin **%** et RASK-CASK comme métriques comparatives |
| Coûts synthétiques | Valeurs absolues approximatives | Rankings robustes · ordres de grandeur publics |
| Reviews English-only | ~40% base parlerait français | Colonne `language` prête pour extension multilingue |
| Tous customers actifs (starter) | Cohorte at-risk petite (6) | Seuils quantiles adaptatifs · s'améliore avec 12 mois de données |

---

## Prochaines étapes

**Court terme**
- Étendre la fenêtre à 12 mois (saisonnalité, recency réaliste)
- Données concurrents (ASKY, Air Sénégal, Brussels Airlines)
- Support multilingue reviews (modèle NLP français)

**Moyen terme**
- Migration DuckDB → Trino + Iceberg (SQL déjà ANSI-compatible)
- Vrais coûts d'exploitation Air CI (remplacer synthétique)
- CI/CD dbt Cloud · GitHub Actions sur chaque PR

**Long terme**
- Ontologie formelle OWL/SHACL pour le raisonnement explicite
- Embeddings sentence-transformers → RAG réel sur les reviews
- Revenue management : forecasting demande par route

---

## Reproductibilité complète

```bash
# Depuis zéro — résultats identiques garantis

# 1. Données
python scripts/generate_synthetic_data.py \
  --starter air_cote_divoire_starter_dataset.xlsx \
  --out-dir data/synthetic/

# 2. Seeds
python scripts/setup_seeds.py

# 3. Pipeline
cd dbt_project
export DBT_PROFILES_DIR=.
dbt seed && dbt run && dbt test

# 4. Dashboard
cd ..
streamlit run dashboard/app.py

# 5. MCP Demo (sans Claude Desktop)
cd mcp_server
python demo.py
```

**SEED=42** dans le générateur → output déterministe.
**73 tests dbt** → intégrité référentielle et cohérence des enums garanties.

---

*Soumission : Artefact Analytics Engineer Challenge — Niveau Mid-Level*
