
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import shap

from sklearn.model_selection import train_test_split

from app.models.diabetes_model import (
    BACKEND_DIR,
    FEATURES,
    ZERO_AS_MISSING,
    load_model,
    prepare_input,
)


DATA_PATH = (
    BACKEND_DIR
    / "datasets"
    / "diabetes"
    / "raw"
    / "diabetes.csv"
)


@lru_cache(maxsize=1)
def get_background():
    """Recreate the training partition for SHAP background data."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    X = df[FEATURES].copy()
    y = df["Outcome"].astype(int)

    for column in ZERO_AS_MISSING:
        X.loc[X[column] == 0, column] = np.nan

    # Match the original training split and row filtering.
    usable = ~X.isna().all(axis=1)
    X = X.loc[usable]
    y = y.loc[usable]

    X_train, _X_test, _y_train, _y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    return X_train.sample(
        n=min(40, len(X_train)),
        random_state=42,
    )


@lru_cache(maxsize=1)
def get_explainer():
    """Cache the SHAP explainer rather than recreating it per request."""

    model = load_model()
    background = get_background()

    def predict_positive_class(data):
        frame = pd.DataFrame(
            data,
            columns=FEATURES,
        )

        for column in ZERO_AS_MISSING:
            frame.loc[frame[column] == 0, column] = np.nan

        probabilities = model.predict_proba(frame)
        classes = list(model.classes_)
        positive_index = classes.index(1)

        return probabilities[:, positive_index]

    return shap.KernelExplainer(
        predict_positive_class,
        background,
    )


def explain_prediction(values: dict) -> list[dict]:
    frame = prepare_input(values)
    explainer = get_explainer()

    shap_values = explainer.shap_values(
        frame,
        nsamples=100,
    )

    contributions = np.asarray(shap_values).reshape(-1)

    if len(contributions) != len(FEATURES):
        raise ValueError(
            "Unexpected SHAP output dimensions."
        )

    result = []

    for feature, observed, contribution in zip(
        FEATURES,
        frame.iloc[0].tolist(),
        contributions,
    ):
        result.append({
            "feature": feature,
            "observed_value": (
                None if pd.isna(observed)
                else float(observed)
            ),
            "shap_value": float(contribution),
            "direction": (
                "increases_model_output"
                if contribution > 0
                else "decreases_model_output"
                if contribution < 0
                else "no_contribution"
            ),
        })

    result.sort(
        key=lambda item: abs(item["shap_value"]),
        reverse=True,
    )

    return result
