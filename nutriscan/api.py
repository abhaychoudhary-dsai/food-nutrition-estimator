"""FastAPI app. Run locally with:  uvicorn nutriscan.api:app --reload"""
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import UnidentifiedImageError

from .model import MODELS, FoodClassifier
from .nutrition import NutritionTable, pretty

STATIC = Path(__file__).resolve().parent.parent / "static"
MAX_BYTES = 8 * 1024 * 1024
LOW_CONFIDENCE = 0.5

app = FastAPI(title="NutriScan", description="Recognise an Indian dish from a photo and estimate its nutrition.",
              version="1.0")
classifier = FoodClassifier()
table = NutritionTable()


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze(image: UploadFile = File(...)):
    data = await image.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image is larger than 8 MB")
    try:
        top = classifier.predict(data)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "That file is not an image we can read (use JPG, PNG or WebP)")
    for t in top:
        t["name"] = pretty(t["dish"])
    best = top[0]
    return {"predictions": top, "low_confidence": best["confidence"] < LOW_CONFIDENCE,
            "nutrition": table.lookup(best["dish"])}


@app.get("/api/nutrition/{dish}")
def nutrition(dish: str, grams: float | None = Query(None, gt=0, le=2000)):
    try:
        return table.lookup(dish, grams)
    except KeyError:
        raise HTTPException(404, "Unknown dish")


@app.get("/api/dishes")
def dishes():
    return [{"dish": d, "name": pretty(d), "status": v["status"]} for d, v in table.dishes.items()]


@app.get("/api/model")
def model_info():
    return json.loads((MODELS / "metrics.json").read_text())


app.mount("/static", StaticFiles(directory=STATIC), name="static")
