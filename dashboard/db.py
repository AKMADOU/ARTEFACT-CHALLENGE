# dashboard/db.py — version robuste avec auto-détection des schémas
# Fonctionne quelle que soit la config dbt locale (main_analytics, airci, etc.)

import os
import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path


# ─────────────────────────────────────────────
# Connexion & détection automatique des schémas
# ─────────────────────────────────────────────

def get_db_path() -> str:
    env_path = os.environ.get("DBT_DUCKDB_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    candidates = [
        Path(__file__).parent.parent / "dbt_project" / "airci.duckdb",
        Path("dbt_project") / "airci.duckdb",
        Path("airci.duckdb"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return str(candidates[0])


@st.cache_resource
def get_schema_map() -> dict:
    """
    Détecte les vrais noms de schémas dbt dans DuckDB.
    Retourne ex: {'analytics': 'airci', 'marts': 'airci', 'raw': 'main'}
    """
    db_path = get_db_path()
    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(
            "SELECT table_schema, table_name FROM information_schema.tables"
        ).fetchdf()
    finally:
        con.close()

    # Tables caractéristiques de chaque couche
    layer_markers = {
        "analytics":    ["route_pnl_monthly", "ontology_highvalue_atrisk_customer",
                         "ontology_upsell_ready_segment",
                         "ontology_strategic_underperforming_route"],
        "marts":        ["fct_flights", "fct_bookings", "fct_reviews_sentiment",
                         "dim_route", "dim_customer"],
        "intermediate": ["int_flight_economics", "int_customer_engagement"],
        "staging":      ["stg_airports", "stg_flights", "stg_bookings"],
        "raw":          ["disruption_log", "customer_reviews", "loyalty_transactions"],
    }

    schema_map = {}
    for layer, markers in layer_markers.items():
        for marker in markers:
            match = df[df["table_name"] == marker]
            if not match.empty:
                schema_map[layer] = match.iloc[0]["table_schema"]
                break

    # Fallbacks si non trouvés
    defaults = {
        "analytics": "main_analytics", "marts": "main_marts",
        "intermediate": "main_intermediate", "staging": "main_staging",
        "raw": "main",
    }
    for layer, default in defaults.items():
        schema_map.setdefault(layer, default)

    return schema_map


def _resolve_sql(sql: str) -> str:
    """Remplace les prefixes de schémas hardcodés par les vrais noms."""
    sm = get_schema_map()
    replacements = {
        "main_analytics.":   sm["analytics"] + ".",
        "main_marts.":       sm["marts"] + ".",
        "main_intermediate.": sm["intermediate"] + ".",
        "main_staging.":     sm["staging"] + ".",
    }
    # Gestion du schéma 'raw' (tables seeds comme disruption_log)
    # Ces tables sont dans le schéma 'raw' ou directement dans 'main'
    raw_prefix = sm["raw"] + "."

    for old, new in replacements.items():
        sql = sql.replace(old, new)

    # Remplacer "main.table" pour les seeds uniquement si le schéma raw ≠ main
    if raw_prefix != "main.":
        # Tables seeds connues dans le schéma raw
        raw_tables = [
            "disruption_log", "customer_reviews", "loyalty_transactions",
            "support_tickets", "aircraft_fleet", "fuel_prices_monthly",
        ]
        for tbl in raw_tables:
            sql = sql.replace(f"main.{tbl}", f"{sm['raw']}.{tbl}")

    return sql


def query(sql: str) -> pd.DataFrame:
    resolved = _resolve_sql(sql)
    db_path = get_db_path()
    con = duckdb.connect(db_path, read_only=True)
    try:
        return con.execute(resolved).fetchdf()
    except duckdb.CatalogException as e:
        # Debug : afficher les tables disponibles si erreur
        try:
            tables = con.execute(
                "SELECT table_schema || '.' || table_name AS full_name "
                "FROM information_schema.tables ORDER BY 1"
            ).fetchdf()
            raise RuntimeError(
                f"Catalog error: {e}\n\n"
                f"SQL essayé:\n{resolved}\n\n"
                f"Tables disponibles:\n{tables['full_name'].tolist()}"
            )
        except Exception:
            raise e
    finally:
        con.close()


# ─────────────────────────────────────────────
# Network & Profitability
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_route_pnl() -> pd.DataFrame:
    return query("""
        SELECT route_id, route_label, route_type, origin_city, destination_city,
               distance_km, year_month,
               flights_count, cancelled_count, delayed_count, on_time_count, pax_count,
               ROUND(load_factor * 100, 1)          AS load_factor_pct,
               ROUND(on_time_performance * 100, 1)  AS otp_pct,
               ROUND(cancellation_rate * 100, 1)    AS cancellation_pct,
               ROUND(total_revenue_usd)              AS revenue_usd,
               ROUND(total_operating_cost_usd)       AS cost_usd,
               ROUND(margin_usd)                     AS margin_usd,
               ROUND(margin_pct * 100, 1)            AS margin_pct,
               ROUND(rask, 4)                        AS rask,
               ROUND(cask, 4)                        AS cask,
               ROUND(yield_usd_per_rpk, 4)           AS yield_usd_per_rpk
        FROM main_analytics.route_pnl_monthly
        ORDER BY margin_pct DESC
    """)


@st.cache_data(ttl=300)
def load_route_summary() -> pd.DataFrame:
    return query("""
        SELECT route_id, route_label, route_type, origin_city, destination_city,
               SUM(flights_count)                                           AS flights,
               SUM(pax_count)                                               AS pax,
               ROUND(AVG(load_factor) * 100, 1)                             AS avg_load_factor_pct,
               ROUND(AVG(on_time_performance) * 100, 1)                     AS avg_otp_pct,
               ROUND(AVG(cancellation_rate) * 100, 1)                       AS avg_cancel_pct,
               ROUND(SUM(total_revenue_usd))                                AS total_revenue_usd,
               ROUND(SUM(total_operating_cost_usd))                         AS total_cost_usd,
               ROUND(SUM(margin_usd))                                       AS total_margin_usd,
               ROUND(SUM(margin_usd)*100.0/NULLIF(SUM(total_revenue_usd),0),1) AS margin_pct
        FROM main_analytics.route_pnl_monthly
        GROUP BY route_id, route_label, route_type, origin_city, destination_city
        ORDER BY margin_pct DESC
    """)


@st.cache_data(ttl=300)
def load_disruption_mix() -> pd.DataFrame:
    return query("""
        SELECT disruption_root_cause AS root_cause,
               COUNT(*) AS n_disruptions,
               ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER (), 1) AS share_pct
        FROM main_marts.fct_flights
        WHERE disruption_root_cause IS NOT NULL
        GROUP BY disruption_root_cause
        ORDER BY n_disruptions DESC
    """)


@st.cache_data(ttl=300)
def load_flight_stats() -> pd.DataFrame:
    return query("""
        SELECT flight_status, COUNT(*) AS n,
               ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER (), 1) AS share_pct
        FROM main_marts.fct_flights
        GROUP BY flight_status
    """)


# ─────────────────────────────────────────────
# Customer & Retention
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_customer_summary() -> pd.DataFrame:
    return query("""
        SELECT customer_segment, loyalty_tier,
               COUNT(*)                                AS n_customers,
               ROUND(AVG(lifetime_revenue_usd))        AS avg_ltv,
               ROUND(AVG(total_bookings), 1)            AS avg_bookings,
               ROUND(AVG(earn_events_per_booking), 2)  AS avg_engagement,
               SUM(CASE WHEN has_loyalty_activity THEN 1 ELSE 0 END) AS n_loyalty_active
        FROM main_marts.dim_customer
        GROUP BY customer_segment, loyalty_tier
        ORDER BY avg_ltv DESC
    """)


@st.cache_data(ttl=300)
def load_at_risk_customers() -> pd.DataFrame:
    return query("""
        SELECT customer_id, customer_segment, loyalty_tier,
               total_bookings,
               ROUND(lifetime_revenue_usd)             AS ltv_usd,
               earn_event_count,
               ROUND(earn_events_per_booking, 2)       AS engagement_ratio,
               ROUND(cohort_median_engagement, 2)      AS cohort_median,
               high_severity_tickets
        FROM main_analytics.ontology_highvalue_atrisk_customer
        ORDER BY ltv_usd DESC
    """)


@st.cache_data(ttl=300)
def load_review_trends() -> pd.DataFrame:
    return query("""
        SELECT r.route_id,
               COALESCE(d.route_label, r.route_id)    AS route_label,
               COALESCE(d.route_type, 'Unknown')       AS route_type,
               COUNT(*)                                AS reviews,
               ROUND(AVG(r.rating), 2)                 AS avg_rating,
               ROUND(SUM(CASE WHEN r.is_promoter  THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS pct_promoter,
               ROUND(SUM(CASE WHEN r.is_detractor THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS pct_detractor,
               ROUND(
                   SUM(CASE WHEN r.is_promoter  THEN 1 ELSE 0 END)*100.0/COUNT(*)
                 - SUM(CASE WHEN r.is_detractor THEN 1 ELSE 0 END)*100.0/COUNT(*), 1
               ) AS nps_proxy
        FROM main_marts.fct_reviews_sentiment r
        LEFT JOIN main_marts.dim_route d ON r.route_id = d.route_id
        GROUP BY r.route_id, d.route_label, d.route_type
        ORDER BY nps_proxy DESC
    """)


@st.cache_data(ttl=300)
def load_negative_topics() -> pd.DataFrame:
    return query("""
        SELECT
            SUM(CASE WHEN has_punctuality     AND is_detractor THEN 1 ELSE 0 END) AS punctuality,
            SUM(CASE WHEN has_cabin_comfort   AND is_detractor THEN 1 ELSE 0 END) AS cabin_comfort,
            SUM(CASE WHEN has_food_beverage   AND is_detractor THEN 1 ELSE 0 END) AS food_beverage,
            SUM(CASE WHEN has_staff_service   AND is_detractor THEN 1 ELSE 0 END) AS staff_service,
            SUM(CASE WHEN has_baggage         AND is_detractor THEN 1 ELSE 0 END) AS baggage,
            SUM(CASE WHEN has_communication   AND is_detractor THEN 1 ELSE 0 END) AS communication,
            SUM(CASE WHEN has_value_for_money AND is_detractor THEN 1 ELSE 0 END) AS value_for_money,
            SUM(CASE WHEN has_cleanliness     AND is_detractor THEN 1 ELSE 0 END) AS cleanliness,
            SUM(CASE WHEN has_boarding        AND is_detractor THEN 1 ELSE 0 END) AS boarding
        FROM main_marts.fct_reviews_sentiment
    """)


# ─────────────────────────────────────────────
# Upsell & Cross-sell
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_ancillary_attach() -> pd.DataFrame:
    return query("""
        SELECT fare_family,
               COUNT(*)                                                            AS bookings,
               ROUND(AVG(ticket_price_usd), 0)                                    AS avg_ticket_usd,
               ROUND(AVG(ancillary_revenue_usd), 2)                               AS arpu_ancillary,
               ROUND(SUM(CASE WHEN has_any_ancillary     THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS attach_rate_pct,
               ROUND(SUM(CASE WHEN bought_lounge         THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS attach_lounge_pct,
               ROUND(SUM(CASE WHEN bought_upgrade        THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS attach_upgrade_pct,
               ROUND(SUM(CASE WHEN bought_meal           THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS attach_meal_pct,
               ROUND(SUM(CASE WHEN bought_seat_selection THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS attach_seat_pct,
               ROUND(SUM(anc_lounge_usd))    AS total_lounge_usd,
               ROUND(SUM(anc_upgrade_usd))   AS total_upgrade_usd,
               ROUND(SUM(anc_meal_usd))      AS total_meal_usd,
               ROUND(SUM(anc_seat_usd))      AS total_seat_usd,
               ROUND(SUM(anc_baggage_usd))   AS total_baggage_usd
        FROM main_marts.fct_bookings
        WHERE booking_status IN ('Flown', 'Confirmed')
        GROUP BY fare_family
        ORDER BY arpu_ancillary DESC
    """)


@st.cache_data(ttl=300)
def load_ancillary_by_segment() -> pd.DataFrame:
    return query("""
        SELECT c.customer_segment,
               COUNT(b.booking_id)                    AS bookings,
               ROUND(AVG(b.ancillary_revenue_usd), 2) AS arpu_ancillary,
               ROUND(AVG(b.anc_lounge_usd), 2)        AS avg_lounge,
               ROUND(AVG(b.anc_upgrade_usd), 2)       AS avg_upgrade,
               ROUND(AVG(b.anc_meal_usd), 2)          AS avg_meal,
               ROUND(SUM(CASE WHEN b.bought_upgrade THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS upgrade_attach_pct
        FROM main_marts.fct_bookings b
        JOIN main_marts.dim_customer c ON b.customer_id = c.customer_id
        WHERE b.booking_status IN ('Flown', 'Confirmed')
        GROUP BY c.customer_segment
        ORDER BY arpu_ancillary DESC
    """)


@st.cache_data(ttl=300)
def load_upsell_ready() -> pd.DataFrame:
    return query("""
        SELECT customer_id, customer_segment, loyalty_tier,
               total_bookings,
               ROUND(lifetime_revenue_usd)                    AS ltv_usd,
               ROUND(personal_ancillary_attach_rate * 100, 1) AS attach_pct,
               ROUND(p25_attach_economy * 100, 1)             AS p25_threshold_pct
        FROM main_analytics.ontology_upsell_ready_segment
        ORDER BY ltv_usd DESC
        LIMIT 20
    """)


@st.cache_data(ttl=300)
def load_channel_mix() -> pd.DataFrame:
    return query("""
        SELECT booking_channel,
               COUNT(*)                               AS bookings,
               ROUND(AVG(ticket_price_usd), 0)        AS avg_ticket_usd,
               ROUND(AVG(ancillary_revenue_usd), 2)   AS arpu_ancillary,
               ROUND(SUM(ticket_price_usd + ancillary_revenue_usd)) AS total_revenue_usd
        FROM main_marts.fct_bookings
        WHERE booking_status IN ('Flown', 'Confirmed')
        GROUP BY booking_channel
        ORDER BY total_revenue_usd DESC
    """)


# ─────────────────────────────────────────────
# Decision Layer
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_strategic_underperforming() -> pd.DataFrame:
    return query("""
        SELECT route_id, route_label, route_type, origin_city, destination_city,
               flights_count, total_pax,
               ROUND(route_revenue_usd)    AS revenue_usd,
               ROUND(route_margin_usd)     AS margin_usd,
               ROUND(margin_pct * 100, 1)  AS margin_pct,
               ROUND(ask_share * 100, 1)   AS ask_share_pct,
               ROUND(load_factor * 100, 1) AS load_factor_pct
        FROM main_analytics.ontology_strategic_underperforming_route
        ORDER BY margin_usd ASC
    """)


@st.cache_data(ttl=300)
def load_global_kpis() -> dict:
    df = query("""
        SELECT
            SUM(total_revenue_usd)              AS total_revenue,
            SUM(total_operating_cost_usd)       AS total_cost,
            SUM(margin_usd)                     AS total_margin,
            ROUND(AVG(load_factor) * 100, 1)    AS avg_load_factor,
            ROUND(AVG(on_time_performance)*100, 1) AS avg_otp,
            SUM(flights_count)                  AS total_flights,
            SUM(pax_count)                      AS total_pax
        FROM main_analytics.route_pnl_monthly
    """)
    row = df.iloc[0]
    return {
        "total_revenue":  int(row["total_revenue"]),
        "total_cost":     int(row["total_cost"]),
        "total_margin":   int(row["total_margin"]),
        "margin_pct":     round(row["total_margin"] / row["total_revenue"] * 100, 1)
                          if row["total_revenue"] else 0,
        "avg_load_factor": row["avg_load_factor"],
        "avg_otp":         row["avg_otp"],
        "total_flights":   int(row["total_flights"]),
        "total_pax":       int(row["total_pax"]),
    }


# ─────────────────────────────────────────────
# Utilitaire debug (appelé si le dashboard ne charge pas)
# ─────────────────────────────────────────────

def show_available_tables() -> pd.DataFrame:
    """Affiche toutes les tables disponibles — utile pour diagnostiquer."""
    return query("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        ORDER BY table_schema, table_name
    """)