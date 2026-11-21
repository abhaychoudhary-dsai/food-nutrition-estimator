"""API tests. Skipped until the trained model files are in models/."""
import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

MODELS = Path(__file__).resolve().parent.parent / "models"
pytestmark = pytest.mark.skipif(not (MODELS / "food_classifier.onnx").exists(), reason="model not trained yet")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from nutriscan.api import app
    return TestClient(app)


def jpeg(w=640, h=480):
    buf = io.BytesIO()
    Image.fromarray(np.random.default_rng(0).integers(0, 255, (h, w, 3), dtype=np.uint8)).save(buf, "JPEG")
    return buf.getvalue()


def test_preprocess_shape():
    from nutriscan.model import preprocess
    x = preprocess(Image.new("RGB", (1000, 300)))
    assert x.shape == (1, 3, 224, 224)


def test_analyze_returns_three_ranked_guesses(client):
    r = client.post("/api/analyze", files={"image": ("food.jpg", jpeg(), "image/jpeg")})
    assert r.status_code == 200
    preds = r.json()["predictions"]
    assert len(preds) == 3 and preds[0]["confidence"] >= preds[1]["confidence"] >= preds[2]["confidence"]


def test_non_image_is_rejected(client):
    r = client.post("/api/analyze", files={"image": ("x.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400


def test_unknown_dish_404(client):
    assert client.get("/api/nutrition/biryani").status_code == 404
