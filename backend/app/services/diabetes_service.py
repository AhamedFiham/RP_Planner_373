"""Core orchestration service for the diabetes risk prediction and clinical awareness pipeline."""
from pathlib import Path
from typing import Any, Optional
import joblib
import pandas as pd
from pydantic import BaseModel, Field

from app.schemas.diabetes_schema import (
    DiabetesPatientInput,
    evaluate_plausibility_and_ood,
    evaluate_clinical_interpretation,
    ClinicalInterpretation,
    PlausibilityReport
)
from app.services.diabetes_explainability_service import (
    diabetes_explainability_service,
    ExplainabilityResult
)
from app.services.diabetes_awareness_service import (
    diabetes_awareness_service,
    RiskFactorCategories,
    PersonalizedAwareness
)
from app.database.repositories.diabetes_repository import diabetes_repository
from app.utils.preprocessing import ALL_FEATURE_COLUMNS

MODEL_PATH = Path(__file__).resolve().parents[2] / "trained_models" / "diabetes" / "selected_model.joblib"


class PredictionDetails(BaseModel):
    label: str  # "positive" | "negative"
    probability: float
    threshold: float
    model_version: str = "1.0.0"
    model_name: str = "RandomForest"


class DiabetesAssessmentResponse(BaseModel):
    id: str
    timestamp: str
    prediction: PredictionDetails
    plausibility: PlausibilityReport
    clinical_assessment: ClinicalInterpretation
    explainability: ExplainabilityResult
    risk_factor_categories: RiskFactorCategories
    personalized_awareness: PersonalizedAwareness
    input: dict[str, Any]
    disclaimer: str = (
        "This assessment is designed for educational and clinical decision-support purposes only. "
        "It does not replace professional medical diagnosis, laboratory testing, or clinical consultation."
    )


class DiabetesService:
    def __init__(self):
        self._pipeline = None
        self._decision_threshold = 0.40

    def _get_pipeline(self):
        if self._pipeline is None:
            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"Trained model not found at {MODEL_PATH}")
            self._pipeline = joblib.load(MODEL_PATH)
        return self._pipeline

    def process_assessment(
        self,
        patient: DiabetesPatientInput,
        user_email: Optional[str] = None
    ) -> DiabetesAssessmentResponse:
        # Step 1: Input Plausibility and Out-of-Distribution Check
        plausibility = evaluate_plausibility_and_ood(patient)

        # Step 2: WHO-Aligned Clinical Interpretation (independent of ML)
        clinical_interp = evaluate_clinical_interpretation(patient)

        # Step 3: ML Prediction
        pipeline = self._get_pipeline()
        patient_row = pd.DataFrame([{
            "gender": patient.gender,
            "age": patient.age,
            "hypertension": patient.hypertension,
            "heart_disease": patient.heart_disease,
            "smoking_history": patient.smoking_history,
            "bmi": patient.bmi,
            "HbA1c_level": patient.hba1c_level,
            "blood_glucose_level": patient.blood_glucose_level
        }])[ALL_FEATURE_COLUMNS]

        prob = float(pipeline.predict_proba(patient_row)[0, 1])
        label = "positive" if prob >= self._decision_threshold else "negative"

        pred_details = PredictionDetails(
            label=label,
            probability=round(prob, 4),
            threshold=self._decision_threshold,
            model_version="1.0.0",
            model_name="RandomForest"
        )

        # Step 4: SHAP Explainability
        try:
            explainability = diabetes_explainability_service.explain_prediction(patient, prob)
        except Exception as e:
            # Fallback if SHAP fails unexpectedly
            explainability = ExplainabilityResult(
                base_value=0.50,
                output_space="probability",
                predicted_probability=round(prob, 4),
                risk_increasing_factors=[],
                risk_decreasing_factors=[]
            )

        # Step 5: Risk Factor Categorization
        risk_categories = diabetes_awareness_service.classify_risk_factors(patient, explainability)

        # Step 6: Personalized Awareness Generation
        awareness = diabetes_awareness_service.generate_awareness(
            patient=patient,
            predicted_label=label,
            predicted_prob=prob,
            threshold=self._decision_threshold,
            clinical_interp=clinical_interp,
            plausibility=plausibility,
            explainability=explainability
        )

        # Step 7: Persistence
        payload_to_store = {
            "user_email": user_email or "anonymous@patient.local",
            "prediction": pred_details.model_dump(),
            "clinical_assessment": clinical_interp.model_dump(),
            "explainability": explainability.model_dump(),
            "risk_factor_categories": risk_categories.model_dump(),
            "personalized_awareness": awareness.model_dump(),
            "input": patient.model_dump()
        }
        assessment_id = diabetes_repository.save_assessment(payload_to_store)

        return DiabetesAssessmentResponse(
            id=assessment_id,
            timestamp=payload_to_store.get("timestamp", ""),
            prediction=pred_details,
            plausibility=plausibility,
            clinical_assessment=clinical_interp,
            explainability=explainability,
            risk_factor_categories=risk_categories,
            personalized_awareness=awareness,
            input=patient.model_dump()
        )

    def get_history(self, user_email: Optional[str] = None, limit: int = 30) -> list[dict[str, Any]]:
        return diabetes_repository.get_history(user_email=user_email, limit=limit)

    def get_assessment(self, assessment_id: str) -> Optional[dict[str, Any]]:
        return diabetes_repository.get_assessment_by_id(assessment_id)


diabetes_service = DiabetesService()
