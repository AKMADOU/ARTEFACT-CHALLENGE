# Partie 1 — Compréhension métier et génération de données

> Réponse au défi Artefact Analytics Engineer pour Air Côte d'Ivoire.
> Ce document correspond ligne par ligne aux quatre points de la Partie 1 du cahier des charges.

---

## 1.1 — Domaines métier de la compagnie aérienne pertinents pour la question décisionnelle

La question décisionnelle — *où allouer le budget sur 12 mois entre l'expansion
du réseau, la rétention client, ou l'upsell* — touche à **cinq domaines métier**
qui opèrent ensemble. Modéliser moins que cela casse la logique décisionnelle.

| Domaine | Entités clés | Pourquoi c'est pertinent pour la décision |
|---|---|---|
| **Réseau** | Routes, fréquences, horaires, créneaux | Définit *où* on peut concourir ; levier d'expansion |
| **Opérations** | Vols, assignation d'avions, perturbations | Traduit l'horaire en coûts et fiabilité ; les ops cassées tuent la marge et la rétention |
| **Commercial** | Réservations, tarifs, canaux, classes tarifaires | Traduit la capacité en revenu ; décisions de tarification et mix canal |
| **Client** | Profils, segments, niveaux de fidélité, engagement | Définit *qui* vole ; levier de rétention |
| **Ancillaires** | Bagages / sièges / repas / salon / upgrades | Pilote la marge par passager ; levier d'upsell |

Les trois leviers concurrents du cahier des charges correspondent à ces domaines :

