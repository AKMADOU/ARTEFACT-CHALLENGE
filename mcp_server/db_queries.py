#!/usr/bin/env python3
"""
db_queries.py — Database query functions for MCP Server
Abstraction layer over DuckDB, reuses logic from dashboard/db.py
"""

import os
import duckdb
import pandas as pd
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────
# Database Connection & Schema Detection
# ─────────────────────────────────────────────────────────────────────

def get_db_path() -> str:
    """Find the DuckDB database file."""
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


def get_schema_map() -> dict:
    """Detect actual dbt schema names in DuckDB."""
    db_path = get_db_path()
    con = duckdb.connect(db_path, read_only=True)
    try:
        df = con.execute(
            "SELECT table_schema, table_name FROM information_schema.tables"
        ).fetchdf()
    finally:
        con.close()

    layer_markers = {
        "analytics":    ["route_pnl_monthly", "ontology_highvalue_atrisk_customer"],
        "marts":        ["fct_flights", "fct_bookings", "fct_reviews_sentiment"],
        "intermediate": ["int_flight_economics"],
        "staging":      ["stg_airports"],
        "raw":          ["disruption_log", "customer_reviews"],
    }

    schema_map = {}
    for layer, markers in layer_markers.items():
        for marker in markers:
            match = df[df["table_name"] == marker]
            if not match.empty:
                schema_map[layer] = match.iloc[0]["table_schema"]
                break

    defaults = {
        "analytics": "main_analytics", "marts": "main_marts",
        "intermediate": "main_intermediate", "staging": "main_staging",
        "raw": "main",
    }
    for layer, default in defaults.items():
        schema_map.setdefault(layer, default)

    return schema_map


def _resolve_sql(sql: str) -> str:
    """Replace hardcoded schema prefixes with actual names."""
    sm = get_schema_map()
    replacements = {
        "main_analytics.":   sm["analytics"] + ".",
        "main_marts.":       sm["marts"] + ".",
        "main_intermediate.": sm["intermediate"] + ".",
        "main_staging.":     sm["staging"] + ".",
    }
    
    for old, new in replacements.items():
        sql = sql.replace(old, new)
    
    raw_prefix = sm["raw"] + "."
    if raw_prefix != "main.":
        raw_tables = [
            "disruption_log", "customer_reviews", "loyalty_transactions",
            "support_tickets", "aircraft_fleet", "fuel_prices_monthly",
        ]
        for tbl in raw_tables:
            sql = sql.replace(f"main.{tbl}", f"{sm['raw']}.{tbl}")
    
    return sql


def query(sql: str) -> pd.DataFrame:
    """Execute SQL query against DuckDB."""
    resolved = _resolve_sql(sql)
    db_path = get_db_path()
    con = duckdb.connect(db_path, read_only=True)
    try:
        return con.execute(resolved).fetchdf()
    except duckdb.CatalogException as e:
        try:
            tables = con.execute(
                "SELECT table_schema || '.' || table_name AS full_name "
                "FROM information_schema.tables ORDER BY 1"
            ).fetchdf()
            raise RuntimeError(
                f"Catalog error: {e}\nSQL: {resolved}\n"
                f"Available tables:\n{tables['full_name'].tolist()}"
            )
        except:
            raise e
    finally:
        con.close()


# ─────────────────────────────────────────────────────────────────────
# TOOL 1: Route Metrics (query_route_metrics)
# ─────────────────────────────────────────────────────────────────────

