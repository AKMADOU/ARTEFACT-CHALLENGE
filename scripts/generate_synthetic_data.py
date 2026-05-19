"""
Air Côte d'Ivoire — Synthetic Data Generation
==============================================

Generates 7 synthetic datasets that enrich the starter Excel file.

Run:
    python scripts/generate_synthetic_data.py \
        --starter ./air_cote_divoire_starter_dataset.xlsx \
        --out-dir ./data/synthetic/

Outputs (CSV + combined Excel):
    - aircraft_fleet.csv
    - fuel_prices_monthly.csv
    - route_operating_costs.csv
    - ancillary_catalog.csv
    - ancillary_purchases.csv
    - loyalty_transactions.csv
    - customer_reviews.csv
    - support_tickets.csv
    - disruption_log.csv
    - enriched_dataset.xlsx (all sheets combined, starter + synthetic)

All generation is deterministic (SEED=42). Numbers are calibrated to be
internally consistent (e.g. ancillary_purchases sums to bookings'
ancillary_revenue_usd, fuel_cost respects fuel_burn × price).
"""

from __future__ import annotations
import argparse
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42

# ============================================================
# 1. Reference / static data
# ============================================================
#== Elle décrit la flotte d’appareils de la compagnie avec ces colonnes :

#   aircraft_type : type d’avion
#   manufacturer : constructeur
#   seats_total : nombre total de sièges
#   seats_business : sièges business
#   seats_premium_eco : sièges premium economy
#   seats_economy : sièges economy
#   fuel_burn_kg_per_hour : consommation de carburant en kg/h
#   cost_per_block_hour_usd : coût par heure de bloc en USD
#   crew_cost_per_hour_usd : coût des équipages par heure en USD
#   introduced_year : année d’entrée en service
#   fleet_count : nombre d’appareils de ce type
#==== 
AIRCRAFT_FLEET = pd.DataFrame([
    # aircraft_type, manufacturer, seats_total, seats_business, seats_premium_eco,
    # seats_economy, fuel_burn_kg_per_hour, cost_per_block_hour_usd, crew_cost_per_hour_usd,
    # introduced_year, fleet_count
    ("A319",        "Airbus", 122,  8,  0, 114, 2400, 4200,  550, 2013, 2),
    ("A320",        "Airbus", 150, 12,  0, 138, 2500, 4500,  580, 2017, 3),
    ("A320neo",     "Airbus", 165, 16, 12, 137, 2100, 4300,  600, 2022, 2),
    ("A330-900neo", "Airbus", 242, 30, 21, 191, 5500, 9500, 1200, 2024, 2),
], columns=[
    "aircraft_type", "manufacturer", "seats_total", "seats_business",
    "seats_premium_eco", "seats_economy", "fuel_burn_kg_per_hour",
    "cost_per_block_hour_usd", "crew_cost_per_hour_usd",
    "introduced_year", "fleet_count",
])

#==== Elle contient les prix du carburant pour chaque mois :

#   year_month : période au format YYYY-MM
#   jet_fuel_usd_per_kg : prix du kérosène en dollars US par kilogramme
#   jet_fuel_usd_per_gallon : prix du kérosène en dollars US par gallon
#  
#   Dans le script, FUEL_PRICES est fusionné avec les vols (flights) pour calculer le coût carburant par vol dans build_route_operating_costs().
FUEL_PRICES = pd.DataFrame([
    ("2024-11", 0.82, 3.10),
    ("2024-12", 0.85, 3.21),
    ("2025-01", 0.88, 3.32),
], columns=["year_month", "jet_fuel_usd_per_kg", "jet_fuel_usd_per_gallon"])

#=== Elle représente le catalogue des services additionnels vendus aux passagers, avec ces colonnes :

# item_id : identifiant du produit
# item_name : nom du service
# base_price_usd : prix de base en dollars US
# applies_to_route_type : type de route pour lequel l’option est disponible (ALL, Regional, International, etc.)
# Utilisation dans le script
# Ce catalogue est utilisé par build_ancillary_purchases() pour décomposer la ancillary_revenue_usd d’une réservation en un ou plusieurs achats d’options, en fonction de la classe tarifaire et du type de route.
ANCILLARY_CATALOG = pd.DataFrame([
    # item_id, item_type, item_name, base_price_usd, applies_to_route_type
    ("ANC01", "baggage",        "Extra Bag 23kg",      35, "ALL"),
    ("ANC02", "baggage",        "Extra Bag 32kg",      50, "ALL"),
    ("ANC03", "seat",           "Standard Seat",        8, "ALL"),
    ("ANC04", "seat",           "Preferred Seat",      18, "ALL"),
    ("ANC05", "seat",           "Extra Legroom Seat",  35, "Regional,International"),
    ("ANC06", "meal",           "Hot Meal Upgrade",    15, "Regional,International"),
    ("ANC07", "meal",           "Premium Meal",        25, "International"),
    ("ANC08", "lounge",         "Lounge Access ABJ",   45, "Regional,International"),
    ("ANC09", "lounge",         "Lounge Access CDG",   80, "International"),
    ("ANC10", "priority",       "Priority Boarding",   12, "ALL"),
    ("ANC11", "priority",       "Fast Track Security", 15, "Regional,International"),
    ("ANC12", "upgrade",        "Upgrade to PremEco", 180, "International"),
    ("ANC13", "upgrade",        "Upgrade to Business",550, "International"),
    ("ANC14", "upgrade",        "Upgrade to Business",120, "Regional"),
], columns=["item_id", "item_type", "item_name", "base_price_usd", "applies_to_route_type"])
#=== Elle mappe chaque type de route à un coût fixe d’atterrissage/débarquement :

