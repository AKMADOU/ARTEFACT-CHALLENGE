#!/usr/bin/env python3
"""
demo.py — Démo des 5 outils MCP sans client AI
================================================
Ce script importe les outils directement et montre les réponses.
Utile pour valider que le server fonctionne AVANT de le brancher à Claude.

Run :  python demo.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Import direct des fonctions (pas besoin du client MCP pour la démo)
from mcp_server.server import (
    query_route_metrics,
    get_at_risk_customers,
    search_reviews_by_route,
    recommend_budget_allocation,
    explain_route_pnl,
)

SEP = "\n" + "─" * 65 + "\n"

QUESTIONS = [
    {
        "question": "Quelles routes méritent plus de budget au prochain trimestre ?",
        "call":     lambda: query_route_metrics(sort_by="margin_pct"),
        "comment":  "→ Tool: query_route_metrics | Vue complète du P&L par route",
    },
    {
        "question": "Quelles routes sont déficitaires malgré leur importance stratégique ?",
        "call":     lambda: query_route_metrics(route_type="International", max_margin_pct=-0.01),
        "comment":  "→ Tool: query_route_metrics | Filtre sur routes intl déficitaires",
    },
    {
        "question": "Quels customers high-value sont à risque de churn ?",
        "call":     lambda: get_at_risk_customers(limit=10),
        "comment":  "→ Tool: get_at_risk_customers | Ontology rule at-risk",
    },
    {
        "question": "Que disent les clients mécontents sur la route Paris ?",
        "call":     lambda: search_reviews_by_route(route_id="R009", sentiment="negative", limit=5),
        "comment":  "→ Tool: search_reviews_by_route | Détracteurs + thèmes négatifs",
    },
    {
        "question": "Quelles sont les plaintes de ponctualité sur Dakar ?",
        "call":     lambda: search_reviews_by_route(route_id="R005", topic="punctuality", limit=5),
        "comment":  "→ Tool: search_reviews_by_route | Filtre topic=punctuality",
    },
    {
        "question": "Explique le P&L de la route Paris (R009) en détail.",
        "call":     lambda: explain_route_pnl("R009"),
        "comment":  "→ Tool: explain_route_pnl | Rapport narratif complet",
    },
    {
        "question": "Compare la route Accra (R004) et la route Dakar (R005).",
        "call":     lambda: "\n\n".join([
            "=== ACCRA ===\n" + explain_route_pnl("R004"),
            "=== DAKAR ===\n" + explain_route_pnl("R005"),
        ]),
        "comment":  "→ Tool: explain_route_pnl x2 | Comparaison en 2 appels",
    },
    {
        "question": "Où doit investir Air CI pour maximiser la croissance rentable ?",
        "call":     lambda: recommend_budget_allocation(include_evidence=True),
        "comment":  "→ Tool: recommend_budget_allocation | Recommandation globale",
    },
]


def run_demo():
    print("=" * 65)
    print("Air Côte d'Ivoire — MCP Tools Demo")
    print("Validation des 5 outils sur les données réelles")
    print("=" * 65)

    for i, q in enumerate(QUESTIONS, 1):
        print(f"\n{'━'*65}")
        print(f"Q{i}. {q['question']}")
        print(f"     {q['comment']}")
        print("━" * 65)
        try:
            result = q["call"]()
            print(result)
        except Exception as e:
            print(f"❌ Erreur : {e}")
            import traceback; traceback.print_exc()

    print("\n" + "=" * 65)
    print("✅ Démo terminée. Tous les outils ont été testés.")
    print("Pour brancher à Claude Desktop, voir README.md")
    print("=" * 65)


if __name__ == "__main__":
    run_demo()
