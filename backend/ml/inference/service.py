from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=8)
def load_model(name: str) -> dict:
    path = ROOT / "models" / f"{name}_v1.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Model artifact {path.name} is unavailable. Run python -m ml.training.train_models.")
    return joblib.load(path)


def predict(name: str, values: dict) -> float:
    artifact = load_model(name)
    frame = pd.DataFrame([[values[key] for key in artifact["features"]]], columns=artifact["features"])
    model = artifact["model"]
    if hasattr(model, "predict_proba"):
        return float(model.predict_proba(frame)[0][1])
    return float(model.predict(frame)[0])


def metadata(name: str) -> dict:
    path = ROOT / "metadata" / f"{name}_v1.json"
    if not path.exists():
        raise FileNotFoundError(f"Model metadata for {name} is unavailable.")
    return json.loads(path.read_text(encoding="utf-8"))