# Domestic : 450
# Regional : 1200
# International : 5000
# Dans build_route_operating_costs(), le script utilise AIRPORT_FEES pour ajouter airport_fees_usd au coût total d’exploitation de chaque vol, selon le route_type du vol.
AIRPORT_FEES = {
    "Domestic":      450,
    "Regional":     1200,
    "International": 5000,
}

# ============================================================
# 2. Helpers
# ============================================================
#=== Cette fonction prend une date ou datetime et renvoie une chaîne au format YYYY-MM.
def year_month(d) -> str:
    """Return YYYY-MM string from a datetime/date."""
    return pd.to_datetime(d).strftime("%Y-%m")

#== Cette fonction convertit une durée en minutes en heures :
#  entrée : block_time_min (minutes)
#  sortie : block_time_min / 60.0

def block_hours(block_time_min: int) -> float:
    return block_time_min / 60.0


# ============================================================
# 3. Synthetic dataset builders
# ============================================================

#== C’est une fonction qui calcule le coût d’exploitation par vol.

#  Ce qu’elle fait
#  .fusionne flights avec routes pour récupérer route_type, distance_km et block_time_min
#  .fusionne ensuite avec AIRCRAFT_FLEET pour obtenir la consommation et les coûts avion/équipage
#  .utilise year_month() pour retrouver le mois du vol
#  .fusionne avec FUEL_PRICES pour obtenir le prix du carburant du mois

#  Calculs produits
#  .fuel_cost_usd = block_hours × fuel_burn × jet_fuel_usd_per_kg
#  .crew_cost_usd = block_hours × crew_cost_per_hour_usd
#  .airport_fees_usd = coût fixe selon route_type à partir de AIRPORT_FEES
#  .nav_fees_usd = 0.15 × distance_km × (seat_capacity / 100)
#  .handling_cost_usd = 250 × (seat_capacity / 100)
#  .total_operating_cost_usd = somme de tous les éléments précédents

#  Résultat
#  La fonction retourne un DataFrame avec ces colonnes :
#  .flight_id
#  .fuel_cost_usd
#  .crew_cost_usd
#  .airport_fees_usd
#  .nav_fees_usd
#  .handling_cost_usd
#  .total_operating_cost_usd
#  C’est la base du fichier route_operating_costs.csv.

