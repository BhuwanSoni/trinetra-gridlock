"""
risk_ai.py
──────────────────────────────────────────────────────────────
Feature 1 — AI-Based Violation Risk Assessment

Replaces the fixed SEVERITY_TABLE risk scores with an XGBoost
model trained on violation feature vectors. The model outputs
a continuous risk score 0–100 and a priority tier.

Usage:
    from risk_ai import RiskPredictor
    predictor = RiskPredictor()          # loads / trains model
    score, tier = predictor.predict(features)

Features fed to the model:
    helmet          0/1  (violation present)
    triple_riding   0/1
    seatbelt        0/1
    phone           0/1
    red_light       0/1
    wrong_side      0/1
    abnormal        0/1
    illegal_parking 0/1
    zebra           0/1
    pedestrian_viol 0/1
    speed_kmh       float (0 if not measured)
    is_night        0/1  (hour >= 20 or hour < 6)
    is_peak_hour    0/1  (7-10 or 17-21)
    vehicle_type    0=bike, 1=car, 2=truck/bus
    total_violations int  (count in this incident)
    model_confidence float (avg across violations)

Training data:
    Synthetic dataset of 5000 incidents is generated here for
    demonstration. In production, replace with real challan data
    from your evidence/ folder via train_from_evidence().
"""

from __future__ import annotations

import json
import pickle
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

MODEL_PATH = Path("models/risk_xgb.pkl")
FEATURE_NAMES = [
    "helmet", "triple_riding", "seatbelt", "phone",
    "red_light", "wrong_side", "abnormal", "illegal_parking",
    "zebra", "pedestrian_viol",
    "speed_kmh", "is_night", "is_peak_hour",
    "vehicle_type", "total_violations", "model_confidence",
]

PRIORITY_TIERS = [
    (85, "Critical"),
    (65, "High"),
    (40, "Medium"),
    (0,  "Low"),
]


def _tier(score: float) -> str:
    for threshold, label in PRIORITY_TIERS:
        if score >= threshold:
            return label
    return "Low"


# ── Feature builder ────────────────────────────────────────────────────────────

def build_features(violations: list,
                   speed_kmh:  float = 0.0,
                   timestamp:  str   = None,
                   vehicle_type: str = "car") -> dict:
    """
    Build a flat feature dict from a list of Violation objects (or dicts).
    Ready to pass directly to RiskPredictor.predict().

    Args:
        violations:   list of Violation objects or .to_dict() dicts
        speed_kmh:    estimated speed (0 if not measured)
        timestamp:    ISO string; used for is_night / is_peak_hour
        vehicle_type: "bike" | "car" | "truck" | "bus"
    """
    vtype_map = {"bike": 0, "car": 1, "truck": 2, "bus": 2}

    # normalise to list of dicts
    dicts = [v if isinstance(v, dict) else v.to_dict() for v in violations]
    vtypes = {d.get("violation_type", "") for d in dicts}
    confs  = [d.get("confidence", 0.5) for d in dicts]

    hour = datetime.now().hour
    if timestamp:
        try:
            hour = datetime.fromisoformat(timestamp).hour
        except Exception:
            pass

    return {
        "helmet":          int("Helmet Violation"             in vtypes),
        "triple_riding":   int("Triple Riding"                in vtypes),
        "seatbelt":        int("Seat Belt Violation"          in vtypes),
        "phone":           int("Mobile Usage While Driving"   in vtypes),
        "red_light":       int("Red Light Violation"          in vtypes),
        "wrong_side":      int("Wrong Side Driving"           in vtypes),
        "abnormal":        int("Abnormal Driving Behaviour"   in vtypes),
        "illegal_parking": int("Illegal Parking"              in vtypes),
        "zebra":           int("Stop Line / Zebra Violation"  in vtypes),
        "pedestrian_viol": int("Pedestrian Signal Violation"  in vtypes),
        "speed_kmh":       float(speed_kmh),
        "is_night":        int(hour >= 20 or hour < 6),
        "is_peak_hour":    int(7 <= hour <= 10 or 17 <= hour <= 21),
        "vehicle_type":    vtype_map.get(vehicle_type.lower(), 1),
        "total_violations": len(dicts),
        "model_confidence": round(float(np.mean(confs)) if confs else 0.5, 3),
    }