def get_route_metrics(
    route_id: str = None,
    route_type: str = None,
    max_margin_pct: float = None,
    sort_by: str = "margin_pct",
) -> pd.DataFrame:
    """
    Get route performance metrics (P&L, load factor, OTP, RASK, CASK).
    
    Args:
        route_id: Filter by single route (e.g. "R009")
        route_type: Filter by type ("Domestic", "Regional", "International")
        max_margin_pct: Only routes with margin_pct <= this value (for unprofitable)
        sort_by: Column to sort by ("margin_pct", "revenue_usd", etc.)
    
    Returns:
        DataFrame with route metrics
    """
    where_clauses = []
    
    if route_id:
        where_clauses.append(f"route_id = '{route_id.strip()}'")
    if route_type:
        where_clauses.append(f"route_type = '{route_type.strip()}'")
    if max_margin_pct is not None:
        where_clauses.append(f"(margin_pct * 100) <= {max_margin_pct}")
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    sql = f"""
        SELECT route_id, route_label, route_type, origin_city, destination_city,
               flights_count, cancelled_count, delayed_count, pax_count,
               ROUND(load_factor * 100, 1)          AS load_factor_pct,
               ROUND(on_time_performance * 100, 1)  AS otp_pct,
               ROUND(cancellation_rate * 100, 1)    AS cancel_pct,
               ROUND(total_revenue_usd)              AS revenue_usd,
               ROUND(total_operating_cost_usd)       AS cost_usd,
               ROUND(margin_usd)                     AS margin_usd,
               ROUND((margin_usd * 100.0) / NULLIF(total_revenue_usd, 0), 1) AS margin_pct,
               ROUND(rask, 4)                        AS rask,
               ROUND(cask, 4)                        AS cask,
               flights AS flights,
               pax AS pax
        FROM main_analytics.route_pnl_monthly
        {where_sql}
        ORDER BY {sort_by} DESC
    """
    
    return query(sql)


# ─────────────────────────────────────────────────────────────────────
# TOOL 2: At-Risk Customers (get_at_risk_customers)
# ─────────────────────────────────────────────────────────────────────

def get_at_risk_customers(
    min_ltv_usd: float = None,
    loyalty_tier: str = None,
) -> pd.DataFrame:
    """
    Get high-value customers identified as at-risk by ontology rule.
    
    Args:
        min_ltv_usd: Only customers with LTV >= this value
        loyalty_tier: Filter by tier ("Silver", "Gold")
    
    Returns:
        DataFrame with at-risk customer details
    """
    where_clauses = []
    
    if min_ltv_usd and min_ltv_usd > 0:
        where_clauses.append(f"lifetime_revenue_usd >= {min_ltv_usd}")
    if loyalty_tier:
        where_clauses.append(f"loyalty_tier = '{loyalty_tier.strip()}'")
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    sql = f"""
        SELECT customer_id, customer_segment, loyalty_tier,
               total_bookings,
               ROUND(lifetime_revenue_usd)             AS ltv_usd,
               earn_event_count,
               ROUND(earn_events_per_booking, 2)       AS engagement_ratio,
               ROUND(cohort_median_engagement, 2)      AS cohort_median,
               high_severity_tickets,
               cond_tier_silver_gold,
               cond_submedian_engagement,
               cond_high_ltv_p60
        FROM main_analytics.ontology_highvalue_atrisk_customer
        {where_sql}
        ORDER BY lifetime_revenue_usd DESC
    """
    
    return query(sql)


# ─────────────────────────────────────────────────────────────────────
# TOOL 3: Reviews for RAG Indexing
# ─────────────────────────────────────────────────────────────────────

def get_reviews_for_indexing() -> pd.DataFrame:
    """
    Get all reviews for TF-IDF RAG indexing.
    Includes text, metadata, and structured fields.
    """
    sql = """
        SELECT r.review_id, r.route_id, d.route_label, d.route_type,
               r.review_date, r.rating,
               CASE WHEN r.is_promoter  THEN 'Promoter'
                    WHEN r.is_detractor THEN 'Detractor'
                    ELSE 'Passive' END AS sentiment_bucket,
               r.review_text,
               CONCAT(
                   CASE WHEN r.has_punctuality THEN 'punctuality ' ELSE '' END,
                   CASE WHEN r.has_cabin_comfort THEN 'comfort ' ELSE '' END,
                   CASE WHEN r.has_food_beverage THEN 'food ' ELSE '' END,
                   CASE WHEN r.has_staff_service THEN 'service ' ELSE '' END,
                   CASE WHEN r.has_baggage THEN 'baggage ' ELSE '' END,
                   CASE WHEN r.has_communication THEN 'communication ' ELSE '' END,
                   CASE WHEN r.has_value_for_money THEN 'value ' ELSE '' END,
                   CASE WHEN r.has_cleanliness THEN 'cleanliness ' ELSE '' END,
                   CASE WHEN r.has_boarding THEN 'boarding ' ELSE '' END
               ) AS topics
        FROM main_marts.fct_reviews_sentiment r
        LEFT JOIN main_marts.dim_route d ON r.route_id = d.route_id
        WHERE r.review_text IS NOT NULL AND r.review_text != ''
        ORDER BY r.review_date DESC
    """
    
    return query(sql)


