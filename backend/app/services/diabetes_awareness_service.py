"""Personalized diabetes awareness service based on deterministic, clinically reviewed guidelines."""
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.diabetes_schema import DiabetesPatientInput, ClinicalInterpretation, PlausibilityReport
from app.services.diabetes_explainability_service import ExplainabilityResult, ShapFactor


class RiskFactorGroup(BaseModel):
    category_name: str
    category_type: str  # "modifiable" | "non_modifiable" | "manageable_clinical"
    description: str
    factors: list[dict[str, Any]] = Field(default_factory=list)


class RiskFactorCategories(BaseModel):
    modifiable: RiskFactorGroup
    non_modifiable: RiskFactorGroup
    manageable_clinical: RiskFactorGroup


class PersonalizedAwareness(BaseModel):
    prediction_explanation: str
    lifestyle_awareness: list[str] = Field(default_factory=list)
    medical_awareness: list[str] = Field(default_factory=list)
    screening_guidance: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class DiabetesAwarenessService:
    def classify_risk_factors(
        self,
        patient: DiabetesPatientInput,
        explainability: ExplainabilityResult
    ) -> RiskFactorCategories:
        """Classifies patient features into modifiable, non-modifiable, and manageable clinical factors."""
        shap_map = {f.feature_name: f for f in explainability.all_factors_ranked}

        # Modifiable
        modifiable_items = []
        # BMI
        bmi_f = shap_map.get("bmi")
        bmi_status = "Optimal"
        if patient.bmi >= 30.0:
            bmi_status = "Obese"
        elif patient.bmi >= 25.0:
            bmi_status = "Overweight"
        elif patient.bmi < 18.5:
            bmi_status = "Underweight"
        
        modifiable_items.append({
            "name": "Body Mass Index (BMI)",
            "value": f"{patient.bmi} kg/m²",
            "clinical_status": bmi_status,
            "shap_impact": bmi_f.shap_value if bmi_f else 0.0,
            "direction": bmi_f.contribution_direction if bmi_f else "neutral",
            "clinical_note": (
                "Weight management through tailored nutrition and safe physical activity can improve insulin sensitivity."
                if patient.bmi >= 25.0 else "Healthy BMI range supports stable insulin regulation."
            )
        })

        # Smoking behavior
        smk_f = shap_map.get("smoking_history")
        smk = patient.smoking_history.lower()
        if smk == "current":
            smk_note = "Active tobacco use directly impairs endothelial function and worsens insulin resistance. Smoking cessation provides immediate metabolic benefits."
            smk_modifiable = True
        elif smk == "former":
            smk_note = "Past smoking history is an unchangeable historical exposure, though maintained cessation greatly reduces ongoing cardiovascular risk."
            smk_modifiable = False
        elif smk == "never":
            smk_note = "Never smoking is an important protective lifestyle factor for cardiovascular and metabolic health."
            smk_modifiable = False
        else:
            smk_note = "Smoking history was not reported. Clarify tobacco use with your physician."
            smk_modifiable = False

        modifiable_items.append({
            "name": "Tobacco Use Status",
            "value": patient.smoking_history,
            "clinical_status": "Active Risk" if smk == "current" else "Historical/Non-active",
            "shap_impact": smk_f.shap_value if smk_f else 0.0,
            "direction": smk_f.contribution_direction if smk_f else "neutral",
            "clinical_note": smk_note
        })

        # Non-Modifiable
        non_modifiable_items = []
        age_f = shap_map.get("age")
        non_modifiable_items.append({
            "name": "Age",
            "value": f"{int(patient.age)} years",
            "clinical_status": "Increased Risk" if patient.age >= 45 else "Baseline",
            "shap_impact": age_f.shap_value if age_f else 0.0,
            "direction": age_f.contribution_direction if age_f else "neutral",
            "clinical_note": "Risk of altered glucose metabolism naturally rises with age and is not a personal shortcoming. Regular screening becomes increasingly vital after age 45."
        })

        gender_f = shap_map.get("gender")
        non_modifiable_items.append({
            "name": "Gender",
            "value": patient.gender,
            "clinical_status": "Inherent Characteristic",
            "shap_impact": gender_f.shap_value if gender_f else 0.0,
            "direction": gender_f.contribution_direction if gender_f else "neutral",
            "clinical_note": "Biological sex influences fat distribution patterns and hormone-mediated insulin dynamics."
        })

        # Manageable Clinical Factors
        clinical_items = []
        hba1c_f = shap_map.get("HbA1c_level")
        clinical_items.append({
            "name": "HbA1c Level",
            "value": f"{patient.hba1c_level}%",
            "clinical_status": "Diagnostic Threshold" if patient.hba1c_level >= 6.5 else ("Elevated" if patient.hba1c_level >= 5.7 else "Normal"),
            "shap_impact": hba1c_f.shap_value if hba1c_f else 0.0,
            "direction": hba1c_f.contribution_direction if hba1c_f else "neutral",
            "clinical_note": "Reflects average blood glucose over the past 2–3 months. Manageable with clinical care, nutritional therapy, and monitoring."
        })

        bg_f = shap_map.get("blood_glucose_level")
        clinical_items.append({
            "name": "Blood Glucose Level",
            "value": f"{patient.blood_glucose_level} mg/dL",
            "clinical_status": "Critical" if patient.blood_glucose_level >= 200 else ("Elevated" if patient.blood_glucose_level >= 126 else "Normal"),
            "shap_impact": bg_f.shap_value if bg_f else 0.0,
            "direction": bg_f.contribution_direction if bg_f else "neutral",
            "clinical_note": "Current circulating glucose level. Highly responsive to medication adherence, meal composition, and acute stressors."
        })

        htn_f = shap_map.get("hypertension")
        clinical_items.append({
            "name": "Hypertension History",
            "value": "Yes" if patient.hypertension == 1 else "No",
            "clinical_status": "Chronic Condition" if patient.hypertension == 1 else "None Reported",
            "shap_impact": htn_f.shap_value if htn_f else 0.0,
            "direction": htn_f.contribution_direction if htn_f else "neutral",
            "clinical_note": "Hypertension requires long-term medical management to protect microvascular (retina, kidneys) and macrovascular systems."
        })

        hd_f = shap_map.get("heart_disease")
        clinical_items.append({
            "name": "Heart Disease History",
            "value": "Yes" if patient.heart_disease == 1 else "No",
            "clinical_status": "Established Vascular Condition" if patient.heart_disease == 1 else "None Reported",
            "shap_impact": hd_f.shap_value if hd_f else 0.0,
            "direction": hd_f.contribution_direction if hd_f else "neutral",
            "clinical_note": "Cardiovascular disease demands rigorous blood pressure, lipid, and glycemic target coordination by medical professionals."
        })

        return RiskFactorCategories(
            modifiable=RiskFactorGroup(
                category_name="Modifiable Risk Factors",
                category_type="modifiable",
                description="Factors you can potentially influence or improve through personalized lifestyle changes.",
                factors=modifiable_items
            ),
            non_modifiable=RiskFactorGroup(
                category_name="Non-Modifiable Risk Factors",
                category_type="non_modifiable",
                description="Intrinsic characteristics that cannot be changed and should be addressed through awareness and proactive screening.",
                factors=non_modifiable_items
            ),
            manageable_clinical=RiskFactorGroup(
                category_name="Manageable Clinical Factors",
                category_type="manageable_clinical",
                description="Physiological measurements and chronic conditions that require professional medical monitoring and treatment.",
                factors=clinical_items
            )
        )

    def generate_awareness(
        self,
        patient: DiabetesPatientInput,
        predicted_label: str,
        predicted_prob: float,
        threshold: float,
        clinical_interp: ClinicalInterpretation,
        plausibility: PlausibilityReport,
        explainability: ExplainabilityResult
    ) -> PersonalizedAwareness:
        """Generates deterministic, clinically reviewed recommendations without generative hallucination."""
        lifestyle: list[str] = []
        medical: list[str] = []
        screening: list[str] = []
        next_steps: list[str] = []

        # Prediction explanation using SHAP top contributors
        top_inc = explainability.risk_increasing_factors[:3]
        if top_inc:
            inc_str = ", ".join([f"{f.feature_label} ({f.patient_value})" for f in top_inc])
            explanation = (
                f"The AI model estimated an overall diabetes probability of {predicted_prob * 100:.1f}%. "
                f"The primary contributors elevating the risk estimate were {inc_str}. "
            )
        else:
            explanation = (
                f"The AI model estimated a low diabetes probability of {predicted_prob * 100:.1f}%. "
                f"Most clinical markers were within baseline ranges. "
            )

        if plausibility.is_out_of_distribution:
            explanation += " Reliability Warning: Certain clinical values fall outside the model's standard training range; clinical evaluation takes priority."

        # Scenario A & C: Positive prediction or clinical flags
        is_positive = (predicted_label == "positive")
        has_clinical_flags = (clinical_interp.status in ["diabetes_range", "elevated_risk", "requires_clinical_review"])

        if is_positive:
            next_steps.append("Schedule a comprehensive medical evaluation with a licensed physician or endocrinologist.")
            if clinical_interp.requires_confirmatory_testing:
                next_steps.append(
                    "Obtain repeat standardized laboratory testing (such as fasting plasma glucose or laboratory HbA1c) "
                    "on a separate day to confirm diagnostic status."
                )
        else:
            if has_clinical_flags:
                next_steps.append(
                    "Even though the AI model prediction is negative, your clinical laboratory values show elevated markers. "
                    "Consult a physician to review these specific findings."
                )
            else:
                next_steps.append("Maintain routine annual health checkups and preventative wellness screenings.")

        # Modifiable lifestyle advice
        if patient.bmi >= 25.0:
            lifestyle.append(
                "Aim for gradual, sustainable weight reduction (5%–7% of body weight) through balanced portion control and nutrient-dense whole foods."
            )
            lifestyle.append(
                "Engage in at least 150 minutes of moderate-intensity aerobic exercise per week (such as brisk walking or swimming), split over at least 3 days."
            )
        else:
            lifestyle.append(
                "Continue balanced dietary habits rich in dietary fiber, vegetables, and lean proteins, and avoid sugar-sweetened beverages."
            )

        if patient.smoking_history.lower() == "current":
            lifestyle.append(
                "Pursue structured tobacco cessation support. Quitting smoking improves vascular health and insulin sensitivity immediately."
            )

        # Medical awareness
        if patient.hba1c_level >= 6.5 or patient.blood_glucose_level >= 200:
            medical.append(
                "Your glycemic readings reach recognized clinical diabetes thresholds. A physician can assess organ health, microvascular function, and appropriate therapeutic pathways."
            )
            medical.append(
                "Do NOT self-prescribe, alter, or stop any diabetes medications without direct guidance from your prescribing physician."
            )
        elif 5.7 <= patient.hba1c_level < 6.5 or patient.blood_glucose_level >= 100:
            medical.append(
                "Your results indicate intermediate hyperglycemia (pre-diabetes range). Early intensive lifestyle modification can prevent or significantly delay onset of Type 2 diabetes."
            )

        if patient.hypertension == 1:
            medical.append(
                "Co-occurring hypertension requires vigilant blood pressure monitoring (aiming for clinical targets recommended by your doctor, typically <130/80 mmHg)."
            )

        if patient.heart_disease == 1:
            medical.append(
                "Established cardiovascular disease necessitates tight lipid, blood pressure, and metabolic monitoring under cardiovascular care."
            )

        # Screening guidance
        if patient.hba1c_level >= 6.5 or patient.blood_glucose_level >= 126:
            screening.append("Comprehensive dilated eye exam to screen for diabetic retinopathy.")
            screening.append("Urine albumin-to-creatinine ratio (uACR) and eGFR to evaluate kidney health.")
            screening.append("Comprehensive foot exam to assess protective sensation and peripheral circulation.")
        elif patient.age >= 45 or patient.bmi >= 25.0:
            screening.append("Annual fasting plasma glucose or laboratory HbA1c screening.")
            screening.append("Annual lipid panel and blood pressure evaluation.")

        return PersonalizedAwareness(
            prediction_explanation=explanation,
            lifestyle_awareness=lifestyle,
            medical_awareness=medical,
            screening_guidance=screening,
            recommended_next_steps=next_steps
        )


diabetes_awareness_service = DiabetesAwarenessService()