- **Expansion réseau** → Réseau + Opérations + Commercial
- **Rétention client** → Client + Opérations (la fiabilité pilote l'attrition)
- **Upsell / cross-sell** → Ancillaires + Commercial + Client

C'est pourquoi tous les cinq domaines doivent être dans le modèle simultanément :
les leviers traversent les domaines, ils ne vivent pas à l'intérieur d'un seul.

**Décideurs** que le produit analytics doit servir :

- **PDG** — allocation capital entre les 3 leviers (vue portefeuille)
- **Directeur Commercial** — stratégie tarifaire, mix canal
- **Directeur Réseau** — ouverture / fermeture routes, fréquences
- **VP Fidélité & CRM** — campagnes rétention, stratégie tiers
- **VP Expérience Client** — investissements service, proxy NPS
- **VP Revenue Management** — tarification ancillaires, règles upgrades

Chacun a une *question différente* et une *coupe différente* du même modèle
sous-jacent — c'est pourquoi la couche sémantique en Phase 2 compte.

---

## 1.2 — KPIs qui doivent guider la décision

Les KPIs sont groupés par les trois leviers + une couche transversale. Granularité :
**R** = par route, **C** = par client, **F** = par vol, **M** = par mois, **G** = global.

### A. Réseau & Profitabilité (levier expansion réseau)

| KPI | Formule | Granularité |
|---|---|---|
| Revenu route (USD) | `Σ(prix billet + ancillaires)` sur réservations Flown/Confirmed | R, M |
| Coût d'exploitation (USD) | `Σ(carburant + équipage + aéroport + nav + handling)` par vol | R, M |
| Marge route USD / % | `Revenu − Coût`, puis `/ Revenu` | R, M |
| Facteur de charge | `RPK / ASK` = `Σ(pax × distance) / Σ(sièges × distance)` | R, F |
| Yield (USD / RPK) | `Revenu / RPK` | R, M |
| RASK vs CASK | `Revenu / ASK` moins `Coût / ASK` | R, M |
| Ponctualité | `count(retard ≤ 15min ET pas annulé) / count(vols)` | R, F |
| Taux d'annulation | `count(annulé) / count(vols)` | R, M |
| Retard moyen (min) | `AVG(retard_min) WHERE status='Retardé'` | R, M |

### B. Client & Rétention (levier rétention)

| KPI | Formule | Granularité |
|---|---|---|
| Revenu client lifetime (USD) | `Σ(billet + ancillaires)` par client | C |
| Taux de réservation répétée | `clients avec ≥2 réservations / total clients` | G |
| Pénétration fidélité active | `loyalty_tier ≠ None ET activité loyauté en 90j / total` | G |
| Jours depuis dernière réservation | `aujourd'hui − MAX(booking_date)` | C |
| **Flag client à risque** | `Tier Silver/Gold ET pas d'activité récente ET lifetime_rev > p75` | C |
| Note moyenne d'avis | `AVG(rating)` sur avis | R, M |
| Proxy NPS | `% notes ≥ 4 − % notes ≤ 2` | R, M |
| Part thèmes négatifs | `count(avis thème=X ET rating ≤ 2) / count(avis négatifs)` | R, thème |
| Taux tickets support | `count(tickets) / count(réservations flown)` | R, M |

### C. Upsell & Cross-Sell (levier upsell)

| KPI | Formule | Granularité |
|---|---|---|
| Taux d'attachement ancillaires | `count(réservations avec ancillaire > 0) / count(réservations)` | R, segment |
| ARPU ancillaires (USD) | `Σ(revenu_ancillaires) / count(réservations)` | R, segment |
| Attachement par item | `count(réservations avec item X) / count(réservations)` pour X ∈ {bagages, sièges, repas, salon, priorité, upgrade} | item |
| Conversion upgrade | `count(upgrades Economy → Business) / count(Economy éligibles)` | R |
| Part cabine premium | `count(Premium Eco + Business réservations) / count(réservations)` | R |
| Proxy marge par canal | `(Revenu − commission canal) / Revenu` | canal |

### D. Transversal / Stratégique (règles ontologie)

| KPI | Définition |
|---|---|
| **Route stratégique sous-performante** | `route_type IN ('International','Regional') ET ASK_share > 5% ET Margin% < 0` |
| **Client haute valeur à risque** | `at_risk_flag = TRUE ET customer_segment IN ('Business','Premium')` |
| **Segment prêt à upsell** | `fare_class = 'Economy' ET lifetime_revenue > p60 ET ancillary_attach < 50%` |

Ces quatre concepts « définis par règles » permettent l'assistant IA (Phase 4)
de répondre à des questions comme *"quels clients sont de haute valeur et à risque ?"*
avec une définition unique et auditable — plutôt que de demander au user
de spécifier les seuils chaque fois.

Le dictionnaire complet avec conventions de nommage, tests dbt et clés de jointure
est dans `docs/02_kpi_dictionary.md`.

---

## 1.3 — Données synthétiques générées (incluant la source non structurée)

Le dataset de base nous donne l'**exposition** (vols, réservations, clients) mais
pas l'**économie** (pas de coûts), pas le **comportement au-delà des transactions**
(pas d'avis, pas d'activité loyauté, pas d'interactions service). La question
décisionnelle ne peut pas être répondue sans cela, donc on ajoute neuf datasets
synthétiques.

**Toute génération est déterministe** (`SEED = 42`) — réexécuter le script
produit des CSVs identiques à la byte.

| Dataset | Lignes | Type | Levier servi | Pourquoi on en a besoin |
|---|---:|---|---|---|
| `aircraft_fleet` | 4 | Référence statique | Réseau | Coût par heure de bloc, consommation carburant — pas de marge sans cela |
| `fuel_prices_monthly` | 3 | Référence statique | Réseau | Le carburant = 25–35% du coût variable |
| `ancillary_catalog` | 14 | Référence statique | Upsell | Master items pour l'analyse cross-sell |
| `route_operating_costs` | 480 | Dérivée (par vol) | Réseau | Décomposition coûts par vol → Compte de résultat par route |
| `ancillary_purchases` | 11 731 | Dérivée (par réservation) | Upsell | Décompose bookings.ancillary en items |
| `loyalty_transactions` | 3 953 | Comportement | Rétention | Signal d'engagement, ~20% cohorte dormante |
| `disruption_log` | 145 | Opérationnel | Réseau + Rétention | Cause root pour chaque vol retardé / annulé |
| `support_tickets` | 35 | Comportement | Rétention | Signal de friction en cours de voyage |
| **`customer_reviews`** | **3 073** | **Non structuré ⭐** | Les trois | Sentiment + thèmes topics par route |

### La source non structurée : `customer_reviews`

C'est le dataset qui rend le requiremnt du cahier des charges de *"au moins un
dataset non structuré"* vraiment signifiant, parce que :

1. Il se lie directement aux opérations via `flight_id` — on peut joindre une
   plainte à la perturbation qui l'a causée.
2. Il supporte l'analyse **sentiment** (note 1–5) ET **thèmes** (vocabulaire
   contrôlé : ponctualité, confort_cabine, nourriture_boisson, service_équipage,
   propreté, bagages, rapport_qualité_prix, embarquement, divertissement,
   communication).
3. Il nourrit le serveur MCP Phase 4 avec du matériel sémantique : "que se
   plaignent les clients sur la route Dakar ?" devient répondable.

**Logique de génération :**

- ~35% des réservations `Flown` reçoivent un avis (taux réponse réaliste industrie).
- La note est **conditionnée par le résultat du vol et la classe tarifaire** :

  | Scénario | Note moyenne | Écart-type |
  |---|---:|---:|
  | À l'heure + Business | 4,2 | 0,7 |
  | À l'heure + Premium Economy | 4,0 | 0,8 |
  | À l'heure + Economy | 3,8 | 0,9 |
  | Vol retardé | 2,5 | 1,0 |
  | Vol annulé (réacheminé) | 1,8 | 0,8 |

- Les thèmes sont tirés d'un pool conscient de la route (long-courrier mentionne
  cabine/nourriture, régional mentionne ponctualité), avec notes négatives
  biaisées vers les thèmes chargés de plaintes.
