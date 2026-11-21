"""Build models/nutrition.json from the Indian Nutrient Databank (INDB).

INDB (Jaacks et al., 2024) is open access:
https://github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-

Usage:
    python scripts/build_nutrition.py path/to/INDB.xlsx

Each of the 20 dishes the image model knows is matched to one INDB recipe
(or two, for chole bhature). Values are stored per 100 g and per serving.

Data check: for deep-fried dishes INDB counts all the oil in the recipe,
including oil left in the pan, so fat and calories come out far too high
(e.g. samosa 59 g fat per 100 g). Any recipe above 40 g fat per 100 g is
marked as unreliable and the app does not show its numbers.
"""
import json
import sys
from pathlib import Path

import pandas as pd

DISHES = {   # image class -> list of (INDB food_name, servings)
    "burger": [("Vegetable burger", 1)],
    "butter_naan": [("Naan", 1)],
    "chai": [("Hot tea (Garam Chai)", 1)],
    "chapati": [("Chapati/Roti", 1)],
    "chole_bhature": [("Chickpeas curry (Safed channa curry)", 1), ("Bhatura", 2)],
    "dal_makhani": [("Dal makhani", 1)],
    "dhokla": [("Dhokla", 1)],
    "fried_rice": [("Chinese fried rice", 1)],
    "idli": [("Idli", 1)],
    "jalebi": [],
    "kaathi_rolls": [("Paneer kaathi roll", 1)],
    "kadai_paneer": [("Kadhai Paneer", 1)],
    "kulfi": [("Kulfi", 1)],
    "masala_dosa": [("Masala dosa", 1)],
    "momos": [],
    "paani_puri": [],
    "pakode": [("Mixed vegetable pakora/pakoda", 1)],
    "pav_bhaji": [("Pav bhaji", 1)],
    "pizza": [("Pizza", 1)],
    "samosa": [("Potato samosa (Aloo ka samosa)", 1)],
}

NUTRIENTS = {   # INDB column -> (label, unit, group)
    "energy_kcal": ("Energy", "kcal", "main"), "protein_g": ("Protein", "g", "main"),
    "carb_g": ("Carbohydrates", "g", "main"), "fat_g": ("Fat", "g", "main"),
    "fibre_g": ("Fibre", "g", "main"), "freesugar_g": ("Free sugar", "g", "main"),
    "calcium_mg": ("Calcium", "mg", "mineral"), "iron_mg": ("Iron", "mg", "mineral"),
    "magnesium_mg": ("Magnesium", "mg", "mineral"), "phosphorus_mg": ("Phosphorus", "mg", "mineral"),
    "potassium_mg": ("Potassium", "mg", "mineral"), "sodium_mg": ("Sodium", "mg", "mineral"),
    "zinc_mg": ("Zinc", "mg", "mineral"),
    "vita_ug": ("Vitamin A", "µg", "vitamin"), "vitb1_mg": ("Vitamin B1 (thiamine)", "mg", "vitamin"),
    "vitb2_mg": ("Vitamin B2 (riboflavin)", "mg", "vitamin"), "vitb3_mg": ("Vitamin B3 (niacin)", "mg", "vitamin"),
    "vitb6_mg": ("Vitamin B6", "mg", "vitamin"), "folate_ug": ("Folate", "µg", "vitamin"),
    "vitc_mg": ("Vitamin C", "mg", "vitamin"), "vite_mg": ("Vitamin E", "mg", "vitamin"),
    "vitk1_ug": ("Vitamin K1", "µg", "vitamin"),
}
FAT_LIMIT = 40   # g per 100 g


def main(path):
    indb = pd.read_excel(path).set_index("food_name")
    out = {"source": "Indian Nutrient Databank (INDB), Jaacks et al. 2024", "nutrients": {
        k: {"label": v[0], "unit": v[1], "group": v[2]} for k, v in NUTRIENTS.items()}, "dishes": {}}
    for dish, parts in DISHES.items():
        if not parts:
            out["dishes"][dish] = {"status": "missing", "note": "This dish is not in INDB yet."}
            continue
        total_g, totals, names, too_fatty = 0.0, {k: 0.0 for k in NUTRIENTS}, [], []
        measured = {k: False for k in NUTRIENTS}   # blank in INDB = not measured, not zero
        for name, n in parts:
            row = indb.loc[name]
            grams = float(row["unit_serving_energy_kcal"] / row["energy_kcal"] * 100) * n
            total_g += grams
            for k in NUTRIENTS:
                if pd.notna(row[k]):
                    totals[k] += float(row[k]) * grams / 100
                    measured[k] = True
            names.append(f"{name} x{n}" if n > 1 else name)
            if row["fat_g"] > FAT_LIMIT:
                too_fatty.append(f"{name}: {row['fat_g']:.0f} g fat per 100 g")
        unit = parts[0][0] if len(parts) == 1 else "plate"
        serving_unit = str(indb.loc[parts[0][0], "servings_unit"]) if len(parts) == 1 else "plate (1 bowl chole + 2 bhature)"
        out["dishes"][dish] = {
            "status": "unreliable" if too_fatty else "ok",
            "note": ("INDB counts all the frying oil in the recipe, so fat and calories are far too high ("
                     + "; ".join(too_fatty) + "). Numbers are hidden.") if too_fatty else "",
            "indb_recipes": names,
            "serving": {"unit": serving_unit if serving_unit != "nan" else "plate", "grams": round(total_g)},
            "per_100g": {k: round(v / total_g * 100, 3) if measured[k] else None for k, v in totals.items()},
        }
    Path("models").mkdir(exist_ok=True)
    Path("models/nutrition.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    ok = [d for d, v in out["dishes"].items() if v["status"] == "ok"]
    print(f"{len(ok)} dishes with nutrition, "
          f"{sum(v['status'] == 'unreliable' for v in out['dishes'].values())} unreliable, "
          f"{sum(v['status'] == 'missing' for v in out['dishes'].values())} missing")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "INDB.xlsx")
