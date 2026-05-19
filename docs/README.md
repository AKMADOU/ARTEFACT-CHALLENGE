# Air Côte d'Ivoire — Growth Allocation Analytics

**Artefact Analytics Engineer Challenge**

> *Where should Air Côte d'Ivoire invest a constrained 12-month budget
> to maximize profitable growth: route expansion, customer retention,
> or upsell / cross-sell?*

---

## Quick start (3 commands)

```bash
# 1. Générer les données synthétiques
python scripts/generate_synthetic_data.py \
  --starter air_cote_divoire_starter_dataset.xlsx \
  --out-dir data/synthetic/

# 2. Construire le pipeline dbt (DuckDB)
python scripts/setup_seeds.py
cd dbt_project && export DBT_PROFILES_DIR=. && dbt seed && dbt run && dbt test

# 3. Lancer le dashboard
cd .. && streamlit run dashboard/app.py
```

---

## Architecture d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1 — Données                                          │
│  Starter Excel (5 sheets) + 9 datasets synthétiques         │
│  └── scripts/generate_synthetic_data.py (SEED=42)           │
└──────────────────────────┬──────────────────────────────────┘
                           │ 14 CSV seeds
┌──────────────────────────▼──────────────────────────────────┐
│  PHASE 2 — Pipeline dbt + DuckDB                            │
│  stg → int → marts/core → marts/analytics                   │
│  30 modèles | 73 tests | Semantic Layer (MetricFlow)        │
│  └── dbt_project/                                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ airci.duckdb
          ┌────────────────┴────────────────┐
          ▼                                 ▼
┌─────────────────────┐       ┌────────────────────────────┐
│  PHASE 3 — Dashboard│       │  PHASE 4 — MCP Server      │
│  Streamlit 4 pages  │       │  5 outils AI               │
│  dashboard/app.py   │       │  mcp_server/server.py      │
└─────────────────────┘       └────────────────────────────┘
```

---

## Structure du projet

```
airci_challenge/
├── README.md                          ← vous êtes ici
├── air_cote_divoire_starter_dataset.xlsx
│
├── scripts/
│   ├── generate_synthetic_data.py     ← Phase 1 : génération données
│   └── setup_seeds.py                 ← copie les CSVs dans seeds/
│
├── data/
│   ├── starter/                       ← Excel original (read-only)
│   └── synthetic/                     ← 9 CSVs générés + enriched_dataset.xlsx
│
├── docs/                              ← Phase 1 documentation
│   ├── 01_business_framing.md
│   ├── 02_kpi_dictionary.md
│   ├── 03_data_enrichment_plan.md
│   ├── 04_assumptions.md
│   └── 05_phase1_preview_insights.md
│
├── dbt_project/                       ← Phase 2 pipeline
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/                         ← 14 CSV (starter + synthétiques)
│   └── models/
│       ├── staging/    (14 vues)
│       ├── intermediate/ (4 vues)
│       └── marts/
│           ├── core/   (7 tables : 4 dims + 3 facts)
│           └── analytics/ (4 tables : 3 ontology + 1 BI)
│
├── dashboard/                         ← Phase 3 Streamlit
│   ├── app.py
│   ├── db.py
│   ├── config.py
│   └── requirements.txt
│
├── mcp_server/                        ← Phase 4 MCP
│   ├── server.py
│   ├── demo.py
│   └── README.md
│
└── deliverables/                      ← Phase 5 (ce dossier)
    ├── README.md (ce fichier)
    ├── DATA_DICTIONARY.md
    ├── WRITE_UP.md
    └── VIDEO_SCRIPTS.md
```

---

## Pré-requis

```bash
Python 3.10+
pip install dbt-core dbt-duckdb duckdb pandas openpyxl \
            streamlit plotly "mcp[cli]"
