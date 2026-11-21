"""Dish + portion -> nutrients, using the table built from INDB (scripts/build_nutrition.py)."""
import json
from pathlib import Path

MODELS = Path(__file__).resolve().parent.parent / "models"


def pretty(dish: str) -> str:
    return dish.replace("_", " ").title().replace("Kaathi Rolls", "Kaathi Roll").replace("Paani Puri", "Paani Puri")


class NutritionTable:
    def __init__(self, models_dir: Path = MODELS):
        data = json.loads((models_dir / "nutrition.json").read_text(encoding="utf-8"))
        self.source = data["source"]
        self.nutrients = data["nutrients"]
        self.dishes = data["dishes"]

    def lookup(self, dish: str, grams: float | None = None) -> dict:
        info = self.dishes.get(dish)
        if info is None:
            raise KeyError(dish)
        out = {"dish": dish, "name": pretty(dish), "status": info["status"], "note": info.get("note", "")}
        if info["status"] != "ok":
            return out
        grams = float(grams or info["serving"]["grams"])
        values = []
        for key, meta in self.nutrients.items():
            per100 = info["per_100g"][key]
            values.append({"key": key, **meta,
                           "amount": None if per100 is None else round(per100 * grams / 100, 2)})
        out.update(grams=round(grams), serving=info["serving"], indb_recipes=info["indb_recipes"],
                   nutrients=values, source=self.source)
        return out
