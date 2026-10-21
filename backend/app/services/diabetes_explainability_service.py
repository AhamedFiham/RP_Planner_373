"""Explainable AI (XAI) service using SHAP for patient-specific diabetes risk prediction."""
from pathlib import Path
from typing import Any, Optional
import joblib
import numpy as np
import pandas as pd
import shap
from pydantic import BaseModel, Field

from app.schemas.diabetes_schema import DiabetesPatientInput
from app.utils.preprocessing import ALL_FEATURE_COLUMNS, get_feature_names

MODEL_PATH = Path(__file__).resolve().parents[2] / "trained_models" / "diabetes" / "selected_model.joblib"


class ShapFactor(BaseModel):
    feature_name: str
    feature_label: str
    patient_value: Any
    shap_value: float
    contribution_direction: str  # "risk_increasing" | "risk_decreasing" | "neutral"
    contribution_rank: int
    risk_category: str  # "modifiable" | "non_modifiable" | "manageable_clinical"
    explanation: str


class ExplainabilityResult(BaseModel):
    base_value: float
    output_space: str = "probability"  # exact model probability space [0, 1]
    predicted_probability: float
    risk_increasing_factors: list[ShapFactor] = Field(default_factory=list)
    risk_decreasing_factors: list[ShapFactor] = Field(default_factory=list)
    all_factors_ranked: list[ShapFactor] = Field(default_factory=list)


# Friendly display names
FEATURE_DISPLAY_NAMES = {
    "HbA1c_level": "HbA1c Level",
    "blood_glucose_level": "Blood Glucose",
    "bmi": "Body Mass Index (BMI)",
    "age": "Age",
    "hypertension": "Hypertension History",
    "heart_disease": "Heart Disease History",
    "smoking_history": "Smoking History",
    "gender": "Gender"
}

# Categorization of features
FEATURE_CATEGORIES = {
    "bmi": "modifiable",
    "smoking_history": "modifiable",
    "age": "non_modifiable",
    "gender": "non_modifiable",
    "HbA1c_level": "manageable_clinical",
    "blood_glucose_level": "manageable_clinical",
    "hypertension": "manageable_clinical",
    "heart_disease": "manageable_clinical"
}


