# Video Scripts — Dashboard & AI Demo

Deux vidéos à enregistrer en screen recording (QuickTime ou Loom).

---

# VIDÉO 1 — Dashboard (2 min 30)

**Outil** : QuickTime Player → File → New Screen Recording (ou Loom)
**Fenêtre** : Chrome plein écran sur http://localhost:8501
**Préparer** : lancer `streamlit run dashboard/app.py` avant

---

## [0:00 – 0:15] — Intro

*Narration (voix ou slide d'intro) :*
> "Voici le Executive Growth Allocation Dashboard d'Air Côte d'Ivoire.
> Il répond à une question : où investir le budget des 12 prochains mois
> pour maximiser la croissance rentable ? 4 pages, 3 leviers analysés."

---

## [0:15 – 0:45] — Page 1 : Network & Profitability

*Actions :* Cliquer sur "🗺️ Network & Profitability"

*Ce qu'on montre + ce qu'on dit :*

1. **KPI cards en haut** — pointer la marge totale -$992K (-24%)
   > "Le réseau est globalement déficitaire, mais regardons par route."

2. **Bar chart marge %** — pointer le contraste Accra +33% / Paris -87%
   > "Accra est le moteur rentable. Paris saigne à -87% de marge."

3. **Route Opportunity Matrix** — insister sur le quadrant bas-gauche (Paris)
   > "La matrice load factor × marge identifie Paris dans le quadrant
   > déficitaire : l'avion vole à 9% de remplissage. Ce n'est pas une
   > route à fermer — c'est une route qui manque de demande."

4. **Donut disruption** — pointer Technical + Weather
   > "30% des disruptions sont techniques — piste d'action maintenance."

---

## [0:45 – 1:15] — Page 2 : Customer & Retention

*Actions :* Cliquer sur "👥 Customer & Retention"

1. **Metric card at-risk** — pointer le chiffre
   > "6 customers Silver/Gold identifiés à risque — $98 000 de LTV
   > concentrés. Chiffre faible parce que la donnée couvre 3 mois ;
   > en 12 mois cette cohorte serait significativement plus large."

2. **NPS proxy par route** — pointer la barre la plus basse
   > "La satisfaction varie fortement par route. La route la moins
   > satisfaisante est directement corrélée au taux de retards."

3. **Bar thèmes négatifs** — pointer Ponctualité en tête
   > "Ponctualité est le sujet n°1 dans les reviews négatives — et c'est
   > une source non-structurée qu'on a rendue structurée via des topic tags."

4. **Table at-risk** — scroller rapidement
   > "La table montre le signal : ces customers ont un ratio engagement
   > loyalty en dessous de la médiane de leurs pairs. C'est la définition
   > d'une ontology rule — pas un seuil arbitraire."

---

## [1:15 – 1:45] — Page 3 : Upsell & Cross-sell

*Actions :* Cliquer sur "💰 Upsell & Cross-sell"

1. **Metric card attach rate**
   > "83% d'attach rate — très élevé. Le levier n'est pas 'd'attacher plus',
   > c'est 'attacher des produits plus chers'."

2. **Bar grouped attach par item** — pointer Lounge à 2.1%
   > "Lounge access est à 2% seulement. Pourtant c'est le produit le plus
   > rentable par booking, à $45-80 par transaction."

3. **Donut mix revenus** — pointer la part baggage dominante
   > "80% du revenu ancillaire vient du baggage. C'est un symptôme : on vend
   > ce qui est obligatoire, pas ce qui crée de la valeur."

4. **Table upsell-ready** — scroller
   > "30 customers Economy identifiés comme sous-attachés par rapport à leurs
   > pairs — $524K de LTV cumulée. C'est la cible d'une campagne lounge."

---

## [1:45 – 2:30] — Page 4 : Decision Layer ⭐ (la plus importante)

*Actions :* Cliquer sur "🎯 Decision Layer" — prendre le temps ici

1. **Headline en vert**
   > "La réponse à la question du brief est ici, en haut, avec la
   > justification data immédiatement en dessous."

2. **Donut allocation budget**
   > "40% upsell, 30% rétention, 20% demand gen Paris, 10% réserve.
   > Ce n'est pas une intuition — c'est ce que les données indiquent."

3. **3 colonnes Routes / Rétention / Upsell**
   > "Les 3 ontology rules alimentent directement ces 3 colonnes.
   > Routes à défendre : Paris et Dakar — ontology strategic_underperforming.
   > Customers à retenir : les 6 at-risk avec leur signal explicité.
   > Offres à pousser : les 30 upsell-ready avec les seuils data."

4. **Table executive finale**
   > "La dernière table est celle qu'on présente au CEO : levier, action,
   > KPI de succès, ROI estimé. Tout est ancré dans la donnée."

---

*Fin de vidéo :*
> "Ce dashboard est alimenté par 30 modèles dbt, 73 tests de qualité,
> et une source non-structurée (reviews) intégrée dans le pipeline."

---
---

# VIDÉO 2 — AI Interaction MCP (1 min 30)

**Outil** : QuickTime screen recording sur Claude Desktop
**Préparer** :
1. Le serveur MCP doit être connecté (marteau 🔨 visible)
2. Ouvrir un New chat
3. Taper les questions une par une, attendre la réponse complète avant de continuer

---

## [0:00 – 0:10] — Setup visible

*Montrer la sidebar Claude Desktop avec le marteau 🔨 "airci-analytics"*
> (narration optionnelle) "Le serveur MCP Air CI est connecté à Claude.
> Il expose 5 outils sur les données dbt/DuckDB."

---

## [0:10 – 0:35] — Question 1 : Route analysis

**Taper :**
> "Quelles routes d'Air CI méritent plus de budget au prochain trimestre ?
> Justifie avec les données."

*Attendre que Claude appelle `query_route_metrics` et réponde.*

*Ce qu'on veut voir :* Claude citant les chiffres exacts (Accra +33%,
Paris -87%, load factor 9.3%). Si Claude reformule sans citer de chiffres,
relancer avec "cite les chiffres exacts retournés par les outils".