# ─────────────────────────────────────────────────────────────────────
# Reviews Query with SQL Filtering
# ─────────────────────────────────────────────────────────────────────

def get_reviews_by_route_sql(
    route_id: str = None,
    sentiment: str = None,
    topic: str = None,
    limit: int = 10,
) -> pd.DataFrame:
    """
    SQL-based review filtering (fallback if RAG not available).
    
    Args:
        route_id: Filter by route
        sentiment: "Promoter", "Passive", "Detractor"
        topic: "punctuality", "baggage", etc.
        limit: Results limit
    """
    where_clauses = []
    
    if route_id:
        where_clauses.append(f"r.route_id = '{route_id.strip()}'")
    
    if sentiment and sentiment in ["Promoter", "Passive", "Detractor"]:
        if sentiment == "Promoter":
            where_clauses.append("r.is_promoter = true")
        elif sentiment == "Detractor":
            where_clauses.append("r.is_detractor = true")
        else:
            where_clauses.append("r.is_promoter = false AND r.is_detractor = false")
    
    if topic:
        topic_col = {
            "punctuality": "r.has_punctuality",
            "comfort": "r.has_cabin_comfort",
            "food": "r.has_food_beverage",
            "service": "r.has_staff_service",
            "baggage": "r.has_baggage",
            "communication": "r.has_communication",
            "value": "r.has_value_for_money",
            "cleanliness": "r.has_cleanliness",
            "boarding": "r.has_boarding",
        }.get(topic.lower())
        if topic_col:
            where_clauses.append(f"{topic_col} = true")
    
    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    sql = f"""
        SELECT r.review_id, r.route_id, COALESCE(d.route_label, r.route_id) AS route_label,
               r.review_date, r.rating,
               CASE WHEN r.is_promoter  THEN 'Promoter'
                    WHEN r.is_detractor THEN 'Detractor'
                    ELSE 'Passive' END AS sentiment_bucket,
               r.review_text,
               CONCAT(
                   CASE WHEN r.has_punctuality THEN 'punctuality ' ELSE '' END,
                   CASE WHEN r.has_cabin_comfort THEN 'comfort ' ELSE '' END,
                   CASE WHEN r.has_food_beverage THEN 'food ' ELSE '' END,
                   CASE WHEN r.has_staff_service THEN 'service ' ELSE '' END,
                   CASE WHEN r.has_baggage THEN 'baggage ' ELSE '' END,
                   CASE WHEN r.has_communication THEN 'communication ' ELSE '' END
               ) AS topics
        FROM main_marts.fct_reviews_sentiment r
        LEFT JOIN main_marts.dim_route d ON r.route_id = d.route_id
        {where_sql}
        ORDER BY r.review_date DESC
        LIMIT {limit}
    """
    
    return query(sql)


# ─────────────────────────────────────────────────────────────────────
# Budget Allocation Signals
# ─────────────────────────────────────────────────────────────────────

