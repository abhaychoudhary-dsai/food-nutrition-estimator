"""Image -> dish. Runs the ONNX export of the fine-tuned EfficientNet-B0 with onnxruntime."""
import io
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

MODELS = Path(__file__).resolve().parent.parent / "models"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(img: Image.Image) -> np.ndarray:
    """Same steps as the evaluation transform in training: resize 256, centre crop 224, normalise."""
    img = ImageOps.exif_transpose(img).convert("RGB")      # phone photos are often stored rotated
    w, h = img.size
    scale = 256 / min(w, h)
    img = img.resize((max(224, round(w * scale)), max(224, round(h * scale))), Image.BILINEAR)
    w, h = img.size
    left, top = (w - 224) // 2, (h - 224) // 2
    img = img.crop((left, top, left + 224, top + 224))
    x = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
    return x.transpose(2, 0, 1)[None]                         # HWC -> 1xCxHxW


class FoodClassifier:
    def __init__(self, models_dir: Path = MODELS):
        self.session = ort.InferenceSession(str(models_dir / "food_classifier.onnx"), providers=["CPUExecutionProvider"])
        self.labels = json.loads((models_dir / "labels.json").read_text())

    def predict(self, image_bytes: bytes, top_k: int = 3):
        img = Image.open(io.BytesIO(image_bytes))
        logits = self.session.run(None, {"image": preprocess(img)})[0][0]
        probs = np.exp(logits - logits.max())
        probs /= probs.sum()
        order = np.argsort(-probs)[:top_k]
        return [{"dish": self.labels[i], "confidence": round(float(probs[i]), 4)} for i in order]
