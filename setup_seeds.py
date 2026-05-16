"""
setup_seeds.py
==============
Prépare le dossier dbt_project/seeds/ en une seule commande :
  1. Copie les CSVs synthétiques depuis data/synthetic/
  2. Exporte les 5 sheets du starter Excel en CSV

Usage (depuis la racine du projet airci_challenge/) :
    python setup_seeds.py
    python setup_seeds.py --starter data/starter/air_cote_divoire_starter_dataset.xlsx
    python setup_seeds.py --synthetic data/synthetic/ --seeds dbt_project/seeds/
"""

import argparse
import shutil
from pathlib import Path
import pandas as pd

SYNTHETIC_SHEETS = [
    ("Airports",  "airports"),
    ("Routes",    "routes"),
    ("Customers", "customers"),
    ("Flights",   "flights"),
    ("Bookings",  "bookings"),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--starter",   default="/mnt/project/air_cote_divoire_starter_dataset.xlsx")
    parser.add_argument("--synthetic", default="data/synthetic")
    parser.add_argument("--seeds",     default="dbt_project/seeds")
    args = parser.parse_args()

    seeds_dir    = Path(args.seeds)
    synthetic_dir = Path(args.synthetic)
    seeds_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copier les CSVs synthétiques
    print("1/2  Copie des CSVs synthétiques...")
    copied = 0
    for csv_file in sorted(synthetic_dir.glob("*.csv")):
        dest = seeds_dir / csv_file.name
        shutil.copy2(csv_file, dest)
        print(f"  ✓  {csv_file.name}")
        copied += 1
    if copied == 0:
        print(f"  ⚠  Aucun CSV trouvé dans {synthetic_dir}")
        print(f"     Lance d'abord : python scripts/generate_synthetic_data.py --starter {args.starter} --out-dir {args.synthetic}")

    # 2. Exporter les 5 sheets du starter en CSV
    print(f"\n2/2  Export du starter Excel → CSV ({args.starter})...")
    for sheet, csv_name in SYNTHETIC_SHEETS:
        df = pd.read_excel(args.starter, sheet_name=sheet)
        # Normalise les dates en ISO string (DuckDB les lit correctement)
        for col in df.columns:
            if "date" in col.lower():
                df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d")
        out = seeds_dir / f"{csv_name}.csv"
        df.to_csv(out, index=False)
        print(f"  ✓  {csv_name}.csv  ({len(df)} lignes)")

    print(f"\n✅  Seeds prêts dans {seeds_dir}/")
    print(f"   Total fichiers : {len(list(seeds_dir.glob('*.csv')))}")
    print("\nTu peux maintenant lancer :")
    print("  cd dbt_project")
    print("  export DBT_PROFILES_DIR=.")
    print("  dbt seed && dbt run && dbt test")

if __name__ == "__main__":
    main()