class DiabetesExplainabilityService:
    def __init__(self):
        self._pipeline = None
        self._explainer = None
        self._feature_names = None

    def _ensure_loaded(self):
        if self._pipeline is None:
            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
            self._pipeline = joblib.load(MODEL_PATH)
            clf = self._pipeline.named_steps["classifier"]
            preproc = self._pipeline.named_steps["preprocessor"]
            self._feature_names = get_feature_names(preproc)
            self._explainer = shap.TreeExplainer(clf)

    def explain_prediction(self, patient: DiabetesPatientInput, predicted_prob: float) -> ExplainabilityResult:
        self._ensure_loaded()

        # Build single-row DataFrame with original schema
        patient_dict = {
            "gender": patient.gender,
            "age": patient.age,
            "hypertension": patient.hypertension,
            "heart_disease": patient.heart_disease,
            "smoking_history": patient.smoking_history,
            "bmi": patient.bmi,
            "HbA1c_level": patient.hba1c_level,
            "blood_glucose_level": patient.blood_glucose_level
        }
        df_patient = pd.DataFrame([patient_dict])[ALL_FEATURE_COLUMNS]

        # Transform features
        preprocessor = self._pipeline.named_steps["preprocessor"]
        X_trans = preprocessor.transform(df_patient)

        # Compute raw TreeExplainer SHAP values (in probability space)
        raw_shap = self._explainer.shap_values(X_trans)

        # Extract class 1 (diabetes probability) SHAP values
        if isinstance(raw_shap, list):
            vals = raw_shap[1][0]
            base_val = float(self._explainer.expected_value[1])
        elif hasattr(raw_shap, "shape") and len(raw_shap.shape) == 3:
            vals = raw_shap[0, :, 1]
            base_val = float(self._explainer.expected_value[1])
        else:
            vals = raw_shap[0]
            base_val = float(self._explainer.expected_value)

        # Aggregate one-hot encoded categories back to original root features
        root_shap: dict[str, float] = {
            "HbA1c_level": 0.0,
            "blood_glucose_level": 0.0,
            "bmi": 0.0,
            "age": 0.0,
            "hypertension": 0.0,
            "heart_disease": 0.0,
            "smoking_history": 0.0,
            "gender": 0.0
        }

        for fname, val in zip(self._feature_names, vals):
            if fname in root_shap:
                root_shap[fname] += float(val)
            elif fname.startswith("gender_"):
                root_shap["gender"] += float(val)
            elif fname.startswith("smoking_history_"):
                root_shap["smoking_history"] += float(val)

        # Generate explanatory factors
        factors: list[ShapFactor] = []
        for feat_name, s_val in root_shap.items():
            p_val = patient_dict[feat_name]
            
            # Formatting patient value
            if feat_name in ["hypertension", "heart_disease"]:
                p_display = "Yes" if p_val == 1 else "No"
            elif feat_name == "HbA1c_level":
                p_display = f"{p_val}%"
            elif feat_name == "blood_glucose_level":
                p_display = f"{p_val} mg/dL"
            elif feat_name == "bmi":
                p_display = f"{p_val} kg/m²"
            elif feat_name == "age":
                p_display = f"{int(p_val)} yrs"
            else:
                p_display = str(p_val)

            direction = "neutral"
            if s_val > 0.0005:
                direction = "risk_increasing"
            elif s_val < -0.0005:
                direction = "risk_decreasing"

            # Plain-language clinical explanation
            explanation = self._build_factor_explanation(feat_name, p_val, s_val, direction)

            factors.append(ShapFactor(
                feature_name=feat_name,
                feature_label=FEATURE_DISPLAY_NAMES.get(feat_name, feat_name),
                patient_value=p_display,
                shap_value=round(s_val, 4),
                contribution_direction=direction,
                contribution_rank=0,  # assigned below
                risk_category=FEATURE_CATEGORIES.get(feat_name, "manageable_clinical"),
                explanation=explanation
            ))

        # Sort by absolute SHAP impact
        factors.sort(key=lambda f: abs(f.shap_value), reverse=True)
        for idx, f in enumerate(factors, start=1):
            f.contribution_rank = idx

        risk_inc = [f for f in factors if f.contribution_direction == "risk_increasing"]
        risk_dec = [f for f in factors if f.contribution_direction == "risk_decreasing"]

        return ExplainabilityResult(
            base_value=round(base_val, 4),
            output_space="probability",
            predicted_probability=round(predicted_prob, 4),
            risk_increasing_factors=risk_inc,
            risk_decreasing_factors=risk_dec,
            all_factors_ranked=factors
        )

    def _build_factor_explanation(self, feat: str, val: Any, s_val: float, direction: str) -> str:
        s_pct = f"{abs(s_val) * 100:.1f}%"
        if direction == "risk_increasing":
            impact_desc = f"increased the predicted diabetes risk by approximately +{s_pct}"
        elif direction == "risk_decreasing":
            impact_desc = f"reduced the predicted diabetes risk by approximately -{s_pct}"
        else:
            impact_desc = "had minimal impact on the model's prediction"

        if feat == "HbA1c_level":
            return f"Patient's HbA1c of {val}% {impact_desc}."
        elif feat == "blood_glucose_level":
            return f"Blood glucose measurement of {val} mg/dL {impact_desc}."
        elif feat == "bmi":
            return f"Patient's BMI of {val} kg/m² {impact_desc}."
        elif feat == "age":
            return f"Patient's age ({val} years) {impact_desc}."
        elif feat == "hypertension":
            state = "presence" if val == 1 else "absence"
            return f"The {state} of hypertension history {impact_desc}."
        elif feat == "heart_disease":
            state = "presence" if val == 1 else "absence"
            return f"The {state} of cardiovascular disease history {impact_desc}."
        elif feat == "smoking_history":
            return f"Smoking status recorded as '{val}' {impact_desc}."
        elif feat == "gender":
            return f"Demographic feature '{val}' {impact_desc}."
        return f"{feat} ({val}) {impact_desc}."


# Singleton instance
diabetes_explainability_service = DiabetesExplainabilityService()
