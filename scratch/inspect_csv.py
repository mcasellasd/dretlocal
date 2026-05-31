import csv
from collections import Counter

nom_ens_counter = Counter()
total_rows = 0
vigent_counter = Counter()

with open("Ordenances_cerdanya_complet.csv", "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        total_rows += 1
        nom_ens = row.get("NOM_ENS", "").strip()
        vigent = row.get("VIGENT", "").strip()
        nom_ens_counter[nom_ens] += 1
        vigent_counter[vigent] += 1
        
        if total_rows <= 3:
            print(f"Row {total_rows}: {dict(row)}")

print(f"\nTotal rows in CSV: {total_rows}")
print("\n--- Rows per NOM_ENS (top 20) ---")
for nom, count in nom_ens_counter.most_common(20):
    print(f"  {nom}: {count}")

print("\n--- VIGENT counts ---")
print(vigent_counter)
