"""Finds the trained model on disk and turns one patient into class probabilities.

Drop a file in backend/models/. Recognised names, in the order they are tried:

    random_forest_model.*        report 4.4 selects this as the deployment engine
    model.*                      the XGBoost bundle
    xgb_Tumor_Response_model.*   XGBoost saved natively

If none of those exist but models/ holds exactly one supported file, that file is
used. Accepted extensions: .pkl / .joblib (pickled) and .json / .ubj (XGBoost
native).

The notebooks save a bundle rather than a bare estimator:

    {"model": ..., "feature_columns": [...], "target": "Tumor_Response", ...}

so _unwrap below looks inside a dict before giving up. Whatever comes out has to
expose predict_proba; the feature frame is then built to match the column list
the file itself declares, which is safer than hardcoding one here.
"""

import logging
from pathlib import Path

import joblib
import numpy as np

import features

log = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "models"

PICKLE_SUFFIXES = (".pkl", ".joblib")
BOOSTER_SUFFIXES = (".json", ".ubj")
SUFFIXES = PICKLE_SUFFIXES + BOOSTER_SUFFIXES

PREFERRED_STEMS = ("random_forest_model", "model", "xgb_Tumor_Response_model")


class ModelUnavailable(RuntimeError):
    """Raised when a prediction is requested but no usable model was found."""


class LoadedModel:
    """An estimator plus the column order it was trained on."""

    def __init__(self, estimator, columns, target, name):
        self.estimator = estimator
        self.columns = list(columns)
        self.target = target
        self.name = name

    def probabilities(self, patient) -> np.ndarray:
        frame = features.build_frame(patient, self.columns)
        proba = self.estimator.predict_proba(frame)
        if isinstance(proba, list):  # multi-output wrapper around one target
            proba = proba[0]
        return np.asarray(proba, dtype=float)[0]


class BoosterAdapter:
    """Gives a native XGBoost Booster the predict_proba shape used above."""

    def __init__(self, booster):
        self.booster = booster
        self.feature_names_in_ = booster.feature_names

    def predict_proba(self, frame):
        import xgboost as xgb

        raw = np.asarray(self.booster.predict(xgb.DMatrix(frame)))
        if raw.ndim == 2:  # multi:softprob
            return raw
        return np.column_stack([1.0 - raw, raw])  # binary:logistic


class Registry:
    """Holds whatever was found on disk, plus how to score with it."""

    def __init__(self):
        self.mode = "unavailable"
        self.detail = f"No model file found in {MODEL_DIR}"
        self.model: LoadedModel | None = None

    def load(self):
        path, reason = _pick_file()
        if path is None:
            self.detail = reason
            log.warning("%s -- /api/predict will return 503", reason)
            return

        try:
            self.model = _load(path)
        except Exception as err:
            self.detail = f"Failed to load {path.name}: {err}"
            log.exception("Model load failed")
            return

        self.mode = "loaded"
        self.detail = (
            f"{path.name}: {type(self.model.estimator).__name__} predicting "
            f"{self.model.target} over {len(self.model.columns)} features"
        )
        log.info(self.detail)

    @property
    def ready(self) -> bool:
        return self.model is not None

    def predict(self, patient) -> tuple[str, dict[str, float], float]:
        """Return (predicted class, per-class probabilities, favourable total)."""
        if self.model is None:
            raise ModelUnavailable(self.detail)

        proba = self.model.probabilities(patient)
        labels = _labels(len(proba))
        by_label = {label: round(float(p), 4) for label, p in zip(labels, proba)}

        favourable = sum(
            float(proba[i]) for i in features.FAVOURABLE_CLASSES if i < len(proba)
        )
        predicted = labels[int(np.argmax(proba))]
        return predicted, by_label, min(1.0, max(0.0, favourable))


def _pick_file() -> tuple[Path | None, str]:
    """The model file to serve, or None plus the reason there isn't one."""
    for stem in PREFERRED_STEMS:
        for suffix in SUFFIXES:
            candidate = MODEL_DIR / f"{stem}{suffix}"
            if candidate.exists():
                return candidate, ""

    found = sorted(p for p in MODEL_DIR.glob("*") if p.suffix in SUFFIXES)
    if len(found) == 1:
        return found[0], ""
    if found:
        return None, (
            f"models/ holds {[p.name for p in found]}, none named "
            f"{' / '.join(PREFERRED_STEMS)}. Rename one, or leave a single "
            "supported file in the folder."
        )
    return None, f"No model file found in {MODEL_DIR}"


def _load(path: Path) -> LoadedModel:
    if path.suffix in PICKLE_SUFFIXES:
        payload = joblib.load(path)
    else:
        import xgboost as xgb

        booster = xgb.Booster()
        booster.load_model(str(path))
        payload = BoosterAdapter(booster)

    estimator, columns, target = _unwrap(payload)

    if not hasattr(estimator, "predict_proba"):
        raise TypeError(
            f"{type(estimator).__name__} has no predict_proba, so it cannot give "
            "per-class probabilities. Save a classifier, not a regressor."
        )
    if not columns:
        raise ValueError(
            "The file does not record which columns it was trained on. Save a "
            "bundle with a 'feature_columns' list alongside the model."
        )

    return LoadedModel(estimator, columns, target, path.name)


def _unwrap(payload) -> tuple[object, list[str], str]:
    """Pull the estimator, its column order, and its target out of a saved file."""
    if isinstance(payload, dict):
        estimator = _first(payload, ("model", "estimator", "clf", "classifier"))
        if estimator is None:
            raise TypeError(
                f"Saved a dict with keys {sorted(payload)} but none of them hold "
                "the model. Expected a 'model' key."
            )
        declared = _first(payload, ("feature_columns", "features", "columns"))
        columns = [] if declared is None else list(declared)
        target = _first(payload, ("target", "target_name")) or "unknown"
    else:
        estimator, columns, target = payload, [], "Tumor_Response"

    if len(columns) == 0:
        # scikit-learn stores this as a numpy array, so test it by length --
        # `or []` would raise "truth value of an array is ambiguous".
        declared = getattr(estimator, "feature_names_in_", None)
        columns = [] if declared is None else list(declared)

    return estimator, [str(c) for c in columns], str(target)


def _first(mapping: dict, keys):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _labels(count: int) -> list[str]:
    known = features.RESPONSE_CLASSES
    if count == len(known):
        return list(known)
    return [f"class {i}" for i in range(count)]


registry = Registry()