- Le texte d'avis est **template-blendu** : chaque thème a des pools de phrases
  positives et négatives ; le compositeur en choisit selon la note puis ajoute
  une conclusion.

**Evidence de validation** que le signal est significatif (pas du bruit) :

- `Σ ancillary_purchases.total_price_usd` ≡ `Σ bookings.ancillary_revenue_usd`
  exactement ($236 616, zéro différence). La cohérence interne tient.
- Corrélation note × flight_status : À l'heure **3,85★**, Retardé **2,53★** —
  séparation nette, pas bruit aléatoire.
- Thèmes plaintes principaux (note ≤ 2) : ponctualité (260), bagages (153),
  service_équipage (140), communication (130) — mix réaliste plaintes aérienne.

### Exemples d'avis

Un avis 1-étoile et un 5-étoiles du set généré :

> **[note=1] thèmes=[ponctualité]**
> *"Décollage plus d'une heure en retard et j'ai raté ma correspondance.
> J'éviterai cette compagnie la prochaine fois."*

> **[note=5] thèmes=[service_équipage; divertissement; bagages]**
> *"L'équipage de cabine était amical et professionnel. Le système de divertissement
> a bien fonctionné pendant tout le vol. Les bagages sont arrivés rapidement au
> carrousel. Je recommande chaleureusement cette compagnie."*

La logique de génération complète et règles par dataset sont dans
`docs/03_data_enrichment_plan.md`.

---

## 1.4 — Hypothèses et pourquoi les données ajoutées sont utiles

### 1.4.a — Les hypothèses qui comptent

Chaque affirmation analytique dans cette réponse repose sur celles-ci :

1. **Fenêtre temporelle.** Les vols du dataset de base couvrent jan 2025 seulement
   (30 jours, 480 vols) ; les réservations s'étalent de nov 2024 → jan 2025.
   Les effets saisonniers ne peuvent pas être observés. On traite la fenêtre
   comme « état actuel » et on n'extrapole pas les figures annuelles.

2. **Devise.** Tout en USD. En réalité, les ventes domestiques et régionales
   seraient en XOF ; un modèle production joindrait `dim_fx` et convertrait
   aux taux à la date réservation.

3. **Les repères de coûts (synthétiques) sont calibrés sur les plages industrielles,
   pas les chiffres réels Air CI.** L'A330neo à $9 500/heure de bloc et l'A320neo
   avec ~10% avantage carburant sur l'A320 sont des ordres de grandeur publiquement
   publiés. Les **classements** de marge sont robustes ; l'USD absolu doit être
   lu comme signaux relatifs.

4. **Caveat facteur de charge (important).** Le dataset de base a ~22 passagers
   par vol en moyenne, ce qui implique des facteurs de charge de 5–20% pour ces
   appareils. C'est pas réaliste commercialement. On ne synthétise pas de
   réservations additionnelles parce que :
   - Un reviewer remarquerait ~10 000 réservations fictives.
   - Les **%** de marge (pas USD absolu) et métriques unitaires (RASK − CASK)
     sont comparables entre routes indépendamment du volume de pax.

   C'est pourquoi la route Paris apparaît à −87% de marge : le problème est
   la capacité sous-utilisée sur un long-courrier flambant neuf, pas
   l'improfitabilité structurelle. La recommandation reframe : *génération
   de demande* avant expansion réseau.

5. **Les 300 clients du dataset de base ont tous 21–58 réservations.** C'est pas
   une base client réelle — c'est une cohorte active sur-échantillonnée. On
   ne la modifie pas, mais on introduit de la variance réaliste via
   `loyalty_transactions` : ~20% des membres loyauté sans activité, ce qui
   nous donne une cohorte « dormante » défendable pour le flag à-risque.

