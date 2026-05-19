# Air Côte d'Ivoire — Executive Growth Allocation Dashboard
# Run : streamlit run app.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import db
from config import COLORS, ROUTE_COLORS, SENTIMENT_COLORS, KPI_LABELS

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Air CI — Growth Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS minimal pour un look propre
st.markdown("""
<style>
    .metric-card {
        background: #F0F4FF;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #1F4E79;
    }
    .stMetric label { font-size: 13px !important; color: #6B7280 !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; }
    .section-title { color: #1F4E79; font-weight: 700; font-size: 16px; margin-top: 8px; }
    .recommendation-box {
        background: #EEF7EE;
        border-left: 4px solid #16A34A;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
    }
    .warning-box {
        background: #FFF7ED;
        border-left: 4px solid #D97706;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
    }
    .danger-box {
        background: #FEF2F2;
        border-left: 4px solid #DC2626;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(
    """<div style="font-size:28px; font-weight:800; color:#1F4E79;
                  letter-spacing:1px; padding:4px 0;">
    ✈️ Air CI
    </div>""",
    unsafe_allow_html=True
)
    st.markdown("### Growth Allocation Dashboard")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["🗺️ Network & Profitability",
         "👥 Customer & Retention",
         "💰 Upsell & Cross-sell",
         "🎯 Decision Layer"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Dashboard construit dans le cadre du challenge Analytics Engineer — Artefact")
    # st.caption("Artefact Analytics Engineer Challenge")
    st.markdown("---")
    st.caption("Candidat : ADOU Kouamé Mathurin")
    st.caption("07 47 10 92 96")



# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def fmt_usd(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def delta_color(v: float) -> str:
    return "normal" if v >= 0 else "inverse"


def bar_color(v: float) -> str:
    return COLORS["positive"] if v >= 0 else COLORS["negative"]


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — NETWORK & PROFITABILITY
# ═══════════════════════════════════════════════════════════════════

if page == "🗺️ Network & Profitability":
    st.title("🗺️ Network & Profitability")
    st.caption("Route P&L · Fiabilité opérationnelle · Opportunity matrix")

    # KPIs globaux
    kpis = db.load_global_kpis()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue total",  fmt_usd(kpis["total_revenue"]))
    c2.metric("Marge totale",   fmt_usd(kpis["total_margin"]),
              f"{kpis['margin_pct']:+.1f}%", delta_color=delta_color(kpis["total_margin"]))
    c3.metric("Load Factor moy.", f"{kpis['avg_load_factor']}%")
    c4.metric("OTP moy.",          f"{kpis['avg_otp']}%")
    c5.metric("Vols opérés",       f"{kpis['total_flights']:,}")

    st.markdown("---")

    route_df = db.load_route_summary()
    pnl_df   = db.load_route_pnl()

    # ── Graphe 1 : Marge % par route (bar)
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown('<p class="section-title">Marge % par route</p>', unsafe_allow_html=True)
        fig = px.bar(
            route_df.sort_values("margin_pct"),
            x="margin_pct", y="route_label",
            color="margin_pct",
            color_continuous_scale=["#DC2626", "#FCA5A5", "#D1FAE5", "#16A34A"],
            color_continuous_midpoint=0,
            orientation="h",
            text="margin_pct",
            labels={"margin_pct": "Marge %", "route_label": "Route"},
            custom_data=["route_type", "total_revenue_usd", "total_margin_usd"],
        )
        fig.update_traces(
            texttemplate="%{x:.1f}%",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Type: %{customdata[0]}<br>"
                          "Revenue: $%{customdata[1]:,.0f}<br>"
                          "Marge: $%{customdata[2]:,.0f}<extra></extra>",
        )
        fig.update_layout(
            height=360, showlegend=False,
            coloraxis_showscale=False,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(zeroline=True, zerolinecolor="#999"),
            margin=dict(l=0, r=60, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown('<p class="section-title">Mix de fiabilité (réseau)</p>', unsafe_allow_html=True)
        flight_df = db.load_flight_stats()
        fig2 = px.pie(
            flight_df, values="n", names="flight_status",
            color="flight_status",
            color_discrete_map={
                "On Time":  COLORS["positive"],
                "Delayed":  COLORS["warning"],
                "Cancelled": COLORS["negative"],
            },
            hole=0.5,
        )
        fig2.update_traces(textinfo="percent+label", showlegend=False)
        fig2.update_layout(
            height=200, margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="white",
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown('<p class="section-title">Causes de disruption</p>', unsafe_allow_html=True)
        disr_df = db.load_disruption_mix()
        fig3 = px.bar(
            disr_df, x="share_pct", y="root_cause", orientation="h",
            color_discrete_sequence=[COLORS["primary"]],
            text="n_disruptions",
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(
            height=160, showlegend=False,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="", yaxis_title="",
            margin=dict(l=0, r=40, t=10, b=10),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── Graphe 2 : Opportunity matrix (scatter load factor vs margin pct)
    st.markdown("---")
    st.markdown('<p class="section-title">Route Opportunity Matrix — Load Factor × Marge %</p>',
                unsafe_allow_html=True)
    st.caption("Quadrant idéal : haut-droite (LF > 50%, Marge > 0). Paris = haut potentiel mais sous-utilisé.")

    fig4 = px.scatter(
        route_df,
        x="avg_load_factor_pct", y="margin_pct",
        size="total_revenue_usd",
        color="route_type",
        color_discrete_map=ROUTE_COLORS,
        text="route_label",
        labels={"avg_load_factor_pct": "Load Factor (%)", "margin_pct": "Marge (%)"},
        custom_data=["route_label", "total_revenue_usd", "total_margin_usd", "avg_otp_pct"],
        size_max=45,
    )
    fig4.update_traces(
        textposition="top center",
        hovertemplate="<b>%{customdata[0]}</b><br>LF: %{x:.1f}%<br>Marge: %{y:.1f}%<br>"
                      "Revenue: $%{customdata[1]:,.0f}<br>OTP: %{customdata[3]:.1f}%<extra></extra>",
    )
    # Quadrant lines
    fig4.add_hline(y=0,  line_dash="dash", line_color="#999", line_width=1)
    fig4.add_vline(x=50, line_dash="dash", line_color="#999", line_width=1)
    fig4.add_annotation(x=70, y=35, text="✅ Grow", font_color=COLORS["positive"], showarrow=False)
    fig4.add_annotation(x=5,  y=35, text="⚠️ Defend / Reprice", font_color=COLORS["warning"], showarrow=False)
    fig4.add_annotation(x=70, y=-90, text="⚡ Fix demand", font_color=COLORS["accent"], showarrow=False)
    fig4.add_annotation(x=5,  y=-90, text="🔴 Review", font_color=COLORS["negative"], showarrow=False)
    fig4.update_layout(
        height=420, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig4, use_container_width=True)

    # ── Table détaillée
    st.markdown("---")
    st.markdown('<p class="section-title">Détail route P&L</p>', unsafe_allow_html=True)
    display_cols = ["route_label", "route_type", "flights", "avg_load_factor_pct",
                    "avg_otp_pct", "total_revenue_usd", "total_margin_usd", "margin_pct"]
    st.dataframe(
        route_df[display_cols].rename(columns={
            "route_label": "Route", "route_type": "Type",
            "flights": "Vols", "avg_load_factor_pct": "LF %",
            "avg_otp_pct": "OTP %", "total_revenue_usd": "Revenue $",
            "total_margin_usd": "Marge $", "margin_pct": "Marge %",
        }),
        use_container_width=True, hide_index=True,
    )


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER & RETENTION
# ═══════════════════════════════════════════════════════════════════

elif page == "👥 Customer & Retention":
    st.title("👥 Customer & Retention")
    st.caption("Segmentation · Loyalty engagement · NPS proxy · At-risk customers")

    cust_df     = db.load_customer_summary()
    at_risk_df  = db.load_at_risk_customers()
    review_df   = db.load_review_trends()
    neg_topics  = db.load_negative_topics()

    # KPIs
    total_cust   = cust_df["n_customers"].sum()
    loyal_active = cust_df["n_loyalty_active"].sum()
    avg_ltv      = (cust_df["avg_ltv"] * cust_df["n_customers"]).sum() / total_cust
    n_at_risk    = len(at_risk_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers",             f"{total_cust:,}")
    c2.metric("Loyalty actif",          f"{loyal_active:,}",
              f"{loyal_active/total_cust*100:.0f}% du base")
    c3.metric("LTV moyen",              fmt_usd(avg_ltv))
    c4.metric("⚠️ High-Value At-Risk",   str(n_at_risk),
              "à cibler en rétention", delta_color="inverse")

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── Segmentation par tier × segment
    with col1:
        st.markdown('<p class="section-title">Segmentation : LTV moyen par segment × tier</p>',
                    unsafe_allow_html=True)
        seg_pivot = cust_df.groupby("customer_segment")[["avg_ltv", "n_customers"]].apply(
            lambda g: pd.Series({
                "avg_ltv": (g["avg_ltv"] * g["n_customers"]).sum() / g["n_customers"].sum(),
                "n_customers": g["n_customers"].sum(),
            })
        ).reset_index()
        fig = px.bar(
            seg_pivot.sort_values("avg_ltv", ascending=False),
            x="customer_segment", y="avg_ltv",
            color_discrete_sequence=[COLORS["primary"]],
            text="avg_ltv",
            labels={"customer_segment": "Segment", "avg_ltv": "LTV moyen ($)"},
        )
        fig.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
        fig.update_layout(
            height=280, plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False, margin=dict(l=0, r=0, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── NPS proxy par route
    with col2:
        st.markdown('<p class="section-title">NPS Proxy par route</p>', unsafe_allow_html=True)
        fig2 = px.bar(
            review_df.sort_values("nps_proxy"),
            x="nps_proxy", y="route_label",
            color="nps_proxy",
            color_continuous_scale=["#DC2626", "#FCA5A5", "#D1FAE5", "#16A34A"],
            color_continuous_midpoint=0,
            orientation="h",
            text="nps_proxy",
            labels={"nps_proxy": "NPS Proxy", "route_label": "Route"},
            custom_data=["avg_rating", "pct_promoter", "pct_detractor"],
        )
        fig2.update_traces(
            texttemplate="%{x:+.0f}",
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>NPS: %{x:+.0f}<br>Rating: %{customdata[0]:.2f}★<br>"
                          "Promoteurs: %{customdata[1]:.1f}%<br>Détracteurs: %{customdata[2]:.1f}%<extra></extra>",
        )
        fig2.update_layout(
            height=280, showlegend=False, coloraxis_showscale=False,
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(zeroline=True, zerolinecolor="#999"),
            margin=dict(l=0, r=60, t=20, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Thèmes négatifs
    st.markdown("---")
    st.markdown('<p class="section-title">Top thèmes des reviews négatives (rating ≤ 2)</p>',
                unsafe_allow_html=True)
    neg_row = neg_topics.iloc[0]
    topics_df = pd.DataFrame(
        [(k, int(v)) for k, v in neg_row.items()],
        columns=["topic", "count"]
    ).sort_values("count", ascending=False)

    fig3 = px.bar(
        topics_df,
        x="topic", y="count",
        color_discrete_sequence=[COLORS["negative"]],
        text="count",
        labels={"topic": "Topic", "count": "Occurrences"},
    )
    fig3.update_traces(textposition="outside")
    fig3.update_layout(
        height=240, plot_bgcolor="white", paper_bgcolor="white",
        showlegend=False, margin=dict(l=0, r=0, t=20, b=20),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── High-value at-risk customers
    st.markdown("---")
    st.markdown(
        f'<p class="section-title">⚠️ High-Value At-Risk Customers ({n_at_risk} identifiés)</p>',
        unsafe_allow_html=True,
    )
    if n_at_risk > 0:
        total_ltv_at_risk = at_risk_df["ltv_usd"].sum()
        st.markdown(
            f"""<div class="warning-box">
            <b>Revenue protégé :</b> {fmt_usd(total_ltv_at_risk)} concentré sur {n_at_risk} customers.<br>
            <b>Signal :</b> Silver/Gold tier avec engagement loyalty en dessous de la médiane du peer group.<br>
            <b>Action recommandée :</b> Voucher "status saver" ou offre upgrade ciblée.
            </div>""",
            unsafe_allow_html=True,
        )
        st.dataframe(
            at_risk_df.rename(columns={
                "customer_id": "Customer", "customer_segment": "Segment",
                "loyalty_tier": "Tier", "total_bookings": "Bookings",
                "ltv_usd": "LTV ($)", "earn_event_count": "Loyalty events",
                "engagement_ratio": "Engagement ratio", "cohort_median": "Cohort median",
                "high_severity_tickets": "Tickets critiques",
            }),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Aucun customer at-risk identifié avec les seuils actuels.")


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — UPSELL & CROSS-SELL
# ═══════════════════════════════════════════════════════════════════

elif page == "💰 Upsell & Cross-sell":
    st.title("💰 Upsell & Cross-sell")
    st.caption("Ancillary attach rate · ARPU ancillaire · Mix items · Segments cibles")

    attach_df  = db.load_ancillary_attach()
    seg_df     = db.load_ancillary_by_segment()
    upsell_df  = db.load_upsell_ready()
    channel_df = db.load_channel_mix()

    # KPIs
    total_bk     = attach_df["bookings"].sum()
    total_anc    = (attach_df["arpu_ancillary"] * attach_df["bookings"]).sum()
    avg_attach   = (attach_df["attach_rate_pct"] * attach_df["bookings"]).sum() / total_bk
    n_upsell     = len(upsell_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ancillary Attach Rate",  f"{avg_attach:.1f}%")
    c2.metric("ARPU Ancillaire",        fmt_usd(total_anc / total_bk))
    c3.metric("Revenue ancillaire tot.", fmt_usd(total_anc))
    c4.metric("🎯 Upsell-Ready",         str(n_upsell), "customers Economy sous-attachés")

    st.markdown("---")

    col1, col2 = st.columns(2)

    # ── Attach rate par item type × fare_family
    with col1:
        st.markdown('<p class="section-title">Attach rate par item et fare family</p>',
                    unsafe_allow_html=True)
        items = ["attach_lounge_pct", "attach_upgrade_pct", "attach_meal_pct",
                 "attach_seat_pct", "attach_rate_pct"]
        item_labels = {"attach_lounge_pct": "Lounge", "attach_upgrade_pct": "Upgrade",
                       "attach_meal_pct": "Meal", "attach_seat_pct": "Seat",
                       "attach_rate_pct": "Any"}
        melted = attach_df.melt(
            id_vars="fare_family",
            value_vars=["attach_lounge_pct", "attach_upgrade_pct",
                        "attach_meal_pct", "attach_seat_pct"],
            var_name="item", value_name="attach_pct",
        )
        melted["item"] = melted["item"].map(
            {"attach_lounge_pct": "Lounge", "attach_upgrade_pct": "Upgrade",
             "attach_meal_pct": "Meal", "attach_seat_pct": "Seat"})
        fig = px.bar(
            melted, x="attach_pct", y="item",
            color="fare_family", barmode="group",
            orientation="h",
            color_discrete_sequence=["#1D4ED8", "#3B82F6", "#93C5FD"],
            labels={"attach_pct": "Attach %", "item": "", "fare_family": "Fare Family"},
        )
        fig.update_layout(
            height=260, plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Mix de revenus ancillaires par type
    with col2:
        st.markdown('<p class="section-title">Mix revenus ancillaires</p>', unsafe_allow_html=True)
        total_cols = ["total_baggage_usd", "total_seat_usd",
                      "total_meal_usd", "total_lounge_usd", "total_upgrade_usd"]
        item_names = {"total_baggage_usd": "Baggage", "total_seat_usd": "Seat",
                      "total_meal_usd": "Meal", "total_lounge_usd": "Lounge",
                      "total_upgrade_usd": "Upgrade"}
        totals = attach_df[total_cols].sum()
        mix_df = pd.DataFrame({"item": totals.index.map(item_names), "revenue": totals.values})
        fig2 = px.pie(
            mix_df, values="revenue", names="item",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            hole=0.45,
        )
        fig2.update_traces(textinfo="percent+label", showlegend=False)
        fig2.update_layout(
            height=260, paper_bgcolor="white",
            margin=dict(l=0, r=0, t=20, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── ARPU ancillaire par segment
    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<p class="section-title">ARPU ancillaire par segment</p>',
                    unsafe_allow_html=True)
        fig3 = px.bar(
            seg_df.sort_values("arpu_ancillary", ascending=False),
            x="customer_segment", y="arpu_ancillary",
            text="arpu_ancillary",
            color_discrete_sequence=[COLORS["accent"]],
            labels={"customer_segment": "Segment", "arpu_ancillary": "ARPU ($)"},
        )
        fig3.update_traces(texttemplate="$%{y:.2f}", textposition="outside")
        fig3.update_layout(
            height=240, plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False, margin=dict(l=0, r=0, t=20, b=20),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.markdown('<p class="section-title">Revenue par channel</p>', unsafe_allow_html=True)
        fig4 = px.bar(
            channel_df.sort_values("total_revenue_usd", ascending=True),
            x="total_revenue_usd", y="booking_channel",
            orientation="h",
            color_discrete_sequence=[COLORS["primary"]],
            text="total_revenue_usd",
            labels={"total_revenue_usd": "Revenue ($)", "booking_channel": "Channel"},
            custom_data=["avg_ticket_usd", "arpu_ancillary"],
        )
        fig4.update_traces(
            texttemplate="$%{x:,.0f}", textposition="outside",
            hovertemplate="<b>%{y}</b><br>Revenue: $%{x:,.0f}<br>"
                          "Ticket moy: $%{customdata[0]:,.0f}<br>"
                          "ARPU ancil: $%{customdata[1]:.2f}<extra></extra>",
        )
        fig4.update_layout(
            height=240, plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False, margin=dict(l=0, r=80, t=20, b=20),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ── Upsell-ready customers
    st.markdown("---")
    st.markdown(
        f'<p class="section-title">🎯 Upsell-Ready Segment ({n_upsell} customers Economy sous-attachés)</p>',
        unsafe_allow_html=True,
    )
    if not upsell_df.empty:
        total_ltv_upsell = upsell_df["ltv_usd"].sum()
        st.markdown(
            f"""<div class="recommendation-box">
            <b>Opportunité :</b> {n_upsell} customers Economy avec LTV > p60 et attach rate < p25 de leurs pairs.<br>
            <b>LTV cumulée :</b> {fmt_usd(total_ltv_upsell)}<br>
            <b>Offres prioritaires :</b> Lounge access (+$45–80), Seat upgrade (+$18–35), Meal upgrade (+$15–25).
            </div>""",
            unsafe_allow_html=True,
        )
        st.dataframe(
            upsell_df.rename(columns={
                "customer_id": "Customer", "customer_segment": "Segment",
                "loyalty_tier": "Tier", "total_bookings": "Bookings",
                "ltv_usd": "LTV ($)", "attach_pct": "Attach %",
                "p25_threshold_pct": "Seuil p25 (%)",
            }),
            use_container_width=True, hide_index=True,
        )


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — DECISION LAYER (LA PLUS IMPORTANTE)
# ═══════════════════════════════════════════════════════════════════

elif page == "🎯 Decision Layer":
    st.title("🎯 Decision Layer")
    st.markdown(
        "#### Où allouer le budget des 12 prochains mois pour maximiser la croissance rentable ?",
        help="Basé sur les 3 ontology rules + route P&L + satisfaction client."
    )

    # ── Réponse headline
    st.markdown("""
    <div style="background:#EEF7EE; border-left:6px solid #16A34A;
                padding:16px 20px; border-radius:8px; margin-bottom:16px;">
        <h4 style="margin:0; color:#15803D;">Recommandation principale (Phase 1-2)</h4>
        <p style="margin:8px 0 0; color:#374151;">
        Investir en priorité sur <b>1) Upsell/cross-sell</b> (payback 0–3 mois),
        puis <b>2) Rétention client</b> (3–6 mois), puis
        <b>3) Demand generation sur Paris</b> (marketing/distribution, pas nouvelle route).<br>
        L'expansion réseau vers de nouvelles destinations est <b>prématurée</b> tant que Paris
        opère à ~9% de load factor.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Allocation suggérée (donut)
    kpis      = db.load_global_kpis()
    strat_df  = db.load_strategic_underperforming()
    at_risk_df = db.load_at_risk_customers()
    upsell_df  = db.load_upsell_ready()
    route_df   = db.load_route_summary()

    col_budget, col_kpis = st.columns([1, 2])

    with col_budget:
        st.markdown('<p class="section-title">Allocation budget suggérée</p>',
                    unsafe_allow_html=True)
        budget_df = pd.DataFrame({
            "levier": ["Upsell / Cross-sell", "Rétention client",
                       "Demand gen Paris", "Réserve opérationnelle"],
            "pct":    [40, 30, 20, 10],
        })
        fig = px.pie(
            budget_df, values="pct", names="levier",
            color_discrete_sequence=["#16A34A", "#2563EB", "#D97706", "#9CA3AF"],
            hole=0.55,
        )
        fig.update_traces(
            textinfo="percent+label", showlegend=False,
            hovertemplate="<b>%{label}</b><br>%{value}% du budget<extra></extra>",
        )
        fig.update_layout(
            height=260, paper_bgcolor="white",
            margin=dict(l=0, r=0, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_kpis:
        st.markdown('<p class="section-title">Signaux qui justifient ce ranking</p>',
                    unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        r1.metric("Attach rate actuel",     f"{83:.0f}%",
                  "Élevé → mix shift, pas volume", delta_color="off")
        r2.metric("At-risk customers",      str(len(at_risk_df)),
                  f"${at_risk_df['ltv_usd'].sum():,.0f} LTV à protéger" if len(at_risk_df) else "0",
                  delta_color="inverse")
        r3.metric("Upsell-ready customers", str(len(upsell_df)),
                  f"${upsell_df['ltv_usd'].sum():,.0f} LTV cumulée" if not upsell_df.empty else "0")

        r4, r5, r6 = st.columns(3)
        r4.metric("Load Factor Paris",  "9.3%", "vs 75% nécessaire pour break-even",
                  delta_color="inverse")
        r5.metric("Marge réseau",       f"{kpis['margin_pct']:+.1f}%",
                  delta_color=delta_color(kpis["margin_pct"]))
        best_route = route_df.loc[route_df["margin_pct"].idxmax(), "route_label"]
        r6.metric("Meilleure route",    best_route,
                  f"{route_df['margin_pct'].max():.1f}% marge", delta_color="off")

    st.markdown("---")

    # ── 3 colonnes : routes / rétention / upsell
    col_r, col_c, col_u = st.columns(3)

    with col_r:
        st.markdown("### 🗺️ Routes")

        # Routes à DÉVELOPPER (margin > 0, load < 70%)
        grow = route_df[(route_df["margin_pct"] > 0) & (route_df["avg_load_factor_pct"] < 70)]
        st.markdown("**✅ À développer** (rentables, capacité disponible)")
        if not grow.empty:
            for _, r in grow.iterrows():
                st.markdown(
                    f"""<div class="recommendation-box" style="padding:8px 12px; margin:4px 0;">
                    <b>{r['route_label']}</b> · {r['route_type']}<br>
                    Marge {r['margin_pct']:+.1f}% · LF {r['avg_load_factor_pct']:.1f}%
                    </div>""",
                    unsafe_allow_html=True,
                )

        st.markdown("**🔴 À défendre** (stratégiques mais déficitaires)")
        if not strat_df.empty:
            for _, r in strat_df.iterrows():
                st.markdown(
                    f"""<div class="danger-box" style="padding:8px 12px; margin:4px 0;">
                    <b>{r['route_label']}</b> · {r['route_type']}<br>
                    Marge {r['margin_pct']:+.1f}% · LF {r['load_factor_pct']:.1f}%<br>
                    → Demand generation, pas abandon
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Aucune route déficitaire avec part > 5%")

    with col_c:
        st.markdown("### 👥 Rétention")

        n_at_risk = len(at_risk_df)
        if n_at_risk > 0:
            total_ltv_risk = at_risk_df["ltv_usd"].sum()
            st.markdown(f"**⚠️ {n_at_risk} customers à retenir**")
            st.markdown(
                f"""<div class="warning-box">
                <b>Revenue à protéger :</b> {fmt_usd(total_ltv_risk)}<br>
                <b>Profil :</b> Silver/Gold, engagement < médiane pairs<br>
                <b>Action :</b> Voucher €50 ou offre status-match.<br>
                <b>ROI estimé :</b> si 30% convertis → {fmt_usd(total_ltv_risk * 0.3)} LTV protégée
                </div>""",
                unsafe_allow_html=True,
            )
            st.dataframe(
                at_risk_df[["customer_id", "customer_segment", "loyalty_tier",
                            "ltv_usd", "engagement_ratio"]].head(6).rename(columns={
                    "customer_id": "ID", "customer_segment": "Segment",
                    "loyalty_tier": "Tier", "ltv_usd": "LTV ($)",
                    "engagement_ratio": "Engagement",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("Pas de customers at-risk identifiés.")

        # Top routes par satisfaction
        review_df = db.load_review_trends()
        st.markdown("**📊 Satisfaction par route** (NPS proxy)")
        worst = review_df.sort_values("nps_proxy").head(3)
        for _, r in worst.iterrows():
            color_class = "danger-box" if r["nps_proxy"] < 0 else "warning-box"
            st.markdown(
                f"""<div class="{color_class}" style="padding:8px 12px; margin:4px 0;">
                <b>{r['route_label']}</b> · NPS {r['nps_proxy']:+.0f}
                · Rating {r['avg_rating']:.2f}★
                </div>""",
                unsafe_allow_html=True,
            )

    with col_u:
        st.markdown("### 💰 Upsell")

        if not upsell_df.empty:
            total_ltv_up = upsell_df["ltv_usd"].sum()
            st.markdown(f"**🎯 {len(upsell_df)} customers upsell-ready**")
            st.markdown(
                f"""<div class="recommendation-box">
                <b>LTV cumulée :</b> {fmt_usd(total_ltv_up)}<br>
                <b>Profil :</b> Economy-dominant, LTV > p60, attach < p25 pairs<br>
                <b>Offres prioritaires :</b><br>
                — Lounge access : $45–80 (+{len(upsell_df) * 60:,}$ potentiel)<br>
                — Seat upgrade : $18–35<br>
                — Meal upgrade : $15–25
                </div>""",
                unsafe_allow_html=True,
            )
            st.dataframe(
                upsell_df[["customer_id", "customer_segment", "ltv_usd",
                           "attach_pct"]].head(6).rename(columns={
                    "customer_id": "ID", "customer_segment": "Segment",
                    "ltv_usd": "LTV ($)", "attach_pct": "Attach %",
                }),
                use_container_width=True, hide_index=True,
            )

        # Mix ancillaire actuel vs potentiel
        attach_df = db.load_ancillary_attach()
        st.markdown("**📊 Comparaison attach rate par fare family**")
        fig_a = px.bar(
            attach_df,
            x="fare_family",
            y=["attach_lounge_pct", "attach_upgrade_pct", "attach_meal_pct"],
            barmode="group",
            labels={"value": "%", "variable": "Item", "fare_family": ""},
            color_discrete_map={
                "attach_lounge_pct":  "#1D4ED8",
                "attach_upgrade_pct": "#16A34A",
                "attach_meal_pct":    "#D97706",
            },
        )
        fig_a.update_layout(
            height=200, plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_a, use_container_width=True)

    # ── Recommandation executive
    st.markdown("---")
    st.markdown("### 📋 Page Executive — Recommandations synthétiques")

    rec_data = [
        {
            "Priorité": "1 — Court terme (0–3 mois)",
            "Levier": "Upsell / Cross-sell",
            "Action concrète": "Revoir la proposition ancillaire : bundle Lounge + Meal pour les clients Flex et Standard sur routes régionales. Objectif : ARPU +$15–25.",
            "Indicateur de succès": "ARPU ancillaire > $25 · Attach lounge > 15%",
            "ROI estimé": "Élevé · Investissement minimal (pricing + UI)",
        },
        {
            "Priorité": "2 — Moyen terme (3–6 mois)",
            "Levier": "Rétention client",
            "Action concrète": f"Programme voucher ciblé sur les {len(at_risk_df)} customers Silver/Gold à faible engagement. Offre : réduction upgrade ou accès lounge gratuit.",
            "Indicateur de succès": "Réengagement 30%+ de la cohorte · LTV protégée",
            "ROI estimé": f"Fort · {fmt_usd(at_risk_df['ltv_usd'].sum() * 0.3)} LTV si 30% convertis",
        },
        {
            "Priorité": "3 — Long terme (6–12 mois)",
            "Levier": "Demand generation Paris",
            "Action concrète": "Investir dans la distribution (OTA, partenaires trade France) et le marketing diaspora CI-France. L'A330neo est en place, la demande doit suivre.",
            "Indicateur de succès": "Load Factor Paris > 50% · Margin% > -20%",
            "ROI estimé": "Moyen · Dépend du volume distribué",
        },
        {
            "Priorité": "✋ Hold",
            "Levier": "Expansion réseau (nouvelle route)",
            "Action concrète": "Reporter l'ouverture de toute nouvelle destination jusqu'à ce que Paris atteigne le break-even en load factor.",
            "Indicateur de succès": "Load Factor Paris ≥ 65%",
            "ROI estimé": "Risque élevé si Paris non comblé",
        },
    ]
    st.dataframe(
        pd.DataFrame(rec_data),
        use_container_width=True, hide_index=True,
    )