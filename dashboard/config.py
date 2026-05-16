# dashboard/config.py
# Palette et constantes partagées par toutes les pages

COLORS = {
    "primary":    "#1F4E79",   # bleu foncé (titres, headers)
    "accent":     "#2563EB",   # bleu vif (charts principaux)
    "positive":   "#16A34A",   # vert (marges positives)
    "negative":   "#DC2626",   # rouge (marges négatives, at-risk)
    "warning":    "#D97706",   # orange (à surveiller)
    "neutral":    "#6B7280",   # gris (labels secondaires)
    "bg_light":   "#F0F4FF",   # fond léger bleu
    "bg_card":    "#FFFFFF",
}

ROUTE_COLORS = {
    "Domestic":      "#94A3B8",
    "Regional":      "#3B82F6",
    "International": "#1D4ED8",
}

SENTIMENT_COLORS = {
    "Promoter":  "#16A34A",
    "Passive":   "#D97706",
    "Detractor": "#DC2626",
}

# Labels pour les axes
KPI_LABELS = {
    "margin_pct":           "Marge %",
    "load_factor":          "Load Factor",
    "on_time_performance":  "OTP %",
    "cancellation_rate":    "Taux Annulation %",
    "total_revenue_usd":    "Revenu (USD)",
    "total_operating_cost_usd": "Coût opérationnel (USD)",
    "rask":                 "RASK",
    "cask":                 "CASK",
}

# Mapping route_id → label court
ROUTE_LABELS = {
    "R001": "ABJ→BYK",  "R002": "ABJ→MJC",  "R003": "ABJ→HGO",
    "R004": "ABJ→ACC",  "R005": "ABJ→DKR",  "R006": "ABJ→LOS",
    "R007": "ABJ→COO",  "R008": "ABJ→OUA",  "R009": "ABJ→CDG",
    "R010": "ACC→ABJ",  "R011": "DKR→ABJ",  "R012": "LOS→ABJ",
}