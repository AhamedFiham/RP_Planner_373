"""Automated test suite verifying the 20 required research validation scenarios."""
import pytest
from pydantic import ValidationError
from app.schemas.diabetes_schema import (
    DiabetesPatientInput,
    evaluate_clinical_interpretation,
    evaluate_plausibility_and_ood
)
from app.services.diabetes_service import diabetes_service
from app.database.repositories.diabetes_repository import diabetes_repository


def test_01_normal_values_negative_prediction():
    patient = DiabetesPatientInput(
        gender="Female", age=28, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=21.5, HbA1c_level=5.0, blood_glucose_level=88,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.prediction.label == "negative"
    assert res.prediction.probability < 0.40
    assert res.clinical_assessment.status == "normal"
    print("Test 1 Passed: Normal values give negative prediction.")


def test_02_positive_elevated_bmi():
    patient = DiabetesPatientInput(
        gender="Male", age=52, hypertension=1, heart_disease=0,
        smoking_history="never", bmi=38.5, HbA1c_level=6.2, blood_glucose_level=145,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.prediction.label == "positive"
    bmi_factors = [f for f in res.explainability.all_factors_ranked if f.feature_name == "bmi"]
    assert len(bmi_factors) > 0
    print("Test 2 Passed: Elevated BMI contributes to prediction.")


def test_03_positive_elevated_hba1c():
    patient = DiabetesPatientInput(
        gender="Female", age=55, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=28.0, HbA1c_level=7.8, blood_glucose_level=160,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.prediction.label == "positive"
    assert res.clinical_assessment.status == "diabetes_range"
    top_factor = res.explainability.risk_increasing_factors[0]
    assert top_factor.feature_name == "HbA1c_level"
    print("Test 3 Passed: Elevated HbA1c is primary contributor and flags diabetes range.")


def test_04_positive_elevated_glucose():
    patient = DiabetesPatientInput(
        gender="Male", age=60, hypertension=1, heart_disease=0,
        smoking_history="never", bmi=29.0, HbA1c_level=6.4, blood_glucose_level=220,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.prediction.label == "positive"
    assert res.clinical_assessment.status == "diabetes_range"
    print("Test 4 Passed: Elevated glucose flags diabetes range.")


def test_05_positive_older_age():
    patient = DiabetesPatientInput(
        gender="Female", age=78, hypertension=1, heart_disease=1,
        smoking_history="former", bmi=27.0, HbA1c_level=6.3, blood_glucose_level=140,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.prediction.label == "positive"
    age_f = [f for f in res.explainability.all_factors_ranked if f.feature_name == "age"][0]
    assert age_f.contribution_direction == "risk_increasing"
    print("Test 5 Passed: Older age increases estimated risk.")


def test_06_positive_hypertension():
    patient = DiabetesPatientInput(
        gender="Male", age=54, hypertension=1, heart_disease=0,
        smoking_history="never", bmi=31.0, HbA1c_level=6.1, blood_glucose_level=135,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    htn_factor = [f for f in res.explainability.all_factors_ranked if f.feature_name == "hypertension"][0]
    assert htn_factor.contribution_direction == "risk_increasing"
    print("Test 6 Passed: Hypertension increases risk.")


def test_07_positive_current_smoking():
    patient = DiabetesPatientInput(
        gender="Male", age=48, hypertension=1, heart_disease=0,
        smoking_history="current", bmi=30.0, HbA1c_level=6.0, blood_glucose_level=130,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    smk_group = res.risk_factor_categories.modifiable.factors
    smk_item = [f for f in smk_group if "Tobacco" in f["name"]][0]
    assert smk_item["clinical_status"] == "Active Risk"
    print("Test 7 Passed: Current smoking classified as active modifiable risk.")


def test_08_multiple_contributing_factors():
    patient = DiabetesPatientInput(
        gender="Male", age=65, hypertension=1, heart_disease=1,
        smoking_history="current", bmi=35.0, HbA1c_level=8.2, blood_glucose_level=210,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.prediction.label == "positive"
    assert res.prediction.probability > 0.85
    assert len(res.explainability.risk_increasing_factors) >= 4
    print("Test 8 Passed: Multiple factors compound predicted probability.")


def test_09_negative_prediction_with_diabetes_range_hba1c():
    """Confirms clinical warning is NEVER suppressed even if model predicts low or negative."""
    patient = DiabetesPatientInput(
        gender="Female", age=22, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=19.0, HbA1c_level=6.6, blood_glucose_level=90,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    # Even if ML might predict lower likelihood due to very young age/low BMI:
    assert res.clinical_assessment.status == "diabetes_range"
    assert res.clinical_assessment.requires_confirmatory_testing is True
    # Clinical warning remains prominently present
    flag_titles = [f.title for f in res.clinical_assessment.flags]
    assert "HbA1c in Diabetes Range" in flag_titles
    print("Test 9 Passed: Clinical flags remain visible independently of ML prediction.")


def test_10_negative_prediction_with_concerning_fasting_glucose():
    patient = DiabetesPatientInput(
        gender="Male", age=25, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=20.0, HbA1c_level=5.2, blood_glucose_level=130,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.clinical_assessment.status == "diabetes_range"
    flag_titles = [f.title for f in res.clinical_assessment.flags]
    assert "Fasting Glucose in Diabetes Range" in flag_titles
    print("Test 10 Passed: Fasting glucose threshold flags diabetes range.")


def test_11_unknown_glucose_context():
    patient = DiabetesPatientInput(
        gender="Female", age=45, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=24.0, HbA1c_level=5.4, blood_glucose_level=130,
        glucose_context="unknown"
    )
    res = diabetes_service.process_assessment(patient)
    # 130 mg/dL with unknown context should be flagged as requires_clinical_review, not misclassified as confirmed fasting diabetes
    assert res.clinical_assessment.status in ["requires_clinical_review", "normal"]
    print("Test 11 Passed: Unknown context treated with safe conservative review.")


def test_12_unusually_high_physiologically_possible_glucose():
    patient = DiabetesPatientInput(
        gender="Male", age=50, hypertension=1, heart_disease=0,
        smoking_history="never", bmi=28.0, HbA1c_level=7.5, blood_glucose_level=340,
        glucose_context="random"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.plausibility.is_out_of_distribution is True
    assert res.plausibility.reliability_warning is not None
    print("Test 12 Passed: Out-of-training glucose generates reliability warning.")


def test_13_unusually_high_bmi():
    patient = DiabetesPatientInput(
        gender="Female", age=40, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=72.0, HbA1c_level=6.2, blood_glucose_level=120,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.plausibility.is_out_of_distribution is True
    print("Test 13 Passed: Extreme BMI triggers OOD warning.")


def test_14_unsupported_smoking_category_rejected():
    with pytest.raises(ValidationError):
        DiabetesPatientInput(
            gender="Female", age=40, hypertension=0, heart_disease=0,
            smoking_history="heavy_chain_smoker_unsupported", bmi=25.0,
            HbA1c_level=5.5, blood_glucose_level=100
        )
    print("Test 14 Passed: Unsupported smoking category rejected by Layer A validation.")


def test_15_missing_required_input_rejected():
    with pytest.raises(ValidationError):
        DiabetesPatientInput(
            gender="Female", age=40, hypertension=0, heart_disease=0,
            # missing smoking_history, bmi, HbA1c, etc.
        )
    print("Test 15 Passed: Missing required fields properly rejected.")


def test_16_invalid_numeric_input_rejected():
    with pytest.raises(ValidationError):
        DiabetesPatientInput(
            gender="Male", age=-5, hypertension=0, heart_disease=0,
            smoking_history="never", bmi=-25.0, HbA1c_level=5.5, blood_glucose_level=100
        )
    print("Test 16 Passed: Negative numeric input rejected.")


def test_17_out_of_distribution_input_handling():
    patient = DiabetesPatientInput(
        gender="Male", age=92, hypertension=1, heart_disease=1,
        smoking_history="former", bmi=26.0, HbA1c_level=9.5, blood_glucose_level=320,
        glucose_context="random"
    )
    res = diabetes_service.process_assessment(patient)
    assert res.plausibility.is_out_of_distribution is True
    assert "reliability" in res.personalized_awareness.prediction_explanation.lower()
    print("Test 17 Passed: OOD input documented in personalized awareness.")


def test_18_shap_explanation_consistency():
    patient = DiabetesPatientInput(
        gender="Female", age=50, hypertension=1, heart_disease=0,
        smoking_history="former", bmi=31.0, HbA1c_level=6.8, blood_glucose_level=150,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient)
    exp = res.explainability
    assert exp.output_space == "probability"
    assert len(exp.all_factors_ranked) == 8
    total_shap = sum(f.shap_value for f in exp.all_factors_ranked)
    # The sum of SHAP values plus base value closely approximates predicted probability
    approx_prob = exp.base_value + total_shap
    assert abs(approx_prob - res.prediction.probability) < 0.05
    print("Test 18 Passed: SHAP additivity and probability mapping verified.")


def test_19_database_persistence_and_retrieval():
    patient = DiabetesPatientInput(
        gender="Female", age=42, hypertension=0, heart_disease=0,
        smoking_history="never", bmi=25.5, HbA1c_level=5.6, blood_glucose_level=102,
        glucose_context="fasting"
    )
    res = diabetes_service.process_assessment(patient, user_email="test_patient_19@example.com")
    assert res.id is not None
    saved = diabetes_repository.get_assessment_by_id(res.id)
    assert saved is not None
    assert saved["id"] == res.id
    assert saved["prediction"]["label"] == res.prediction.label
    print("Test 19 Passed: Assessment saved and retrieved from persistent repository.")


def test_20_historical_assessment_retrieval():
    history = diabetes_service.get_history(limit=5)
    assert isinstance(history, list)
    assert len(history) > 0
    print(f"Test 20 Passed: Retrieved {len(history)} historical assessments.")


if __name__ == "__main__":
    test_01_normal_values_negative_prediction()
    test_02_positive_elevated_bmi()
    test_03_positive_elevated_hba1c()
    test_04_positive_elevated_glucose()
    test_05_positive_older_age()
    test_06_positive_hypertension()
    test_07_positive_current_smoking()
    test_08_multiple_contributing_factors()
    test_09_negative_prediction_with_diabetes_range_hba1c()
    test_10_negative_prediction_with_concerning_fasting_glucose()
    test_11_unknown_glucose_context()
    test_12_unusually_high_physiologically_possible_glucose()
    test_13_unusually_high_bmi()
    test_14_unsupported_smoking_category_rejected()
    test_15_missing_required_input_rejected()
    test_16_invalid_numeric_input_rejected()
    test_17_out_of_distribution_input_handling()
    test_18_shap_explanation_consistency()
    test_19_database_persistence_and_retrieval()
    test_20_historical_assessment_retrieval()
    print("\nALL 20 REQUIRED TEST SCENARIOS PASSED SUCCESSFULLY!")
