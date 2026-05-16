#!/usr/bin/env python3
"""
Air Côte d'Ivoire — MCP Analytics Server
Fichier autonome, aucune dépendance locale (pas de db_queries, pas de search).
Run: python server.py
"""

import json, os, sys
import duckdb
import pandas as pd
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

# ─── DuckDB — chemin + auto-détection des schémas ───────────────

def get_db_path() -> str:
    env = os.environ.get("DBT_DUCKDB_PATH")
    if env and Path(env).exists():
        return env
    for p in [
        Path(__file__).parent.parent / "dbt_project" / "airci.duckdb",
        Path("dbt_project") / "airci.duckdb",
        Path("airci.duckdb"),
    ]:
        if p.exists():
            return str(p)
    raise FileNotFoundError("airci.duckdb introuvable. Lance dbt seed && dbt run d'abord.")


_sm: dict = {}

def schema_map() -> dict:
    global _sm
    if _sm:
        return _sm
    con = duckdb.connect(get_db_path(), read_only=True)
    df = con.execute("SELECT table_schema, table_name FROM information_schema.tables").fetchdf()
    con.close()
    markers = {
        "analytics": ["route_pnl_monthly", "ontology_highvalue_atrisk_customer"],
        "marts":     ["fct_flights", "fct_bookings", "fct_reviews_sentiment", "dim_customer"],
    }
    for layer, tables in markers.items():
        for t in tables:
            row = df[df["table_name"] == t]
            if not row.empty:
                _sm[layer] = row.iloc[0]["table_schema"]
                break
    _sm.setdefault("analytics", "main_analytics")
    _sm.setdefault("marts",     "main_marts")
    return _sm


def _sql(sql: str) -> str:
    sm = schema_map()
    return sql.replace("main_analytics.", sm["analytics"] + ".") \
              .replace("main_marts.",     sm["marts"] + ".")


def q(sql: str) -> pd.DataFrame:
    con = duckdb.connect(get_db_path(), read_only=True)
    try:
        return con.execute(_sql(sql)).fetchdf()
    finally:
        con.close()


def to_text(df: pd.DataFrame, n: int = 40) -> str:
    return "Aucun résultat." if df.empty else df.head(n).to_string(index=False)


# ─── MCP Server ─────────────────────────────────────────────────

mcp = FastMCP(
    name="airci-analytics",
    instructions=(
        "Assistant analytique Air Côte d'Ivoire. "
        "Réponds toujours en citant les chiffres exacts retournés par les outils."
    ),
)


@mcp.tool()
def query_route_metrics(
    route_id: Optional[str] = None,
    route_type: Optional[str] = None,
    min_margin_pct: Optional[float] = None,
    max_margin_pct: Optional[float] = None,
    sort_by: str = "margin_pct",
) -> str:
    """
    Retourne le P&L et les KPIs de performance des routes Air CI.

    Args:
        route_id:       Filtrer sur une route ex: "R009" (Paris). None = toutes.
        route_type:     "Domestic", "Regional" ou "International".
        min_margin_pct: Marge % minimum (ex: 0 pour rentables seulement).
        max_margin_pct: Marge % maximum (ex: -0.01 pour déficitaires).
        sort_by:        "margin_pct", "total_revenue_usd", "load_factor_pct".
    """
    where = []
    if route_id:        where.append(f"route_id = '{route_id.upper()}'")
    if route_type:      where.append(f"route_type = '{route_type}'")
    if min_margin_pct is not None: where.append(f"margin_pct >= {min_margin_pct}")
    if max_margin_pct is not None: where.append(f"margin_pct <= {max_margin_pct}")

    w   = "WHERE " + " AND ".join(where) if where else ""
    col = sort_by if sort_by in {"margin_pct","total_revenue_usd","load_factor_pct"} else "margin_pct"

    df = q(f"""
        SELECT route_id, route_label, route_type,
               SUM(flights_count)                                              AS vols,
               SUM(pax_count)                                                  AS pax,
               ROUND(SUM(total_revenue_usd))                                   AS revenue_usd,
               ROUND(SUM(total_operating_cost_usd))                            AS cout_usd,
               ROUND(SUM(margin_usd))                                          AS marge_usd,
               ROUND(SUM(margin_usd)*100.0/NULLIF(SUM(total_revenue_usd),0),1) AS margin_pct,
               ROUND(AVG(load_factor)*100,1)                                   AS load_factor_pct,
               ROUND(AVG(on_time_performance)*100,1)                           AS otp_pct,
               ROUND(AVG(rask),4) AS rask, ROUND(AVG(cask),4) AS cask
        FROM main_analytics.route_pnl_monthly {w}
        GROUP BY route_id, route_label, route_type
        ORDER BY {col} DESC
    """)

    if df.empty:
        return "Aucune route trouvée."

    best  = df.iloc[0]
    worst = df.iloc[-1]
    rentables = (df["margin_pct"] > 0).sum()
    header = (
        f"=== Métriques routes ({len(df)} routes) ===\n"
        f"Rentables : {rentables}/{len(df)} | "
        f"Meilleure : {best['route_label']} ({best['margin_pct']:+.1f}%) | "
        f"Pire : {worst['route_label']} ({worst['margin_pct']:+.1f}%)\n\n"
    )
    return header + to_text(df)


