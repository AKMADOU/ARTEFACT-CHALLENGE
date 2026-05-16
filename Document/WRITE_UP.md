# Write-up — Air CI Growth Allocation Analytics

**Artefact Analytics Engineer Challenge — Submission**
Niveau visé : Mid-level

---

## 1. Résumé exécutif

Ce projet construit un analytics product end-to-end qui aide la direction
d'Air Côte d'Ivoire à décider où allouer son budget sur 12 mois entre
expansion réseau, rétention client, et upsell/cross-sell.

**Réponse à la question de décision :**

| Rang | Levier | Payback | Justification data |
|---|---|---|---|
| 1 | Upsell / Cross-sell | 0–3 mois | Attach rate 83% mais ARPU lounge 2.1% — mix shift vers items à valeur |
| 2 | Rétention client | 3–6 mois | 6 customers Silver/Gold à LTV $98K désengagés loyalty |
| 3 | Demand gen Paris | 6–12 mois | Paris opère à 9.3% LF — l'avion est là, la demande manque |
| — | Network expansion | Not now | Prématuré : Paris doit atteindre ≥65% LF d'abord |

---

## 2. Architecture

### Choix de stack

**DuckDB + dbt** pour un challenge solo : aucune infrastructure (zéro serveur,
zéro cloud), pipeline reproductible en 3 commandes. Le SQL est écrit en
style ANSI compatible Trino pour la portabilité en production.

**Streamlit** pour le dashboard : cohérence Python end-to-end, itération
rapide, idéal pour un prototype analytique orienté décision.

**FastMCP** pour le serveur AI : le standard open-protocol qui permet à
Claude (ou tout LLM compatible) d'appeler les outils de façon structurée.

### Choix de modélisation

**Star schema à 3 grains distincts** (fct_flights, fct_bookings,
fct_reviews_sentiment) plutôt qu'un fait unique : chaque grain répond à
une question différente (route P&L / upsell par pax / NPS par review).
Les combiner en un seul fait produirait des fan traps et du count inflation.

**Seuils data-adaptatifs** dans les ontology rules : la donnée starter
sur-échantillonne les customers actifs (tous bookent 21-58× en 3 mois),
rendant les seuils absolus (ex: attach < 50%) sans signification. Les
quantiles de la cohorte peer group sont plus robustes et plus défendables.

**Semantic layer MetricFlow** : définir `load_factor` et `route_margin_pct`
une seule fois garantit que le dashboard et l'agent AI produisent exactement
le même chiffre. C'est ce qui rend le MCP "grounded" — il ne calcule pas,
il lit depuis la même couche que le BI.

---

## 3. Phase 1 — Données synthétiques

### Ce qu'on a ajouté et pourquoi

**`route_operating_costs`** — le starter n'a aucune donnée de coût. Sans
ça, impossible de calculer une marge, et la question centrale ("investir où
pour maximiser la croissance *rentable*") devient insoluble. C'est le dataset
le plus critique.

**`customer_reviews`** (3 073 reviews) — la source non-structurée requise par
le brief. Elle connecte la satisfaction perçue au contexte opérationnel
(flight_status) via flight_id. Rating conditionné sur outcome (On-Time:
3.85★, Delayed: 2.53★) — pas du bruit aléatoire, un signal utile.

**`loyalty_transactions`** — le `loyalty_tier` du starter est statique.
L'activité loyalty permet de distinguer les customers engagés des dormants,
ce qui est le signal central de l'ontology rule at-risk.

**Validation de la cohérence :**
- `Σ ancillary_purchases.total_price` = `Σ bookings.ancillary_revenue` exactement ($0 d'écart)
- Rating × flight_status corrélation propre (Delayed 2.53★ vs On-Time 3.85★)

---

## 4. Phase 2 — Pipeline

### Layering et matérialisation

| Couche | Matérialistion | Raison |
|---|---|---|
| staging | view | Toujours frais, coût négligeable |
| intermediate | view | Logique transiente, pas de cache |
| marts/core | table | Surface BI publiée, cache pour perfs |
| marts/analytics | table | Ontology rules sont coûteuses (cross join quantiles) |

### Tests (73, tous verts)

- `unique` + `not_null` sur tous les PKs
- `relationships` sur toutes les FKs
- `accepted_values` sur tous les enums (route_type, fare_class, flight_status, etc.)

Ces tests constituent le "quality contract" : si un upstream change, le
pipeline échoue explicitement plutôt que silencieusement.

---

## 5. Limitations et honnêteté analytique

**Le starter a ~22 pax/vol** (load factor 5-20%), ce qui n'est pas
commercialement réaliste. Conséquences :
- Les marges absolues (USD) sont sous-estimées proportionnellement
- Paris (-87%) reflète l'underuse, pas une non-rentabilité structurelle
- On utilise margin **%** et RASK-CASK comme métriques comparatives

**Fenêtre de 30 jours** (Janvier 2025 uniquement pour les vols) : pas
de saisonnalité observable. Les recommandations sont basées sur un snapshot
de l'état actuel, pas sur des tendances.

**Coûts synthétiques** : les benchmarks sont des ordres de grandeur
publics (A330neo ~$9 500/block-hour), pas les coûts réels d'Air CI. Les
*rankings* de rentabilité sont robustes ; les valeurs absolues ne le sont pas.

**Reviews English-only** : 100% anglais dans la génération pour simplifier
le NLP. En production, ~40% des reviews seraient en français. La colonne
`language` permet l'extension multilingue.

**At-risk cohort** : 6 customers identifiés (sur 300). Ce nombre est faible
parce que le starter n'a pas de variance de recency (tous actifs). En
production avec une fenêtre 12 mois, la cohorte serait significativement
plus large.

---

## 6. Next steps

### Court terme (si plus de temps sur le challenge)

- [ ] Étendre la fenêtre temporelle à 12 mois pour observer la saisonnalité
- [ ] Ajouter les données concurrents (capacités ASKY, Air Sénégal) pour
      le competitive positioning
- [ ] Multi-langue sur les reviews (modèle NLP français)
- [ ] Snapshot dbt pour historiser les ontology rules (suivi de la cohorte
      at-risk dans le temps)

### Moyen terme (production)

- [ ] Remplacer DuckDB par Trino + Iceberg (le SQL est portable)
- [ ] Intégrer les vrais coûts d'exploitation (non-synthétiques)
- [ ] Pipeline Airflow/Prefect pour l'orchestration
- [ ] CI/CD avec dbt Cloud ou GitHub Actions (dbt test sur chaque PR)
- [ ] Embeddings sur les reviews (sentence-transformers) pour une vraie
      semantic search dans le MCP

### Long terme (différenciation senior)

- [ ] Ontologie formelle OWL/SHACL pour les business rules
- [ ] Data Vault 2.0 pour l'auditabilité et l'historisation
- [ ] Revenue management integration (forecasting demand par route)
- [ ] A/B test framework sur les offres upsell

---

## 7. Reproductibilité

Tout le projet est déterministe :

```bash
# Depuis zéro → résultats identiques
python scripts/generate_synthetic_data.py --starter <xlsx> --out-dir data/synthetic/
python scripts/setup_seeds.py
cd dbt_project && dbt seed && dbt run && dbt test
```

SEED=42 dans le générateur. Les 73 tests dbt garantissent l'intégrité
référentielle et la cohérence des enums à chaque run.