# ── Synthetic training data ───────────────────────────────────────────────────

def _generate_synthetic_data(n: int = 5000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate plausible (features, risk_score) pairs for initial training.

    Risk is modelled as a weighted sum of violation severities plus
    time-of-day and speed modifiers, then clipped to [0, 100].
    Replace with real evidence data via train_from_evidence() for production.
    """
    rng = random.Random(42)
    X, y = [], []

    weights = {
        "helmet": 18, "triple_riding": 20, "seatbelt": 16,
        "phone": 20, "red_light": 30, "wrong_side": 28,
        "abnormal": 22, "illegal_parking": 10,
        "zebra": 14, "pedestrian_viol": 8,
    }

    for _ in range(n):
        row = {k: rng.randint(0, 1) for k in weights}
        row["speed_kmh"]        = rng.uniform(0, 120)
        row["is_night"]         = rng.randint(0, 1)
        row["is_peak_hour"]     = rng.randint(0, 1)
        row["vehicle_type"]     = rng.randint(0, 2)
        row["total_violations"] = sum(row[k] for k in weights)
        row["model_confidence"] = round(rng.uniform(0.45, 0.99), 3)

        base_risk = sum(weights[k] * row[k] for k in weights)
        base_risk += min(row["speed_kmh"] / 3, 25)   # speed contribution
        base_risk += row["is_night"]    * 8
        base_risk -= row["is_peak_hour"] * 3           # peak → more cameras
        base_risk += (row["model_confidence"] - 0.5) * 10

        risk = float(np.clip(base_risk + rng.gauss(0, 4), 0, 100))
        X.append([row[f] for f in FEATURE_NAMES])
        y.append(risk)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ── Model class ───────────────────────────────────────────────────────────────

class RiskPredictor:
    """
    XGBoost regression model that predicts a risk score 0–100
    from a violation feature dict.

    Falls back to weighted-rule scoring if XGBoost is not installed.
    """

    def __init__(self, model_path: Path = MODEL_PATH):
        self._model   = None
        self._mode    = "xgb"
        self._path    = model_path

        if model_path.exists():
            self._load(model_path)
        else:
            self._train_and_save(model_path)

    # ── Training ──────────────────────────────────────────────────────────────

    def _train_and_save(self, path: Path) -> None:
        try:
            import xgboost as xgb
        except ImportError:
            print("[RiskAI] xgboost not installed — using rule fallback.")
            print("         pip install xgboost")
            self._mode = "rule"
            return

        print("[RiskAI] Training XGBoost risk model on synthetic data …")
        X, y = _generate_synthetic_data(5000)

        self._model = xgb.XGBRegressor(
            n_estimators    = 300,
            max_depth       = 5,
            learning_rate   = 0.08,
            subsample       = 0.8,
            colsample_bytree= 0.8,
            objective       = "reg:squarederror",
            random_state    = 42,
            n_jobs          = -1,
        )
        self._model.fit(X, y, eval_set=[(X, y)], verbose=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self._model, f)
        print(f"[RiskAI] Model saved → {path}")

    def _load(self, path: Path) -> None:
        try:
            with open(path, "rb") as f:
                self._model = pickle.load(f)
            print(f"[RiskAI] Model loaded ← {path}")
        except Exception as e:
            print(f"[RiskAI] Load failed ({e}), retraining …")
            self._train_and_save(path)

    def train_from_evidence(self, evidence_dir: str = "evidence/metadata") -> None:
        """
        Retrain on real challan records saved by evidence.py.
        Expects JSON files with 'violations' list and 'combined_risk' label.
        Falls back to synthetic data if too few records.
        """
        try:
            import xgboost as xgb
        except ImportError:
            print("[RiskAI] xgboost not installed.")
            return

        records = []
        for f in Path(evidence_dir).glob("*.json"):
            try:
                records.append(json.loads(f.read_text()))
            except Exception:
                pass

        MIN_RECORDS = 200
        if len(records) < MIN_RECORDS:
            print(f"[RiskAI] Only {len(records)} real records "
                  f"(need {MIN_RECORDS}) — padding with synthetic data.")
            X_syn, y_syn = _generate_synthetic_data(MAX(0, MIN_RECORDS - len(records)))
        else:
            X_syn, y_syn = np.empty((0, len(FEATURE_NAMES))), np.empty(0)

        X_real, y_real = [], []
        for r in records:
            feats = build_features(
                r.get("violations", []),
                vehicle_type=r.get("vehicle_type", "car"),
                timestamp=r.get("timestamp"),
            )
            X_real.append([feats[f] for f in FEATURE_NAMES])
            y_real.append(float(r.get("combined_risk", 50)))

        X = np.vstack([np.array(X_real, dtype=np.float32), X_syn]) if X_real else X_syn
        y = np.concatenate([np.array(y_real, dtype=np.float32), y_syn])

        self._model = xgb.XGBRegressor(n_estimators=300, max_depth=5,
                                        learning_rate=0.08, random_state=42)
        self._model.fit(X, y, verbose=False)
        with open(self._path, "wb") as f:
            pickle.dump(self._model, f)
        print(f"[RiskAI] Retrained on {len(records)} real + synthetic records → {self._path}")

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, features: dict) -> tuple[float, str]:
        """
        Args:
            features: dict from build_features()

        Returns:
            (risk_score: float 0-100, priority_tier: str)
        """
        if self._mode == "rule" or self._model is None:
            return self._rule_fallback(features)

        vec = np.array([[features.get(f, 0) for f in FEATURE_NAMES]],
                       dtype=np.float32)
        try:
            score = float(np.clip(self._model.predict(vec)[0], 0, 100))
            return round(score, 1), _tier(score)
        except Exception as e:
            print(f"[RiskAI] Predict error ({e}), using rule fallback.")
            return self._rule_fallback(features)

    @staticmethod
    def _rule_fallback(features: dict) -> tuple[float, str]:
        """Simple weighted sum — used when XGBoost is unavailable."""
        weights = {
            "helmet": 18, "triple_riding": 20, "seatbelt": 16,
            "phone": 20, "red_light": 30, "wrong_side": 28,
            "abnormal": 22, "illegal_parking": 10,
            "zebra": 14, "pedestrian_viol": 8,
        }
        score = sum(weights.get(k, 0) * float(features.get(k, 0))
                    for k in weights)
        score += min(features.get("speed_kmh", 0) / 3, 25)
        score += features.get("is_night", 0) * 8
        score  = float(np.clip(score, 0, 100))
        return round(score, 1), _tier(score)

    def feature_importance(self) -> dict:
        """Return feature importances (XGBoost mode only)."""
        if self._model is None or self._mode == "rule":
            return {}
        try:
            imp = self._model.feature_importances_
            return dict(sorted(zip(FEATURE_NAMES, imp.tolist()),
                               key=lambda x: -x[1]))
        except Exception:
            return {}


# ── Module-level singleton ─────────────────────────────────────────────────────

_predictor: Optional[RiskPredictor] = None


def get_predictor() -> RiskPredictor:
    global _predictor
    if _predictor is None:
        _predictor = RiskPredictor()
    return _predictor


def predict_risk(violations: list,
                 speed_kmh:    float = 0.0,
                 timestamp:    str   = None,
                 vehicle_type: str   = "car") -> tuple[float, str]:
    """
    Convenience wrapper. Call from anywhere with a list of Violation objects.

    Returns:
        (risk_score: float, priority_tier: str)
    """
    features = build_features(violations, speed_kmh, timestamp, vehicle_type)
    return get_predictor().predict(features)