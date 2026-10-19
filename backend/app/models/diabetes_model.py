
import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BACKEND_DIR
    / "trained_models"
    / "diabetes"
    / "selected_model.joblib"
)

METADATA_PATH = (
    BACKEND_DIR
    / "trained_models"
    / "diabetes"
    / "model_metadata.json"
)

FEATURES = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
]

ZERO_AS_MISSING = [
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
]


@lru_cache(maxsize=1)
def load_model():
    """Load the saved training pipeline once per process."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_metadata():
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Model metadata not found: {METADATA_PATH}"
        )

    with METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def prepare_input(values: dict) -> pd.DataFrame:
    """Preserve training feature order and zero policy."""

    clean_values = dict(values)
    if clean_values.get("Pregnancies") is None:
        clean_values["Pregnancies"] = 0

    frame = pd.DataFrame(
        [clean_values],
        columns=FEATURES,
    )

    for column in ZERO_AS_MISSING:
        frame.loc[frame[column] == 0, column] = float("nan")

    if frame.isna().all(axis=1).any():
        raise ValueError(
            "The assessment has no usable clinical measurements."
        )

    return frame


def predict(values: dict) -> dict:
    model = load_model()
    frame = prepare_input(values)

    predicted_class = int(model.predict(frame)[0])
    probabilities = model.predict_proba(frame)[0]

    # Find the probability associated with class 1
    # rather than assuming a column position.
    class_values = list(model.classes_)
    positive_index = class_values.index(1)

    return {
        "predicted_class": predicted_class,
        "probability_class_1": float(
            probabilities[positive_index]
        ),
        "model_name": load_metadata().get(
            "model_name",
            "Unknown",
        ),
    }
