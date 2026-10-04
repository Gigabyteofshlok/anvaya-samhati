"""Train deterministic demo-only ML artifacts from programmatically generated synthetic data.

Run explicitly: python -m ml.training.train_models
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, roc_auc_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
METADATA = ROOT / "metadata"
DATASETS = ROOT / "datasets"
RANDOM_SEED = 20260923


def _save(name: str, model, features: list[str], target: str, metrics: dict, rows: int, algorithm: str) -> None:
    MODELS.mkdir(parents=True, exist_ok=True); METADATA.mkdir(parents=True, exist_ok=True)
    artifact = MODELS / f"{name}_v1.joblib"
    joblib.dump({"model": model, "features": features, "version": "1.0.0"}, artifact)
    metadata = {"model_name": name, "model_version": "1.0.0", "training_date": date.today().isoformat(), "dataset_size": rows,
                "features": features, "target": target, "algorithm": algorithm, "metrics": metrics,
                "artifact_path": str(artifact.relative_to(ROOT.parent)),
                "limitations": "Trained entirely on programmatically generated synthetic demo data. It is decision support only, not validated clinical or operational guidance."}
    (METADATA / f"{name}_v1.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def train_all(rows: int = 2400) -> None:
    rng = np.random.default_rng(RANDOM_SEED)
    DATASETS.mkdir(parents=True, exist_ok=True)
    age = rng.integers(18, 91, rows); heart_rate = rng.normal(84, 17, rows).clip(45, 180)
    systolic_bp = rng.normal(126, 22, rows).clip(70, 230); temperature = rng.normal(37.0, .8, rows).clip(34, 42)
    spo2 = rng.normal(96, 3, rows).clip(75, 100); respiratory_rate = rng.normal(18, 5, rows).clip(8, 42)
    hemoglobin = rng.normal(12.5, 2.0, rows).clip(5, 19); wbc = rng.normal(7800, 2500, rows).clip(1500, 28000)
    condition_count = rng.integers(0, 5, rows); admission_type = rng.integers(0, 3, rows)
    risk_signal = ((age > 72).astype(float) + (heart_rate > 108) + (systolic_bp < 95) + (temperature > 38.4) + (spo2 < 92) * 1.8 + (respiratory_rate > 24) + (hemoglobin < 9) + (wbc > 13000) + condition_count * .25 + admission_type * .18 + rng.normal(0, .55, rows))
    risk_target = (risk_signal > 2.15).astype(int)
    clinical_features = ["age", "heart_rate", "systolic_bp", "temperature", "spo2", "respiratory_rate", "hemoglobin", "wbc", "condition_count", "admission_type"]
    clinical = pd.DataFrame(dict(zip(clinical_features, [age, heart_rate, systolic_bp, temperature, spo2, respiratory_rate, hemoglobin, wbc, condition_count, admission_type])))
    clinical.to_csv(DATASETS / "synthetic_clinical.csv", index=False)
    x_train, x_test, y_train, y_test = train_test_split(clinical, risk_target, test_size=.25, random_state=RANDOM_SEED, stratify=risk_target)
    risk_model = RandomForestClassifier(n_estimators=180, min_samples_leaf=5, random_state=RANDOM_SEED, n_jobs=-1).fit(x_train, y_train)
    _save("patient_risk", risk_model, clinical_features, "deterioration_risk", {"roc_auc": round(roc_auc_score(y_test, risk_model.predict_proba(x_test)[:, 1]), 3), "accuracy": round(accuracy_score(y_test, risk_model.predict(x_test)), 3)}, rows, "RandomForestClassifier")
    los_target = np.maximum(1, 1.4 + age / 38 + condition_count * .55 + admission_type * .7 + risk_signal * .6 + rng.normal(0, 1.1, rows))
    los_model = RandomForestRegressor(n_estimators=180, min_samples_leaf=5, random_state=RANDOM_SEED, n_jobs=-1).fit(x_train, los_target[x_train.index])
    _save("length_of_stay", los_model, clinical_features, "length_of_stay_days", {"mae_days": round(mean_absolute_error(los_target[x_test.index], los_model.predict(x_test)), 3)}, rows, "RandomForestRegressor")
    readmission_target = ((risk_signal + (condition_count >= 3) + rng.normal(0, .7, rows)) > 2.5).astype(int)
    readmission_model = RandomForestClassifier(n_estimators=180, min_samples_leaf=5, random_state=RANDOM_SEED, n_jobs=-1).fit(x_train, readmission_target[x_train.index])
    _save("readmission_risk", readmission_model, clinical_features, "readmission_within_30_days", {"roc_auc": round(roc_auc_score(readmission_target[x_test.index], readmission_model.predict_proba(x_test)[:, 1]), 3)}, rows, "RandomForestClassifier")
    operational = pd.DataFrame({"branch_index": rng.integers(0, 3, rows), "ward_index": rng.integers(0, 5, rows), "day_of_week": rng.integers(0, 7, rows), "day_offset": rng.integers(0, 30, rows)})
    occupancy = np.clip(42 + operational.branch_index * 7 + operational.ward_index * 4 + operational.day_of_week * .8 + operational.day_offset * .18 + rng.normal(0, 4, rows), 0, 100)
    bx, tx, by, ty = train_test_split(operational, occupancy, test_size=.25, random_state=RANDOM_SEED)
    bed_model = RandomForestRegressor(n_estimators=160, min_samples_leaf=5, random_state=RANDOM_SEED, n_jobs=-1).fit(bx, by)
    _save("bed_occupancy", bed_model, list(operational.columns), "occupancy_percent", {"mae_percent": round(mean_absolute_error(ty, bed_model.predict(tx)), 3)}, rows, "RandomForestRegressor")
    pharmacy = pd.DataFrame({"medication_index": rng.integers(0, 12, rows), "day_of_week": rng.integers(0, 7, rows), "current_stock": rng.integers(0, 260, rows), "recent_dispenses": rng.integers(0, 45, rows)})
    demand = np.maximum(1, 7 + pharmacy.medication_index * 1.3 + pharmacy.day_of_week * .7 + pharmacy.recent_dispenses * .65 + rng.normal(0, 4, rows))
    px, tx, py, ty = train_test_split(pharmacy, demand, test_size=.25, random_state=RANDOM_SEED)
    pharmacy_model = RandomForestRegressor(n_estimators=160, min_samples_leaf=5, random_state=RANDOM_SEED, n_jobs=-1).fit(px, py)
    _save("pharmacy_demand", pharmacy_model, list(pharmacy.columns), "next_7_day_demand", {"mae_units": round(mean_absolute_error(ty, pharmacy_model.predict(tx)), 3)}, rows, "RandomForestRegressor")


if __name__ == "__main__":
    train_all()