---

## [0:35 – 1:00] — Question 2 : Reviews non-structurées

**Taper :**
> "Que disent les clients mécontents sur la route Paris ?
> Cite des reviews réels."

*Attendre que Claude appelle `search_reviews_by_route`.*

*Ce qu'on veut voir :* Claude citant de vraies reviews datées avec le flag
"⚠️ Vol Delayed", montrant que le contexte opérationnel est joint au texte.

---

## [1:00 – 1:20] — Question 3 : Budget recommendation

**Taper :**
> "Où doit investir Air CI pour maximiser la croissance rentable ?
> Donne la recommandation avec le ROI estimé."

*Attendre que Claude appelle `recommend_budget_allocation`.*

*Ce qu'on veut voir :* Claude reprenant le ranking (upsell → rétention →
demand gen Paris → hold network expansion) avec les chiffres ROI ($29K
protégés si 30% convertis, $524K LTV upsell-ready).

---

## [1:20 – 1:30] — Closing

*Montrer les 5 outils dans la sidebar ou dans la réponse Claude*
> (narration) "Le MCP expose 5 outils : route metrics, at-risk customers,
> semantic search sur les reviews, budget allocation, et route P&L explain.
> Tout est ancré dans les mêmes marts dbt que le dashboard."

---

## Tips enregistrement

**Dashboard :**
- Zoom navigateur à 90% pour que tout tienne à l'écran
- Mode sombre Streamlit (Settings → Theme → Dark) pour un meilleur contraste
- Désactiver les notifications macOS (Ne pas déranger)

**Claude Desktop :**
- Fenêtre plein écran
- Aller assez lentement pour que les tool calls soient visibles
- Si Claude ne cite pas les chiffres, ajouter "en citant les valeurs exactes retournées"

**Durée cible :**
- Dashboard : 2 min 30 (ne pas dépasser 3 min)
- AI : 1 min 30 (dense, percutant)

**Montage (optionnel) :**
- Couper les temps de chargement
- Ajouter des sous-titres sur les chiffres clés
- Outil simple : iMovie ou Loom (trim intégré)
