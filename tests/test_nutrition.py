"""Nutrition table tests (no image model needed)."""
from nutriscan.nutrition import NutritionTable

table = NutritionTable()


def test_twenty_dishes_with_a_status():
    assert len(table.dishes) == 20
    assert {d["status"] for d in table.dishes.values()} <= {"ok", "unreliable", "missing"}


def test_values_scale_with_portion():
    a = {n["key"]: n["amount"] for n in table.lookup("idli", 100)["nutrients"]}
    b = {n["key"]: n["amount"] for n in table.lookup("idli", 200)["nutrients"]}
    assert abs(b["energy_kcal"] - 2 * a["energy_kcal"]) < 0.05


def test_fried_dishes_are_hidden():
    for dish in ["samosa", "pakode", "chole_bhature", "burger"]:
        out = table.lookup(dish)
        assert out["status"] == "unreliable" and "nutrients" not in out


def test_energy_roughly_matches_macros():
    """Sanity check on the source data: 4 kcal/g protein and carbs, 9 kcal/g fat."""
    for dish, info in table.dishes.items():
        if info["status"] != "ok":
            continue
        p = info["per_100g"]
        estimate = 4 * p["protein_g"] + 4 * p["carb_g"] + 9 * p["fat_g"]
        assert abs(estimate - p["energy_kcal"]) / p["energy_kcal"] < 0.25, dish