```

---

## Phase 1 — Données

### Données starter
5 feuilles Excel : **Airports** (10), **Routes** (12), **Customers** (300),
**Flights** (480, Janvier 2025), **Bookings** (11 475, Nov 2024–Jan 2025).

### Données synthétiques ajoutées (9 datasets)

| Dataset | Lignes | Rôle |
|---|---:|---|
| `aircraft_fleet` | 4 | Coûts par block hour (indispensable pour le P&L) |
| `fuel_prices_monthly` | 3 | Prix carburant Nov 2024–Jan 2025 |
| `ancillary_catalog` | 14 | Référentiel produits ancillaires |
| `route_operating_costs` | 480 | Décomposition coût par vol |
| `ancillary_purchases` | 11 731 | Décomposition ancillary par item |
| `loyalty_transactions` | 3 953 | Activité loyalty (signal engagement) |
| `disruption_log` | 145 | Cause racine des retards/annulations |
| `support_tickets` | 35 | Interactions service client |
| **`customer_reviews`** | **3 073** | **⭐ Source non-structurée** |

Générer : `python scripts/generate_synthetic_data.py --starter <path> --out-dir data/synthetic/`

---

## Phase 2 — Pipeline dbt

```bash
cd dbt_project
export DBT_PROFILES_DIR=.
dbt seed    # PASS=14
dbt run     # PASS=30 en ~2s
dbt test    # PASS=73
```

### Modèles clés

| Modèle | Type | Description |
|---|---|---|
| `fct_flights` | Fact | Grain : 1 vol. Revenue + cost + margin + load factor |
| `fct_bookings` | Fact | Grain : 1 booking. Ticket + ancillary décomposé |
| `fct_reviews_sentiment` | Fact | Grain : 1 review. Rating + sentiment + 10 topic flags |
| `dim_route` | Dim | Routes enrichies avec villes |
| `dim_customer` | Dim | Customer avec LTV + engagement loyalty |
| `route_pnl_monthly` | Analytics | P&L route × mois, BI-ready |
| `ontology_strategic_underperforming_route` | Analytics | Routes stratégiques déficitaires |
| `ontology_highvalue_atrisk_customer` | Analytics | Customers Silver/Gold désengagés |
| `ontology_upsell_ready_segment` | Analytics | Customers Economy sous-attachés |

### Portabilité Trino
Le SQL est ANSI-standard. Points de divergence DuckDB/Trino commentés inline :
- `x::type` → `CAST(x AS type)`
- `generate_series` → `sequence`
- `quantile_cont` → `approx_percentile`

---

## Phase 3 — Dashboard Streamlit

```bash
streamlit run dashboard/app.py
# Ouvre http://localhost:8501
```

4 pages :
1. **🗺️ Network & Profitability** — Route P&L, opportunity matrix
2. **👥 Customer & Retention** — NPS proxy, at-risk customers, topics négatifs
3. **💰 Upsell & Cross-sell** — Attach rates, ARPU, segments cibles
4. **🎯 Decision Layer** — Recommandation executive avec evidence trail

Variable d'env pour pointer sur un DuckDB custom :
```bash
DBT_DUCKDB_PATH=/path/to/airci.duckdb streamlit run dashboard/app.py
```

---

## Phase 4 — MCP Server

```bash
# Tester sans Claude
cd mcp_server && python demo.py

# Connecter à Claude Desktop
# → voir mcp_server/README.md
```

5 outils exposés : `query_route_metrics`, `get_at_risk_customers`,
`search_reviews_by_route`, `recommend_budget_allocation`, `explain_route_pnl`.

Config Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`) :
```json
{
  "mcpServers": {
    "airci-analytics": {
      "command": "/Applications/anaconda3/bin/python",
      "args": ["/chemin/absolu/mcp_server/server.py"],
      "env": { "DBT_DUCKDB_PATH": "/chemin/absolu/dbt_project/airci.duckdb" }
    }
  }
}
```

---

## Résultats headline

| Métrique | Valeur |
|---|---|
| Revenue réseau (Jan 2025) | $4.1M |
| Marge réseau | −$992K (−24%) |
| Meilleure route | ABJ→ACC +33% marge |
| Pire route | ABJ→CDG −87% marge |
| Load factor Paris | 9.3% (vs ~65% break-even) |
| Customers at-risk identifiés | 6 (LTV $98 728) |
| Customers upsell-ready | 30 (LTV $524 302) |

## Réponse à la question de décision

**Ranking budget 12 mois :**
1. **Upsell/cross-sell** — mix shift vers lounge/upgrade (payback 0–3 mois)
2. **Rétention client** — cohorte at-risk ciblée (payback 3–6 mois)
3. **Demand generation Paris** — marketing/distribution, pas nouvelle route
4. **Network expansion** — prématuré tant que Paris < 65% load factor