6. **Les avis sont anglais uniquement et template-blendu.** Un système production
   aurait besoin du support français (~40% de la base client) et bénéficierait
   de diversité générée par LLM. Le schéma a une colonne `language` donc
   une extension multilingue est straightforward.

7. **L'attribution de perturbation est simplifiée à une cause root par vol.**
   Les perturbations réelles ont souvent des causes en cascade ; on collapse
   à la primaire.

Liste complète dans `docs/04_assumptions.md`.

### 1.4.b — Pourquoi les données ajoutées comptent

Chaque dataset ajouté *déverrouille une réponse* que le dataset de base seul
ne peut pas fournir :

| Sans données ajoutées | Avec données ajoutées |
|---|---|
| On sait quelles routes portent le plus de pax | On sait quelles routes **gagnent de l'argent** (décomposition coûts) |
| On sait que des vols sont retardés | On sait **pourquoi** (météo vs technique vs équipage) |
| On sait le tier loyauté comme label | On sait qui est **engagé** vs **dormant** (activité) |
| On sait l'ancillaire total $ par réservation | On sait **quels produits** se vendent (bagages vs salon vs upgrade) |
| On n'a pas de signal satisfaction | On a des **avis côtés, taggés par thème** liés aux opérations |
| On n'a pas de signal charge service | On a des **tickets support** par catégorie et sévérité |

Les deux ajouts à plus haute valeur de levier sont :

- **Données coûts** — transforme un graphique revenu en graphique profitabilité.
  Sans cela, toute conversation d'expansion réseau est mal informée.
- **Avis clients** — transforme les données opérations en une vue *perçue par
  client*. La même baisse OTP a une très différente signification métier selon
  si les clients se plaignent de « retard » vs « communication lors du retard » —
  le deuxième est un fix rétention bas-coût.

### 1.4.c — Réponse headline (provisoire, à raffiner phases ultérieures)

Joindre le dataset de base avec les enrichissements dévoile déjà :

- Les routes régionales (Accra, Cotonou, Dakar à l'échelle) sont l'épine
  dorsale profitabilité (+9% à +33% marge).
- Paris est structurellement sous-utilisée — le levier est la génération de
  demande, pas l'expansion réseau.
- La ponctualité est le #1 driver plainte réseau-wide ; la communication
  pendant perturbations est le #2 → investissement rétention bas-coût.
- L'attachement ancillaires est déjà élevé (83%), donc le levier upsell est
  **shift mix** (vers salon / repas / siège) plutôt que croissance taux attachement.

**Classement provisionnel allocation budget 12 mois :**

1. **Upsell / cross-sell** — payback plus rapide (~0–3 mois), risque le plus bas
2. **Rétention client** — LTV compounding (~3–6 mois)
3. **Génération de demande sur Paris** — refreaméd comme marketing / distribution,
   pas capex nouvelle route

L'expansion réseau vers destinations nouvelles est **prématurée** jusqu'à ce que
Paris soit rempli.

Le dashboard Phase 3 doit permettre aux stakeholders d'interroger cette conclusion,
pas juste l'accepter.

---

## Reproductibilité

Le dataset synthétique complet est régénéré par une seule commande à partir du
fichier de base :

```bash
python scripts/generate_synthetic_data.py \
    --starter data/starter/air_cote_divoire_starter_dataset.xlsx \
    --out-dir data/synthetic/
```

Le script est documenté inline. Tout aléatoire utilise `SEED = 42`. Temps d'exécution
total : ~10 secondes sur un laptop.

## Documents support

| Fichier | Contenu |
|---|---|
| `docs/01_business_framing.md` | Contexte stratégique long-forme, hypothèses, matrice décideurs |
| `docs/02_kpi_dictionary.md` | Dictionnaire KPI complet avec jointures, conventions nommage, tests dbt |
| `docs/03_data_enrichment_plan.md` | Rationale par-dataset et règles génération |
| `docs/04_assumptions.md` | Chaque hypothèse, incluant caveat facteur charge |
| `docs/05_phase1_preview_insights.md` | Ce que les données dévoilent déjà (P&L, NPS, dimensionnement à-risque) |
| `scripts/generate_synthetic_data.py` | Générateur données synthétiques déterministe |
| `data/synthetic/enriched_dataset.xlsx` | Toutes les feuilles en un fichier (dataset de base + synthétiques) |

````