def build_route_operating_costs(flights: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
    """
    Per-flight cost decomposition.
        fuel_cost     = block_hours × fuel_burn × fuel_price
        crew_cost     = block_hours × crew_cost_per_hour
        airport_fees  = lookup by route_type (each way)
        nav_fees      = 0.15 × distance_km × (seat_capacity / 100)
        handling      = 250 × (seat_capacity / 100)
    """
    f = flights.merge(routes[["route_id", "route_type", "distance_km", "block_time_min"]],
                      on="route_id", how="left")
    f = f.merge(
        AIRCRAFT_FLEET[["aircraft_type", "fuel_burn_kg_per_hour",
                        "cost_per_block_hour_usd", "crew_cost_per_hour_usd"]],
        on="aircraft_type", how="left",
    )
    f["year_month"] = f["flight_date"].apply(year_month)
    f = f.merge(FUEL_PRICES[["year_month", "jet_fuel_usd_per_kg"]],
                on="year_month", how="left")

    bh = f["block_time_min"] / 60.0
    f["fuel_cost_usd"]    = (bh * f["fuel_burn_kg_per_hour"] * f["jet_fuel_usd_per_kg"]).round(2)
    f["crew_cost_usd"]    = (bh * f["crew_cost_per_hour_usd"]).round(2)
    f["airport_fees_usd"] = f["route_type"].map(AIRPORT_FEES).astype(float).round(2)
    f["nav_fees_usd"]     = (0.15 * f["distance_km"] * (f["seat_capacity"] / 100.0)).round(2)
    f["handling_cost_usd"] = (250 * (f["seat_capacity"] / 100.0)).round(2)
    f["total_operating_cost_usd"] = (
        f["fuel_cost_usd"] + f["crew_cost_usd"] + f["airport_fees_usd"]
        + f["nav_fees_usd"] + f["handling_cost_usd"]
    ).round(2)

    return f[[
        "flight_id", "fuel_cost_usd", "crew_cost_usd", "airport_fees_usd",
        "nav_fees_usd", "handling_cost_usd", "total_operating_cost_usd",
    ]]


# C’est une fonction qui génère les achats d’options additionnelles pour chaque réservation.

#  Ce qu’elle fait
#  .prend bookings, flights, routes et un générateur aléatoire rng
#  .associe chaque réservation à son route_type
#  .utilise ANCILLARY_CATALOG pour choisir des services additionnels (bagages, siège, repas, salon, priorité, upgrade)
#  .répartit la ancillary_revenue_usd de la réservation en 1 à 3 lignes de produits
#  .ajuste les prix pour que la somme des lignes corresponde à ancillary_revenue_usd

#  Résultat
#  Elle retourne un DataFrame avec ces colonnes :
#  .ancillary_purchase_id
#  .booking_id
#  .item_id
#  .item_type
#  .item_name
#  .quantity
#  .unit_price_usd
#  .total_price_usd

#  C’est la fonction qui construit le fichier ancillary_purchases.csv à partir des revenus accessoires déclarés dans les réservations.

def build_ancillary_purchases(bookings: pd.DataFrame, flights: pd.DataFrame,
                               routes: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """
    Decompose each booking's ancillary_revenue_usd into 0-3 line items
    drawn from the catalog, weighted by fare_family and route_type.
    """
    fr = flights[["flight_id", "route_id"]].merge(
        routes[["route_id", "route_type"]], on="route_id", how="left"
    )
    b = bookings.merge(fr[["flight_id", "route_type"]], on="flight_id", how="left")

    fam_weights = {
        # bag, seat, meal, lounge, priority, upgrade
        "Basic":    {"baggage": 0.55, "seat": 0.20, "meal": 0.10,
                     "lounge": 0.02, "priority": 0.10, "upgrade": 0.03},
        "Standard": {"baggage": 0.30, "seat": 0.25, "meal": 0.15,
                     "lounge": 0.10, "priority": 0.10, "upgrade": 0.10},
        "Flex":     {"baggage": 0.15, "seat": 0.20, "meal": 0.15,
                     "lounge": 0.25, "priority": 0.10, "upgrade": 0.15},
    }

    rows = []
    purchase_seq = 1
    for _, row in b.iterrows():
        target_amount = float(row["ancillary_revenue_usd"])
        if target_amount <= 0:
            continue

        candidates = ANCILLARY_CATALOG[
            ANCILLARY_CATALOG["applies_to_route_type"].str.contains(row["route_type"])
            | (ANCILLARY_CATALOG["applies_to_route_type"] == "ALL")
        ]

        weights = fam_weights.get(row["fare_family"], fam_weights["Standard"])
        # weight each catalog row by its item_type weight
        item_weights = candidates["item_type"].map(weights).fillna(0.05).values

        # decide how many items: 1-3, biased by amount
        n_items = 1 if target_amount < 25 else (2 if target_amount < 50 else 3)
        # try to pick items whose summed base_price is close to target
        # simple greedy: pick first item, then fill remaining
        remaining = target_amount
        picked = []
        for _ in range(n_items):
            if remaining < 5 or candidates.empty:
                break
            # filter candidates that could fit
            fit = candidates[candidates["base_price_usd"] <= remaining + 15]
            if fit.empty:
                fit = candidates
            w = fit["item_type"].map(weights).fillna(0.05).values
            if w.sum() == 0:
                break
            idx = rng.choices(range(len(fit)), weights=w, k=1)[0]
            item = fit.iloc[idx]
            picked.append(item)
            remaining -= item["base_price_usd"]

        if not picked:
            # fallback: pick cheapest item
            item = candidates.sort_values("base_price_usd").iloc[0]
            picked = [item]

        # scale prices so they sum to target_amount
        raw_sum = sum(p["base_price_usd"] for p in picked)
        scale = target_amount / raw_sum if raw_sum else 1.0
        for p in picked:
            unit = round(p["base_price_usd"] * scale, 2)
            rows.append({
                "ancillary_purchase_id": f"ANCP{purchase_seq:07d}",
                "booking_id":   row["booking_id"],
                "item_id":      p["item_id"],
                "item_type":    p["item_type"],
                "item_name":    p["item_name"],
                "quantity":     1,
                "unit_price_usd": unit,
                "total_price_usd": unit,
            })
            purchase_seq += 1

    return pd.DataFrame(rows)

#= C’est une fonction qui génère les transactions de fidélité pour les clients.

# Ce qu’elle fait
# .prend customers, bookings et un générateur aléatoire rng
# .sélectionne les clients qui ont un loyalty_tier valide (Explorer, Silver, Gold)
# .marque environ 20% de ces clients comme « dormants » (pas d’activité dans la période)
# .pour chaque réservation d’un client actif :
#   .avec 70% de probabilité, crée une transaction Earn
#   .le montant de miles est proportionnel au ticket_price_usd
#   .le bonus dépend du niveau de fidélité :
#     .Explorer = 1.0 × prix
#     .Silver = 1.25 × prix
#     .Gold = 1.5 × prix

# .quelques transactions Redeem pour environ 8% des clients fidèles non dormants
# .dates de transaction aléatoires dans la fenêtre définie
# .montants négatifs pour la dépense de miles
#Résultat
#Retourne un DataFrame avec ces colonnes :

# .loyalty_txn_id
# .customer_id
# .txn_date
# .txn_type (Earn ou Redeem)
# .miles_amount
# .related_booking_id
# .description
# C’est la base du fichier loyalty_transactions.csv.

def build_loyalty_transactions(customers: pd.DataFrame, bookings: pd.DataFrame,
                                rng: random.Random) -> pd.DataFrame:
    """
    Earn events on ~70% of bookings (for customers with a loyalty tier).
    Occasional Redeem events. ~20% of loyalty customers receive no activity
    in our window → dormant cohort for at-risk flagging.
    """
    tier_mult = {"Explorer": 1.0, "Silver": 1.25, "Gold": 1.5}
    loyal = customers[customers["loyalty_tier"].notna()
                      & (customers["loyalty_tier"] != "None")].copy()

    # mark dormant ~20%
    dormant_ids = set(rng.sample(loyal["customer_id"].tolist(),
                                  k=int(0.20 * len(loyal))))

    rows = []
    seq = 1
    for _, b in bookings.iterrows():
        cid = b["customer_id"]
        if cid not in loyal["customer_id"].values or cid in dormant_ids:
            continue
        if rng.random() > 0.70:
            continue
        tier = loyal.loc[loyal["customer_id"] == cid, "loyalty_tier"].iloc[0]
        mult = tier_mult.get(tier, 1.0)
        miles = int(round(float(b["ticket_price_usd"]) * mult))
        rows.append({
            "loyalty_txn_id":  f"LTX{seq:07d}",
            "customer_id":     cid,
            "txn_date":        b["booking_date"],
            "txn_type":        "Earn",
            "miles_amount":    miles,
            "related_booking_id": b["booking_id"],
            "description":     f"Miles earned from flight booking (tier={tier})",
        })
        seq += 1

    # add some Redeem events
    redeemers = rng.sample(
        [c for c in loyal["customer_id"].tolist() if c not in dormant_ids],
        k=int(0.08 * len(loyal)),
    )
    base_date = pd.to_datetime("2024-11-15")
    for cid in redeemers:
        n_redeems = rng.randint(1, 2)
        for _ in range(n_redeems):
            offset_days = rng.randint(0, 75)
            rows.append({
                "loyalty_txn_id":  f"LTX{seq:07d}",
                "customer_id":     cid,
                "txn_date":        (base_date + timedelta(days=offset_days)).date(),
                "txn_type":        "Redeem",
                "miles_amount":    -rng.choice([5000, 10000, 15000, 25000]),
                "related_booking_id": None,
                "description":     "Miles redeemed (lounge / upgrade / free flight)",
            })
            seq += 1

    return pd.DataFrame(rows)



#= C’est une fonction qui génère un journal des perturbations opérationnelles
#  pour les vols retardés ou annulés.

# Ce qu’elle fait
# .prend flights et un générateur aléatoire rng
# .sélectionne uniquement les vols ayant le statut :
#   .Delayed
#   .Cancelled
# .attribue une cause racine (root_cause) selon des probabilités pondérées :
#   .Weather
#   .Technical
#   .Crew
#   .ATC
#   .Ground_Handling
#   .Other
# .génère ensuite :
#   .une sous-cause (sub_cause)
#   .une description du problème
#   .une action de récupération (recovery_action)

# Exemples
# .Weather → Thunderstorm at origin
# .Technical → Aircraft change required
# .Crew → Pilot illness
# .ATC → Slot delay at CDG

# Résultat
# Retourne un DataFrame avec ces colonnes :
#
# .disruption_id
# .flight_id
# .root_cause
# .sub_cause
# .description
# .recovery_action
#
# C’est la base du fichier disruption_log.csv.

def build_disruption_log(flights: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """One disruption row per Delayed / Cancelled flight."""
    causes = [
        ("Weather",         ["Thunderstorm at origin", "Harmattan dust reducing visibility",
                              "Heavy rain at destination", "Crosswind exceeding limits"],
         ["Reschedule to next slot", "Held on stand", "Diverted briefly"], 0.25),
        ("Technical",       ["Minor maintenance finding", "APU replacement",
                              "Aircraft change required", "Tire change"],
         ["Aircraft swap", "Engineering hold", "Extended turnaround"], 0.30),
        ("Crew",            ["Cabin crew duty time exceeded", "Pilot illness",
                              "Crew positioning delay"],
         ["Reserve crew called", "Schedule re-plan"], 0.15),
        ("ATC",             ["Slot delay at CDG", "Lagos approach congestion",
                              "Abidjan ground hold"],
         ["Held on stand", "Reduced taxi speed"], 0.10),
        ("Ground_Handling", ["Late baggage loading", "Fuel truck delay",
                              "Catering uplift late", "Pushback tug breakdown"],
         ["Extended boarding", "Push delay accepted"], 0.15),
        ("Other",           ["Operational disruption", "Schedule recovery"],
         ["Accepted minor delay"], 0.05),
    ]
    labels   = [c[0] for c in causes]
    weights  = [c[3] for c in causes]
    sub_map  = {c[0]: c[1] for c in causes}
    rec_map  = {c[0]: c[2] for c in causes}

    disrupted = flights[flights["flight_status"].isin(["Delayed", "Cancelled"])]
    rows = []
    for i, f in disrupted.reset_index(drop=True).iterrows():
        root = rng.choices(labels, weights=weights, k=1)[0]
        rows.append({
            "disruption_id":  f"DSR{i+1:05d}",
            "flight_id":      f["flight_id"],
            "root_cause":     root,
            "sub_cause":      rng.choice(sub_map[root]),
            "description":    rng.choice(sub_map[root]),
            "recovery_action": rng.choice(rec_map[root]),
        })
    return pd.DataFrame(rows)


#== C'est une fonction qui génère les tickets de support client.
#
#  Ce qu'elle fait
#  .sélectionne environ 8% des clients de la base customers
#  .pour chaque client, génère 1-3 tickets d'assistance
#  .chaque ticket a une catégorie, un canal de contact, une sévérité et un statut
#
#  Répartition des catégories (par poids)
#  .Baggage = 35% (problèmes de bagages)
#  .Schedule_Change = 25% (modification de vol)
#  .Refund_Request = 15% (demande de remboursement)
#  .Loyalty = 10% (questions de fidélité)
#  .Booking_Issue = 10% (problèmes de réservation)
#  .Other = 5% (autres)
#
#  Canaux de contact (par poids)
#  .Email = 45%
#  .Phone = 30%
#  .Chat = 15%
#  .Social_Media = 10%
#
#  Sévérité par catégorie
#  .Baggage : Medium, Low, High (multiple options)
#  .Schedule_Change : Medium, High, Low
#  .Refund_Request : High, Medium
#  .Loyalty : Low, Medium
#  .Booking_Issue : Medium, High
#  .Other : Low, Medium
#
#  Temps de résolution
#  .Les tickets High sévérité sont traités en au moins 12 heures
#  .Les autres utilisent une distribution log-normale basée sur la sévérité
#  .90% des tickets sont fermés, 10% restent ouverts
#
#  Résultat
#  Le DataFrame contient ces colonnes :
#  .ticket_id
#  .customer_id
#  .related_booking_id
#  .related_flight_id
#  .open_date
#  .close_date (None si statut=Open)
#  .channel (Email, Phone, Chat, Social_Media)
#  .category (voir répartition ci-dessus)
#  .severity (Low, Medium, High)
#  .status (Closed ou Open)
#  .resolution_hours (en heures, None si Open)
#
#  C'est la base du fichier support_tickets.csv.
def build_support_tickets(customers: pd.DataFrame, bookings: pd.DataFrame,
                            flights: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """
    ~8% of customers raise at least one ticket. Category mix:
    Baggage 35%, Schedule_Change 25%, Refund_Request 15%, Loyalty 10%,
    Booking_Issue 10%, Other 5%.
    """
    categories = [
        ("Baggage",         0.35, ["Medium", "Medium", "Low", "High"]),
        ("Schedule_Change", 0.25, ["Medium", "High", "Low"]),
        ("Refund_Request",  0.15, ["High", "High", "Medium"]),
        ("Loyalty",         0.10, ["Low", "Medium"]),
        ("Booking_Issue",   0.10, ["Medium", "High"]),
        ("Other",           0.05, ["Low", "Medium"]),
    ]
    cat_names = [c[0] for c in categories]
    cat_w     = [c[1] for c in categories]
    cat_sev   = {c[0]: c[2] for c in categories}

    channels = ["Email", "Phone", "Chat", "Social_Media"]
    chan_w   = [0.45, 0.30, 0.15, 0.10]

    n_ticketing_cust = int(0.08 * len(customers))
    ticketing = rng.sample(customers["customer_id"].tolist(), k=n_ticketing_cust)

    rows = []
    seq = 1
    for cid in ticketing:
        cust_bk = bookings[bookings["customer_id"] == cid]
        n_tickets = rng.choices([1, 2, 3], weights=[0.65, 0.25, 0.10], k=1)[0]
        for _ in range(n_tickets):
            cat = rng.choices(cat_names, weights=cat_w, k=1)[0]
            sev = rng.choice(cat_sev[cat])
            channel = rng.choices(channels, weights=chan_w, k=1)[0]
            if len(cust_bk) > 0:
                bk = cust_bk.sample(1, random_state=rng.randint(0, 1_000_000)).iloc[0]
                related_bk = bk["booking_id"]
                related_flt = bk["flight_id"]
                base_open = pd.to_datetime(bk["booking_date"])
            else:
                related_bk = None
                related_flt = None
                base_open = pd.to_datetime("2024-12-01")
            open_dt = base_open + timedelta(days=rng.randint(1, 25))
            resolution_hours = max(0.5, round(rng.lognormvariate(2.0,
                                                {"Low": 0.5, "Medium": 0.8, "High": 1.0}[sev]), 1))
            if sev == "High":
                resolution_hours = max(resolution_hours, 12)
            close_dt = open_dt + timedelta(hours=resolution_hours)
            status = "Closed" if rng.random() < 0.90 else "Open"
            rows.append({
                "ticket_id":          f"TKT{seq:06d}",
                "customer_id":        cid,
                "related_booking_id": related_bk,
                "related_flight_id":  related_flt,
                "open_date":          open_dt.date(),
                "close_date":         close_dt.date() if status == "Closed" else None,
                "channel":            channel,
                "category":           cat,
                "severity":           sev,
                "status":             status,
                "resolution_hours":   resolution_hours if status == "Closed" else None,
            })
            seq += 1
    return pd.DataFrame(rows)


# ============================================================
# 4. Customer reviews — the unstructured source
# ============================================================

REVIEW_TEMPLATES = {
    # topic -> (positive_sentences, negative_sentences)
    "punctuality": (
        ["Departed and arrived on time.", "Smooth and punctual flight, no fuss.",
         "Right on schedule, exactly what I needed.",
         "Boarded and pushed back early — great work."],
        ["Significant delay with poor communication.",
         "Boarding announced late and we sat on the apron for ages.",
         "Departed over an hour late and I missed my connection.",
         "The delay was very disruptive to my schedule."],
    ),
    "cabin_comfort": (
        ["Seat was comfortable for the route length.",
         "Cabin was modern and pleasant.", "Newer aircraft made a real difference.",
         "Plenty of legroom in this cabin."],
        ["Seat was cramped and uncomfortable.",
         "Cabin felt tired and the seat padding was thin.",
         "Recline didn't work properly.",
         "Hard to sleep, seat was not ideal for a long flight."],
    ),
    "food_beverage": (
        ["Meal was tasty and well presented.",
         "Good beverage selection on board.",
         "Enjoyed the local menu options.",
         "Snack service was a nice touch."],
        ["Meal was disappointing, especially for a long-haul flight.",
         "Food quality below other African carriers.",
         "Drinks options were very limited.",
         "Cold meal when it should have been warm."],
    ),
    "staff_service": (
        ["Cabin crew were friendly and professional.",
         "Staff went out of their way to help.",
         "Crew handled a tough situation with patience.",
         "Attentive service from boarding to landing."],
        ["Staff were unhelpful when I asked questions.",
         "Crew seemed rushed and impatient.",
         "Customer service was indifferent.",
         "Felt ignored by the cabin crew during the flight."],
    ),
    "cleanliness": (
        ["Cabin was clean and well prepared.",
         "Lavatories were kept tidy throughout the flight."],
        ["Cabin needed a deeper clean before boarding.",
         "Lavatories were dirty by mid-flight."],
    ),
    "baggage": (
        ["Bags arrived quickly at the carousel.",
         "Baggage handling was efficient on arrival."],
        ["Long wait for bags at the carousel.",
         "My luggage was damaged on arrival.",
         "One bag arrived on a later flight — frustrating."],
    ),
    "value_for_money": (
        ["Good value for the price paid.",
         "Reasonable fare for the route."],
        ["Felt overpriced for what was offered.",
         "Would not pay this fare again given the experience."],
    ),
    "boarding": (
        ["Boarding was orderly and quick.",
         "Priority boarding worked smoothly."],
        ["Chaotic boarding process at the gate.",
         "Boarding was very slow and disorganized."],
    ),
    "entertainment": (
        ["Good selection of entertainment for a long-haul flight.",
         "IFE worked well throughout the flight."],
        ["Entertainment system was unreliable.",
         "Very limited content for such a long flight."],
    ),
    "communication": (
        ["Crew kept us informed throughout the flight.",
         "Clear announcements from the flight deck."],
        ["No communication during the delay — very frustrating.",
         "We were left guessing what was happening.",
         "Information from staff was inconsistent."],
    ),
}

#== Cette fonction sélectionne les sujets (topics) à inclure dans un avis client.
#
#  Ce qu'elle fait
#  .choisit 1-3 thèmes selon le rating et le type de route
#  .pondère le choix des thèmes selon la note (rating)
#  .adapte les thèmes disponibles au type de route (Domestic, Regional, International)
#
#  Thèmes disponibles par route_type
#  .Domestic : punctuality, staff_service, value_for_money, cleanliness, boarding, baggage
#  .Regional : punctuality, staff_service, cabin_comfort, food_beverage, boarding, communication, value_for_money, baggage
#  .International : cabin_comfort, food_beverage, staff_service, entertainment, communication, punctuality, baggage
#
#  Logique de pondération (by_rating)
#  .rating <= 2 (avis négatif)
#    .punctuality = 3.0, communication = 2.0, cabin_comfort = 1.5, etc.
#    .favorise les thèmes de plainte (retards, communication, confort)
#  .rating == 3 (neutre/mitigé)
#    .tous les thèmes poids égal = 1.0
#  .rating >= 4 (avis positif)
#    .staff_service = 2.0, cabin_comfort = 1.5, punctuality = 1.5, etc.
#    .favorise les thèmes de satisfaction
#
#  Nombre de thèmes
#  .1 thème = 25% de probabilité
#  .2 thèmes = 50%
#  .3 thèmes = 25%
#
#  Résultat
#  Retourne une liste de 1-3 chaînes (topics) choisies aléatoirement
def pick_topics(rating: int, route_type: str, rng: random.Random) -> list[str]:
    """Choose 1-3 topics. Low ratings cluster around problem areas."""
    long_haul_only = {"entertainment"}
    if route_type == "Domestic":
        pool = ["punctuality", "staff_service", "value_for_money", "cleanliness",
                "boarding", "baggage"]
    elif route_type == "Regional":
        pool = ["punctuality", "staff_service", "cabin_comfort", "food_beverage",
                "boarding", "communication", "value_for_money", "baggage"]
    else:  # International
        pool = ["cabin_comfort", "food_beverage", "staff_service", "entertainment",
                "communication", "punctuality", "baggage"]

    # negative ratings → bias toward complaint-heavy topics
    if rating <= 2:
        weight_pool = {
            "punctuality":     3.0,
            "communication":   2.0,
            "cabin_comfort":   1.5,
            "food_beverage":   1.5,
            "baggage":         1.5,
            "staff_service":   1.5,
            "value_for_money": 1.0,
            "boarding":        1.0,
            "cleanliness":     1.0,
            "entertainment":   1.0,
        }
    elif rating == 3:
        weight_pool = {k: 1.0 for k in REVIEW_TEMPLATES.keys()}
    else:
        weight_pool = {
            "staff_service":   2.0,
            "cabin_comfort":   1.5,
            "punctuality":     1.5,
            "food_beverage":   1.0,
            "boarding":        1.0,
            "value_for_money": 1.0,
            "cleanliness":     0.8,
            "communication":   0.8,
            "baggage":         0.8,
            "entertainment":   1.0,
        }

    weights = [weight_pool.get(t, 0.5) for t in pool]
    n = rng.choices([1, 2, 3], weights=[0.25, 0.50, 0.25], k=1)[0]
    chosen = []
    available = list(pool)
    avail_w = list(weights)
    for _ in range(min(n, len(available))):
        idx = rng.choices(range(len(available)), weights=avail_w, k=1)[0]
        chosen.append(available.pop(idx))
        avail_w.pop(idx)
    return chosen


#== Cette fonction compose le texte d'un avis client à partir des thèmes et de la note.
#
#  Ce qu'elle fait
#  .génère une liste de phrases à partir des topics fournis
#  .sélectionne des phrases positives ou négatives selon le rating
#  .ajoute une phrase de conclusion cohérente avec le rating
#
#  Logique de sélection des phrases
#  Pour chaque thème (topic) :
#    .rating >= 4 (avis positif) : sélectionne une phrase positive du template
#    .rating <= 2 (avis négatif) : sélectionne une phrase négative du template
#    .rating == 3 (mitigé) : 55% de chance pour négatif, 45% pour positif
#
#  Phrase de conclusion (par rating)
#  .rating == 5 : "Would fly again.", "Great experience overall.", etc.
#  .rating == 1 : "Will avoid this airline next time.", "Very disappointing.", etc.
#  .rating 2-4 : pas de conclusion spéciale
#
#  Source des phrases
#  Les phrases positives et négatives viennent du dictionnaire REVIEW_TEMPLATES,
#  qui définit pour chaque topic une liste de phrases positives et négatives
#
#  Résultat
#  Retourne une chaîne de texte composée de 2-4 phrases (topics + conclusion)
#  Les phrases sont séparées par un espace et forment un compte-rendu complet
def compose_review(rating: int, topics: list[str], rng: random.Random) -> str:
    """Compose review text by blending topic sentences. Positive vs negative
    selection depends on rating."""
    sentences = []
    for topic in topics:
        pos, neg = REVIEW_TEMPLATES[topic]
        if rating >= 4:
            sentences.append(rng.choice(pos))
        elif rating <= 2:
            sentences.append(rng.choice(neg))
        else:  # rating == 3, mixed
            if rng.random() < 0.55:
                sentences.append(rng.choice(neg))
            else:
                sentences.append(rng.choice(pos))
    # add a closing line
    if rating == 5:
        sentences.append(rng.choice([
            "Would fly again.", "Great experience overall.",
            "Highly recommend this airline."]))
    elif rating == 1:
        sentences.append(rng.choice([
            "Will avoid this airline next time.",
            "Very disappointing experience.",
            "Hope they take this feedback seriously."]))
    return " ".join(sentences)



#= C’est une fonction qui génère des avis clients synthétiques
#  à partir des réservations et des vols effectués.

# Ce qu’elle fait
# .prend bookings, flights, routes et un générateur rng
# .sélectionne uniquement les réservations avec :
#   .booking_status == "Flown"
#
# .enrichit les données avec :
#   .flight_status
#   .flight_date
#   .route_type
#
# .environ 35% des vols reçoivent un avis client
#
# .génère une note (rating) conditionnée par :
#   .le statut du vol
#   .la classe tarifaire
#
# Règles générales :
# .Cancelled → très mauvaises notes
# .Delayed → notes moyennes/basses
# .Business → meilleures notes
# .Premium Economy → bonnes notes
# .Economy → notes normales
#
# .utilise ensuite :
#   .pick_topics() pour choisir les thèmes
#   .compose_review() pour créer le texte
#
# .génère enfin :
#   .une date d’avis
#   .une langue
#   .une liste de thèmes

# Résultat
# Retourne un DataFrame avec ces colonnes :
#
# .review_id
# .booking_id
# .customer_id
# .flight_id
# .review_date
# .rating
# .review_text
# .language
# .topics
#
# C’est la base du fichier customer_reviews.csv.
#
# Ce dataset représente la source non structurée principale
# du projet pour les analyses NLP / sentiment analysis.
def build_customer_reviews(bookings: pd.DataFrame, flights: pd.DataFrame,
                            routes: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """
    ~35% of Flown bookings get a review. Rating conditioned on flight
    outcome and fare class. Topics conditioned on rating and route_type.
    """
    flown = bookings[bookings["booking_status"] == "Flown"].copy()
    enriched = flown.merge(
        flights[["flight_id", "flight_status", "flight_date", "route_id"]],
        on="flight_id", how="left",
    ).merge(routes[["route_id", "route_type"]], on="route_id", how="left")

    rows = []
    seq = 1
    for _, b in enriched.iterrows():
        if rng.random() > 0.35:
            continue
        # rating: conditioned on flight_status + fare_class
        if b["flight_status"] == "Cancelled":
            mean, std = 1.8, 0.8
        elif b["flight_status"] == "Delayed":
            mean, std = 2.5, 1.0
        elif b["fare_class"] == "Business":
            mean, std = 4.2, 0.7
        elif b["fare_class"] == "Premium Economy":
            mean, std = 4.0, 0.8
        else:  # Economy on-time
            mean, std = 3.8, 0.9
        rating_raw = np.random.normal(mean, std)
        rating = int(np.clip(round(rating_raw), 1, 5))

        topics = pick_topics(rating, b["route_type"], rng)
        text = compose_review(rating, topics, rng)

        review_date = pd.to_datetime(b["flight_date"]) + timedelta(
            days=rng.randint(1, 14))
        rows.append({
            "review_id":    f"RVW{seq:06d}",
            "booking_id":   b["booking_id"],
            "customer_id":  b["customer_id"],
            "flight_id":    b["flight_id"],
            "review_date":  review_date.date(),
            "rating":       rating,
            "review_text":  text,
            "language":     "en",
            "topics":       ";".join(topics),
        })
        seq += 1
    return pd.DataFrame(rows)


# ============================================================
# 5. Orchestration
# ============================================================

# ============================================================
# 5. Orchestration
# ============================================================

#= Fonction principale du script.
#
# Ce qu’elle fait
# .lit les arguments de ligne de commande :
#   .--starter → fichier Excel source
#   .--out-dir → dossier de sortie
#
# .initialise les graines aléatoires avec SEED=42
#   pour garantir une génération déterministe
#
# .charge les feuilles du fichier starter :
#   .Airports
#   .Routes
#   .Customers
#   .Flights
#   .Bookings
#
# .génère ensuite tous les datasets synthétiques :
#   .aircraft_fleet
#   .fuel_prices_monthly
#   .ancillary_catalog
#   .route_operating_costs
#   .ancillary_purchases
#   .loyalty_transactions
#   .disruption_log
#   .support_tickets
#   .customer_reviews
#
# .exporte chaque dataset au format CSV
#
# .crée également un fichier Excel consolidé :
#   .enriched_dataset.xlsx
#
# Ce fichier contient :
#   .les datasets de départ
#   .les datasets synthétiques
#
# .affiche enfin un résumé statistique :
#   .nombre de lignes générées
#   .distribution des notes clients
#   .principaux sujets de plainte
#
# Cette fonction orchestre donc l’intégralité
# du pipeline de génération de données synthétiques.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--starter", required=True,
                        help="Path to starter xlsx")
    parser.add_argument("--out-dir", required=True,
                        help="Output directory for CSVs and combined xlsx")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Deterministic seeds for ALL randomness
    random.seed(SEED)
    np.random.seed(SEED)
    rng = random.Random(SEED)

    print(f"[1/9] Loading starter from {args.starter} ...")
    airports  = pd.read_excel(args.starter, sheet_name="Airports")
    routes    = pd.read_excel(args.starter, sheet_name="Routes")
    customers = pd.read_excel(args.starter, sheet_name="Customers")
    flights   = pd.read_excel(args.starter, sheet_name="Flights")
    bookings  = pd.read_excel(args.starter, sheet_name="Bookings")

    print("[2/9] Aircraft fleet (static reference) ...")
    AIRCRAFT_FLEET.to_csv(out_dir / "aircraft_fleet.csv", index=False)

    print("[3/9] Fuel prices monthly (static reference) ...")
    FUEL_PRICES.to_csv(out_dir / "fuel_prices_monthly.csv", index=False)

    print("[4/9] Ancillary catalog (static reference) ...")
    ANCILLARY_CATALOG.to_csv(out_dir / "ancillary_catalog.csv", index=False)

    print("[5/9] Route operating costs (per flight) ...")
    costs = build_route_operating_costs(flights, routes)
    costs.to_csv(out_dir / "route_operating_costs.csv", index=False)

    print("[6/9] Ancillary purchases (per booking decomposition) ...")
    anc_purch = build_ancillary_purchases(bookings, flights, routes, rng)
    anc_purch.to_csv(out_dir / "ancillary_purchases.csv", index=False)

    print("[7/9] Loyalty transactions ...")
    loyalty = build_loyalty_transactions(customers, bookings, rng)
    loyalty.to_csv(out_dir / "loyalty_transactions.csv", index=False)

    print("[8/9] Disruption log (delayed / cancelled flights) ...")
    disruption = build_disruption_log(flights, rng)
    disruption.to_csv(out_dir / "disruption_log.csv", index=False)

    print("[9/9] Support tickets ...")
    tickets = build_support_tickets(customers, bookings, flights, rng)
    tickets.to_csv(out_dir / "support_tickets.csv", index=False)

    print("[+]   Customer reviews (unstructured, the key dataset) ...")
    reviews = build_customer_reviews(bookings, flights, routes, rng)
    reviews.to_csv(out_dir / "customer_reviews.csv", index=False)

    # Combined Excel — all sheets in one file for convenience
    combined_xlsx = out_dir / "enriched_dataset.xlsx"
    print(f"[+]   Writing combined Excel → {combined_xlsx}")
    with pd.ExcelWriter(combined_xlsx, engine="openpyxl") as xw:
        # Starter sheets first
        airports.to_excel(xw,  sheet_name="Airports",   index=False)
        routes.to_excel(xw,    sheet_name="Routes",     index=False)
        customers.to_excel(xw, sheet_name="Customers",  index=False)
        flights.to_excel(xw,   sheet_name="Flights",    index=False)
        bookings.to_excel(xw,  sheet_name="Bookings",   index=False)
        # Synthetic sheets
        AIRCRAFT_FLEET.to_excel(xw,    sheet_name="Aircraft_Fleet", index=False)
        FUEL_PRICES.to_excel(xw,       sheet_name="Fuel_Prices",    index=False)
        ANCILLARY_CATALOG.to_excel(xw, sheet_name="Ancillary_Catalog", index=False)
        costs.to_excel(xw,    sheet_name="Route_Operating_Costs", index=False)
        anc_purch.to_excel(xw,sheet_name="Ancillary_Purchases", index=False)
        loyalty.to_excel(xw,  sheet_name="Loyalty_Txn", index=False)
        disruption.to_excel(xw, sheet_name="Disruption_Log", index=False)
        tickets.to_excel(xw,  sheet_name="Support_Tickets", index=False)
        reviews.to_excel(xw,  sheet_name="Customer_Reviews", index=False)

    # Summary
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)
    print(f"  Aircraft fleet:        {len(AIRCRAFT_FLEET):>6} rows")
    print(f"  Fuel prices:           {len(FUEL_PRICES):>6} rows")
    print(f"  Ancillary catalog:     {len(ANCILLARY_CATALOG):>6} rows")
    print(f"  Route operating costs: {len(costs):>6} rows (per flight)")
    print(f"  Ancillary purchases:   {len(anc_purch):>6} rows")
    print(f"  Loyalty transactions:  {len(loyalty):>6} rows")
    print(f"  Disruption log:        {len(disruption):>6} rows")
    print(f"  Support tickets:       {len(tickets):>6} rows")
    print(f"  Customer reviews:      {len(reviews):>6} rows (UNSTRUCTURED)")
    print()
    print(f"  Review rating distribution: ")
    print(reviews["rating"].value_counts().sort_index().to_string())
    print()
    print(f"  Top complaint topics (rating <= 2):")
    neg = reviews[reviews["rating"] <= 2]
    topic_counts = {}
    for t_list in neg["topics"]:
        for t in t_list.split(";"):
            topic_counts[t] = topic_counts.get(t, 0) + 1
    for t, c in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"    {t:20s} {c}")


if __name__ == "__main__":
    main()