@mcp.tool()
def get_at_risk_customers(
    min_ltv_usd: float = 0,
    segment: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    Retourne les customers high-value (Business/Premium, Silver/Gold)
    montrant un signal de désengagement loyalty.

    Args:
        min_ltv_usd: LTV minimum en USD (défaut 0 = tous).
        segment:     "Business" ou "Premium".
        limit:       Nombre max de résultats.
    """
    where = ["1=1"]
    if min_ltv_usd > 0: where.append(f"lifetime_revenue_usd >= {min_ltv_usd}")
    if segment:         where.append(f"customer_segment = '{segment}'")

    df = q(f"""
        SELECT customer_id, customer_segment, loyalty_tier,
               ROUND(lifetime_revenue_usd)       AS ltv_usd,
               total_bookings, earn_event_count,
               ROUND(earn_events_per_booking,2)  AS engagement,
               ROUND(cohort_median_engagement,2) AS cohort_median,
               high_severity_tickets,
               CASE
                   WHEN earn_events_per_booking = 0 THEN 'Aucune activité loyalty'
                   WHEN earn_events_per_booking < cohort_median_engagement*0.5
                       THEN 'Engagement très faible (<50% médiane pairs)'
                   ELSE 'Engagement sous la médiane du peer group'
               END AS signal
        FROM main_analytics.ontology_highvalue_atrisk_customer
        WHERE {' AND '.join(where)}
        ORDER BY lifetime_revenue_usd DESC
        LIMIT {limit}
    """)

    if df.empty:
        return "Aucun customer at-risk identifié."

    ltv_total = df["ltv_usd"].sum()
    header = (
        f"=== {len(df)} customers High-Value At-Risk ===\n"
        f"LTV totale à protéger : ${ltv_total:,.0f}\n"
        f"ROI si 30% convertis  : ${ltv_total*0.3:,.0f}\n"
        f"Action : voucher €50 ou offre status-match ciblée\n\n"
    )
    return header + to_text(df)


@mcp.tool()
def search_reviews_by_route(
    route_id: Optional[str] = None,
    sentiment: Optional[str] = None,
    topic: Optional[str] = None,
    text_search: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Recherche dans les reviews clients (source non-structurée).
    Combine filtres topic contrôlé + recherche plein-texte.

    Args:
        route_id:    Ex "R009" (Paris), "R005" (Dakar). None = tout le réseau.
        sentiment:   "positive" (rating>=4), "negative" (rating<=2), "neutral".
        topic:       punctuality | cabin_comfort | food_beverage | staff_service
                     | cleanliness | baggage | value_for_money | boarding
                     | entertainment | communication
        text_search: Mot-clé libre dans le texte des reviews (insensible casse).
        limit:       Nombre de reviews retournées (max 50).
    """
    TOPIC_COLS = {
        "punctuality":"has_punctuality","cabin_comfort":"has_cabin_comfort",
        "food_beverage":"has_food_beverage","staff_service":"has_staff_service",
        "cleanliness":"has_cleanliness","baggage":"has_baggage",
        "value_for_money":"has_value_for_money","boarding":"has_boarding",
        "entertainment":"has_entertainment","communication":"has_communication",
    }
    where = ["1=1"]
    if route_id:           where.append(f"r.route_id = '{route_id.upper()}'")
    if sentiment == "positive": where.append("r.rating >= 4")
    elif sentiment == "negative": where.append("r.rating <= 2")
    elif sentiment == "neutral": where.append("r.rating = 3")
    if topic:
        col = TOPIC_COLS.get(topic.lower())
        where.append(f"r.{col} = TRUE" if col else f"r.topics ILIKE '%{topic}%'")
    if text_search:        where.append(f"r.review_text ILIKE '%{text_search}%'")

    w   = " AND ".join(where)
    lim = min(int(limit), 50)

    stats = q(f"""
        SELECT COALESCE(d.route_label, r.route_id) AS route,
               COUNT(*) AS total,
               ROUND(AVG(r.rating),2) AS avg_rating,
               ROUND(SUM(CASE WHEN r.is_promoter  THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS pct_promo,
               ROUND(SUM(CASE WHEN r.is_detractor THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS pct_detrac,
               SUM(CASE WHEN r.has_punctuality  AND r.is_detractor THEN 1 ELSE 0 END) AS neg_punct,
               SUM(CASE WHEN r.has_baggage      AND r.is_detractor THEN 1 ELSE 0 END) AS neg_bag,
               SUM(CASE WHEN r.has_staff_service AND r.is_detractor THEN 1 ELSE 0 END) AS neg_staff,
               SUM(CASE WHEN r.has_communication AND r.is_detractor THEN 1 ELSE 0 END) AS neg_comm
        FROM main_marts.fct_reviews_sentiment r
        LEFT JOIN main_marts.dim_route d ON r.route_id = d.route_id
        WHERE {w}
        GROUP BY d.route_label, r.route_id
    """)

    reviews = q(f"""
        SELECT COALESCE(d.route_label, r.route_id) AS route,
               r.review_date, r.rating, r.sentiment_bucket,
               r.flight_status, r.topics, r.review_text
        FROM main_marts.fct_reviews_sentiment r
        LEFT JOIN main_marts.dim_route d ON r.route_id = d.route_id
        WHERE {w}
        ORDER BY r.rating ASC, r.review_date DESC
        LIMIT {lim}
    """)

    if reviews.empty:
        return "Aucune review trouvée."

    lines = []
    if not stats.empty:
        s = stats.iloc[0]
        nps = s["pct_promo"] - s["pct_detrac"]
        neg = sorted({
            "Ponctualité": int(s["neg_punct"]), "Bagages": int(s["neg_bag"]),
            "Staff": int(s["neg_staff"]), "Communication": int(s["neg_comm"]),
        }.items(), key=lambda x: -x[1])
        lines += [
            f"=== Reviews {route_id.upper() if route_id else '(réseau)'} ===",
            f"{int(s['total'])} reviews | {s['avg_rating']:.2f}★ | NPS proxy {nps:+.0f} "
            f"(Promoteurs {s['pct_promo']:.0f}% / Détracteurs {s['pct_detrac']:.0f}%)",
            "Top thèmes négatifs : " + " | ".join(f"{k} ({v})" for k, v in neg[:3] if v > 0),
            "",
        ]

    for _, row in reviews.iterrows():
        delayed = " ⚠️ Vol Delayed" if row["flight_status"] == "Delayed" else ""
        stars   = "★" * int(row["rating"]) + "☆" * (5 - int(row["rating"]))
        lines += [
            f"[{stars}] {row['route']} | {str(row['review_date'])[:10]} | "
            f"{row['sentiment_bucket']}{delayed}",
            f"Topics : {row['topics']}",
            f"\"{row['review_text']}\"",
            "",
        ]
    return "\n".join(lines)


@mcp.tool()
def recommend_budget_allocation(include_evidence: bool = True) -> str:
    """
    Recommandation d'allocation budgétaire 12 mois basée sur les 3 ontology
    rules + P&L réseau. Inclut ROI estimé et actions concrètes.

    Args:
        include_evidence: Si True, ajoute les données brutes justificatives.
    """
    pnl    = q("SELECT SUM(total_revenue_usd) AS rev, SUM(margin_usd) AS margin, SUM(flights_count) AS vols FROM main_analytics.route_pnl_monthly")
    undr   = q("SELECT route_label, ROUND(margin_pct*100,1) AS margin_pct, ROUND(load_factor*100,1) AS lf_pct, ROUND(ask_share*100,1) AS ask_share_pct FROM main_analytics.ontology_strategic_underperforming_route ORDER BY margin_pct ASC")
    atrisk = q("SELECT COUNT(*) AS n, ROUND(SUM(lifetime_revenue_usd)) AS ltv FROM main_analytics.ontology_highvalue_atrisk_customer")
    upsell = q("SELECT COUNT(*) AS n, ROUND(SUM(lifetime_revenue_usd)) AS ltv FROM main_analytics.ontology_upsell_ready_segment")
    anc    = q("SELECT ROUND(AVG(ancillary_revenue_usd),2) AS arpu, ROUND(SUM(CASE WHEN bought_lounge THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS attach_lounge FROM main_marts.fct_bookings WHERE booking_status IN ('Flown','Confirmed')")

    ar  = atrisk.iloc[0]
    up  = upsell.iloc[0]
    anc = anc.iloc[0]
    n_risk   = int(ar["n"]);   ltv_risk  = float(ar["ltv"]  or 0)
    n_up     = int(up["n"]);   ltv_up    = float(up["ltv"]  or 0)
    lounge   = float(anc["attach_lounge"] or 0)

    lines = [
        "═"*60,
        "RECOMMANDATION BUDGET 12 MOIS — Air Côte d'Ivoire",
        "═"*60,
        f"Données : {int(pnl.iloc[0]['vols'])} vols | {n_risk} customers at-risk | {n_up} upsell-ready",
        "",
        "┌─ PRIORITÉ 1 — Upsell / Cross-sell (40% budget)",
        "│  Payback : 0–3 mois | Risque : très faible",
        f"│  Signal : lounge attach {lounge:.1f}% — fortement sous-utilisé",
        f"│  Cible : {n_up} customers Economy sous-attachés | LTV ${ltv_up:,.0f}",
        "│  Action : bundle Lounge+Meal sur Flex, routes régionales",
        "│  KPI : ARPU ancillaire > $25 | Attach lounge > 15%",
        "",
        "├─ PRIORITÉ 2 — Rétention client (30% budget)",
        "│  Payback : 3–6 mois | Risque : faible",
        f"│  Signal : {n_risk} customers Silver/Gold sous-engagés",
        f"│  LTV à protéger : ${ltv_risk:,.0f} | ROI si 30% convertis : ${ltv_risk*0.3:,.0f}",
        "│  Action : voucher €50 ou status-match ciblé",
        "│  KPI : réengagement 30%+ de la cohorte",
        "",
    ]

    if not undr.empty:
        paris = undr[undr["route_label"].str.contains("CDG", na=False)]
        if not paris.empty:
            pr = paris.iloc[0]
            lines += [
                "├─ PRIORITÉ 3 — Demand generation Paris (20% budget)",
                "│  Payback : 6–12 mois | Risque : moyen",
                f"│  Signal : Paris {pr['margin_pct']:+.1f}% marge, LF {pr['lf_pct']:.1f}%",
                f"│  A330-900neo représente {pr['ask_share_pct']:.1f}% des ASK réseau",
                "│  Action : OTA, partenariats trade France, marketing diaspora CI",
                "│  KPI : Load factor Paris ≥ 50%",
                "",
            ]

    lines += [
        "└─ HOLD — Nouvelles routes",
        "   Condition de réévaluation : Paris LF ≥ 65% sur 3 mois",
        "═"*60,
    ]

    if include_evidence and not undr.empty:
        lines += ["", "EVIDENCE — Routes sous-performantes :", to_text(undr)]

    return "\n".join(lines)


@mcp.tool()
def explain_route_pnl(route_id: str) -> str:
    """
    Rapport narratif complet d'une route : P&L, fiabilité, satisfaction
    client et diagnostic. Exemple : route_id="R009" pour Paris CDG.
    """
    rid = route_id.upper()

    pnl = q(f"""
        SELECT route_label, route_type, distance_km,
               SUM(flights_count) AS vols, SUM(pax_count) AS pax,
               ROUND(SUM(total_revenue_usd))           AS rev,
               ROUND(SUM(total_operating_cost_usd))    AS cout,
               ROUND(SUM(margin_usd))                  AS marge,
               ROUND(SUM(margin_usd)*100.0/NULLIF(SUM(total_revenue_usd),0),1) AS margin_pct,
               ROUND(AVG(load_factor)*100,1)           AS lf_pct,
               ROUND(AVG(on_time_performance)*100,1)   AS otp_pct,
               ROUND(AVG(cancellation_rate)*100,1)     AS cancel_pct,
               ROUND(SUM(fuel_cost_usd))               AS fuel,
               ROUND(SUM(airport_fees_usd))            AS airport,
               ROUND(AVG(rask),4) AS rask, ROUND(AVG(cask),4) AS cask
        FROM main_analytics.route_pnl_monthly WHERE route_id = '{rid}'
        GROUP BY route_label, route_type, distance_km
    """)

    if pnl.empty:
        return f"Route {rid} introuvable. IDs valides : R001–R012."

    r = pnl.iloc[0]

    disr = q(f"""
        SELECT disruption_root_cause, COUNT(*) AS n
        FROM main_marts.fct_flights
        WHERE route_id = '{rid}' AND disruption_root_cause IS NOT NULL
        GROUP BY disruption_root_cause ORDER BY n DESC LIMIT 3
    """)

    sat = q(f"""
        SELECT COUNT(*) AS total, ROUND(AVG(rating),2) AS avg_rating,
               ROUND(SUM(CASE WHEN is_promoter  THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS promo,
               ROUND(SUM(CASE WHEN is_detractor THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS detrac,
               SUM(CASE WHEN has_punctuality  AND is_detractor THEN 1 ELSE 0 END) AS np,
               SUM(CASE WHEN has_staff_service AND is_detractor THEN 1 ELSE 0 END) AS ns,
               SUM(CASE WHEN has_communication AND is_detractor THEN 1 ELSE 0 END) AS nc
        FROM main_marts.fct_reviews_sentiment WHERE route_id = '{rid}'
    """)

    lines = [
        "═"*55,
        f"ROUTE {rid} — {r['route_label']} ({r['route_type']})",
        f"Distance : {r['distance_km']} km",
        "═"*55,
        "── P&L ──────────────────────────────────────────",
        f"  Revenue   : ${r['rev']:>12,.0f}",
        f"  Coût      : ${r['cout']:>12,.0f}",
        f"  Marge     : ${r['marge']:>12,.0f}  ({r['margin_pct']:+.1f}%)",
        f"  Fuel: ${r['fuel']:,.0f}  | Aéroport: ${r['airport']:,.0f}",
        "── Capacité ──────────────────────────────────────",
        f"  Vols : {int(r['vols'])}  | Pax : {int(r['pax']):,}  | Load Factor : {r['lf_pct']:.1f}%",
        f"  RASK : {r['rask']:.4f}  | CASK : {r['cask']:.4f}  | Spread : {r['rask']-r['cask']:+.4f}",
        "── Fiabilité ─────────────────────────────────────",
        f"  OTP : {r['otp_pct']:.1f}%  | Annulations : {r['cancel_pct']:.1f}%",
    ]

    if not disr.empty:
        causes = " | ".join(f"{row['disruption_root_cause']} ({int(row['n'])})"
                            for _, row in disr.iterrows())
        lines.append(f"  Disruptions : {causes}")

    if not sat.empty and sat.iloc[0]["total"] > 0:
        s   = sat.iloc[0]
        nps = s["promo"] - s["detrac"]
        neg = sorted({"Ponctualité": int(s["np"]), "Staff": int(s["ns"]),
                       "Communication": int(s["nc"])}.items(), key=lambda x: -x[1])
        lines += [
            "── Satisfaction ──────────────────────────────────",
            f"  {int(s['total'])} reviews | {s['avg_rating']:.2f}★ | NPS {nps:+.0f} "
            f"({s['promo']:.0f}% Promo / {s['detrac']:.0f}% Détrac)",
            "  Top thèmes négatifs : " + " | ".join(f"{k}({v})" for k, v in neg if v > 0),
        ]

    mp  = float(r["margin_pct"])
    lf  = float(r["lf_pct"])
    spr = float(r["rask"]) - float(r["cask"])
    lines.append("── Diagnostic ────────────────────────────────────")
    if mp >= 15:
        lines.append(f"  ✅ Route saine ({mp:+.1f}%). Envisager fréquence accrue.")
    elif mp >= 0:
        lines.append(f"  ⚠️  Rentable mais marges étroites ({mp:+.1f}%).")
        if lf < 60:
            lines.append(f"     Load factor {lf:.1f}% — remplir les sièges est la priorité.")
    else:
        lines.append(f"  🔴 Route déficitaire ({mp:+.1f}%).")
        if lf < 30:
            lines.append(
                f"     Load factor très bas ({lf:.1f}%).\n"
                "     Ce n'est PAS structurel : demand generation avant tout."
            )
        if spr < 0:
            lines.append(f"     Spread RASK−CASK = {spr:+.4f} : coûts > revenus unitaires.")

    lines.append("═"*55)
    return "\n".join(lines)


# ─── Entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    transport = "stdio"
    if "--transport" in sys.argv:
        i = sys.argv.index("--transport")
        transport = sys.argv[i + 1] if i + 1 < len(sys.argv) else "stdio"

    print(f"🚀 Air CI MCP Server | transport={transport}", file=sys.stderr)
    print(f"📁 DuckDB : {get_db_path()}", file=sys.stderr)
    print(f"📊 Schémas : {schema_map()}", file=sys.stderr)

    mcp.run(transport="streamable-http" if transport == "http" else "stdio")