def get_allocation_signals() -> dict:
    """
    Get all signals for budget allocation recommendation.
    Returns dict with routes, at_risk, upsell, attach, NPS, strategic routes.
    """
    
    # Overall routes
    routes = query("""
        SELECT route_id, route_label, route_type,
               ROUND((margin_usd * 100.0) / NULLIF(total_revenue_usd, 0), 1) AS margin_pct,
               ROUND(total_revenue_usd) AS revenue_usd,
               ROUND(margin_usd) AS margin_usd
        FROM main_analytics.route_pnl_monthly
    """)
    
    # At-risk customers
    at_risk = query("""
        SELECT customer_id, loyalty_tier, lifetime_revenue_usd AS ltv_usd
        FROM main_analytics.ontology_highvalue_atrisk_customer
    """)
    
    # Upsell-ready
    upsell = query("""
        SELECT COUNT(*) AS n,
               ROUND(SUM(lifetime_revenue_usd)) AS total_ltv_usd
        FROM main_analytics.ontology_upsell_ready_segment
    """)
    
    # Ancillary attachment
    attach = query("""
        SELECT 
            ROUND(SUM(CASE WHEN has_any_ancillary THEN 1 ELSE 0 END)*100.0/COUNT(*), 1) AS attach_rate_pct,
            ROUND(AVG(ancillary_revenue_usd), 2) AS arpu_ancillary
        FROM main_marts.fct_bookings
        WHERE booking_status IN ('Flown', 'Confirmed')
    """)
    
    # NPS proxy
    nps = query("""
        SELECT ROUND(
            SUM(CASE WHEN is_promoter  THEN 1 ELSE 0 END)*100.0/COUNT(*)
          - SUM(CASE WHEN is_detractor THEN 1 ELSE 0 END)*100.0/COUNT(*), 1
        ) AS nps_proxy
        FROM main_marts.fct_reviews_sentiment
    """)
    
    # Strategic underperforming routes
    strategic = query("""
        SELECT route_id, route_label,
               ROUND((margin_pct * 100), 1) AS margin_pct,
               ROUND(load_factor * 100, 1) AS load_factor_pct
        FROM main_analytics.ontology_strategic_underperforming_route
    """)
    
    return {
        "routes": routes,
        "at_risk": at_risk,
        "upsell": upsell,
        "attach": attach,
        "nps": nps,
        "strategic_routes": strategic,
    }


# ─────────────────────────────────────────────────────────────────────
# Route P&L Explanation
# ─────────────────────────────────────────────────────────────────────

def explain_route(route_id: str) -> dict:
    """
    Get complete analysis for a single route.
    Includes P&L, disruptions, positive/negative reviews.
    """
    route_id = route_id.strip()
    
    # Metrics
    metrics = query(f"""
        SELECT route_id, route_label, route_type, origin_city, destination_city,
               ROUND(total_revenue_usd) AS revenue_usd,
               ROUND(total_operating_cost_usd) AS cost_usd,
               ROUND(margin_usd) AS margin_usd,
               ROUND((margin_usd * 100.0) / NULLIF(total_revenue_usd, 0), 1) AS margin_pct,
               ROUND(load_factor * 100, 1) AS load_factor_pct,
               ROUND(on_time_performance * 100, 1) AS otp_pct,
               ROUND(rask, 4) AS rask,
               ROUND(cask, 4) AS cask,
               flights_count AS flights,
               pax_count AS pax
        FROM main_analytics.route_pnl_monthly
        WHERE route_id = '{route_id}'
    """)
    
    # Disruption breakdown
    disruption = query(f"""
        SELECT disruption_root_cause AS cause,
               COUNT(*) AS n_disruptions,
               ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER (), 1) AS share_pct
        FROM main_marts.fct_flights
        WHERE route_id = '{route_id}' AND disruption_root_cause IS NOT NULL
        GROUP BY disruption_root_cause
        ORDER BY n_disruptions DESC
    """)
    
    # Positive reviews
    pos_reviews = query(f"""
        SELECT review_text, rating
        FROM main_marts.fct_reviews_sentiment
        WHERE route_id = '{route_id}' AND is_promoter = true
        ORDER BY rating DESC
        LIMIT 10
    """)
    
    # Negative reviews
    neg_reviews = query(f"""
        SELECT review_text, rating
        FROM main_marts.fct_reviews_sentiment
        WHERE route_id = '{route_id}' AND is_detractor = true
        ORDER BY rating ASC
        LIMIT 10
    """)
    
    return {
        "metrics": metrics,
        "disruption": disruption,
        "sample_reviews": pos_reviews,
        "neg_reviews": neg_reviews,
    }
