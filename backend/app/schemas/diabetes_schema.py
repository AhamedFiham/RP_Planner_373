"""Request and response schemas and multi-layer validation for diabetes risk assessment.

Layers:
  Layer A: Technical validation (types, parsing, bounds, finite numbers, categories)
  Layer B: Plausibility & Out-of-Distribution checks (physiological bounds, reliability warnings)
  Layer C: WHO & international guideline-aligned clinical interpretation (independent of ML)
"""
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# Valid categorical values from the trained pipeline
SUPPORTED_GENDERS = ["Female", "Male", "Other"]
SUPPORTED_SMOKING = ["No Info", "never", "former", "current", "not current", "ever"]
SUPPORTED_GLUCOSE_CONTEXTS = ["fasting", "random", "two_hour_ogtt", "unknown"]


class DiabetesPatientInput(BaseModel):
    """Patient medical features collected for diabetes assessment."""
    gender: str = Field(..., description="Patient gender (Female, Male, Other)")
    age: float = Field(..., description="Age in years (>= 0)")
    hypertension: int = Field(..., description="History of hypertension (0 = No, 1 = Yes)")
    heart_disease: int = Field(..., description="History of heart disease (0 = No, 1 = Yes)")
    smoking_history: str = Field(..., description="Smoking status (No Info, never, former, current, not current, ever)")
    bmi: float = Field(..., description="Body Mass Index (kg/m^2)")
    hba1c_level: float = Field(..., alias="HbA1c_level", description="Glycated hemoglobin percentage (%)")
    blood_glucose_level: float = Field(..., description="Blood glucose measurement (mg/dL)")
    
    # Optional clinical context fields (used for clinical interpretation, NOT passed to ML model)
    glucose_context: Optional[str] = Field(
        default="unknown",
        description="Clinical context of glucose measurement (fasting, random, two_hour_ogtt, unknown)"
    )
    hba1c_lab_confirmed: Optional[bool] = Field(
        default=True,
        description="Whether HbA1c was measured by a standardized laboratory assay"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        json_schema_extra={
            "example": {
                "gender": "Female",
                "age": 45,
                "hypertension": 0,
                "heart_disease": 0,
                "smoking_history": "never",
                "bmi": 26.5,
                "HbA1c_level": 5.8,
                "blood_glucose_level": 115,
                "glucose_context": "fasting",
                "hba1c_lab_confirmed": True
            }
        }
    )

    # ----------------------------------------------------
    # LAYER A: TECHNICAL VALIDATION
    # ----------------------------------------------------
    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Gender must be a string.")
        norm = v.strip().capitalize()
        if norm not in SUPPORTED_GENDERS:
            raise ValueError(f"Gender '{v}' is not supported. Supported values: {', '.join(SUPPORTED_GENDERS)}")
        return norm

    @field_validator("smoking_history")
    @classmethod
    def validate_smoking_history(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Smoking history must be a string.")
        norm = v.strip()
        # Case-insensitive match for common inputs
        lookup = {s.lower(): s for s in SUPPORTED_SMOKING}
        if norm.lower() not in lookup:
            raise ValueError(
                f"Smoking history '{v}' is not supported. Supported values: {', '.join(SUPPORTED_SMOKING)}"
            )
        return lookup[norm.lower()]

    @field_validator("hypertension", "heart_disease", mode="before")
    @classmethod
    def validate_binary_flags(cls, v: Any) -> int:
        if isinstance(v, bool):
            return 1 if v else 0
        try:
            val = int(v)
            if val not in [0, 1]:
                raise ValueError
            return val
        except Exception:
            raise ValueError("Value must be 0 (No) or 1 (Yes).")

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: float) -> float:
        if v < 0 or v > 125:
            raise ValueError("Age must be between 0 and 125 years.")
        return round(float(v), 1)

    @field_validator("bmi")
    @classmethod
    def validate_bmi(cls, v: float) -> float:
        if v < 8.0 or v > 120.0:
            raise ValueError("BMI must be between 8.0 and 120.0 kg/m^2.")
        return round(float(v), 2)

    @field_validator("hba1c_level")
    @classmethod
    def validate_hba1c(cls, v: float) -> float:
        if v < 3.0 or v > 22.0:
            raise ValueError("HbA1c level must be between 3.0% and 22.0%.")
        return round(float(v), 2)

    @field_validator("blood_glucose_level")
    @classmethod
    def validate_glucose(cls, v: float) -> float:
        if v < 30 or v > 800:
            raise ValueError("Blood glucose must be between 30 and 800 mg/dL.")
        return round(float(v), 1)

    @field_validator("glucose_context")
    @classmethod
    def validate_glucose_context(cls, v: Optional[str]) -> str:
        if not v:
            return "unknown"
        norm = v.strip().lower()
        if norm not in SUPPORTED_GLUCOSE_CONTEXTS:
            return "unknown"
        return norm


# ----------------------------------------------------
# LAYER B: PLAUSIBILITY & OOD VALIDATION RESULT
# ----------------------------------------------------
class PlausibilityReport(BaseModel):
    is_plausible: bool = True
    is_out_of_distribution: bool = False
    reliability_warning: Optional[str] = None
    flags: list[str] = Field(default_factory=list)


def evaluate_plausibility_and_ood(patient: DiabetesPatientInput) -> PlausibilityReport:
    """Evaluates whether inputs are physiologically unusual or out of model training domain."""
    flags = []
    ood = False
    warning = None

    # Model training domain boundaries (from 100,992 record training set):
    # age: [0, 81], bmi: [9.97, 95.83], HbA1c: [3.47, 9.09], glucose: [79, 303]
    if patient.age > 81:
        flags.append("Patient age exceeds the model's primary training ceiling (81 years).")
        ood = True
    if patient.age < 18:
        flags.append("Pediatric age: standard adult clinical thresholds and training distributions may not fully apply.")

    if patient.blood_glucose_level > 303:
        flags.append(f"Blood glucose ({patient.blood_glucose_level} mg/dL) exceeds model's training upper range (303 mg/dL).")
        ood = True
    elif patient.blood_glucose_level < 79:
        flags.append(f"Blood glucose ({patient.blood_glucose_level} mg/dL) is below model's training lower range (79 mg/dL).")
        ood = True

    if patient.hba1c_level > 9.09:
        flags.append(f"HbA1c ({patient.hba1c_level}%) exceeds model's training upper range (9.09%).")
        ood = True
    elif patient.hba1c_level < 3.47:
        flags.append(f"HbA1c ({patient.hba1c_level}%) is below model's training lower range (3.47%).")
        ood = True

    if patient.bmi > 65.0:
        flags.append(f"Extreme BMI ({patient.bmi} kg/m^2) is clinically unusual.")
        ood = True

    if ood:
        warning = (
            "One or more clinical measurements fall outside the validated machine learning training distribution. "
            "Model prediction probability should be interpreted with clinical caution, and primary clinical guidelines should take precedence."
        )

    return PlausibilityReport(
        is_plausible=True,
        is_out_of_distribution=ood,
        reliability_warning=warning,
        flags=flags
    )


# ----------------------------------------------------
# LAYER C: WHO & INTERNATIONAL CLINICAL INTERPRETATION
# ----------------------------------------------------
class ClinicalFlag(BaseModel):
    category: str
    severity: Literal["info", "warning", "critical"]
    title: str
    description: str
    guideline_source: str


class ClinicalInterpretation(BaseModel):
    status: Literal["normal", "elevated_risk", "diabetes_range", "hypoglycemia_risk", "requires_clinical_review"]
    summary: str
    flags: list[ClinicalFlag] = Field(default_factory=list)
    requires_confirmatory_testing: bool = False
    guideline_sources: list[str] = Field(default_factory=list)


def evaluate_clinical_interpretation(patient: DiabetesPatientInput) -> ClinicalInterpretation:
    """Interprets clinical measurements against WHO (2006, 2011, 2019) and ADA (2024) criteria.
    
    This layer operates INDEPENDENTLY of the machine learning model.
    """
    flags: list[ClinicalFlag] = []
    sources = set()
    status: str = "normal"
    requires_confirmation = False

    # 1. Hypoglycemia check
    if patient.blood_glucose_level < 70:
        status = "hypoglycemia_risk"
        flags.append(ClinicalFlag(
            category="Blood Glucose",
            severity="critical",
            title="Hypoglycemia Warning",
            description=f"Blood glucose is low ({patient.blood_glucose_level} mg/dL). Clinically urgent if symptoms are present.",
            guideline_source="WHO Guidelines for Management of Diabetes Mellitus"
        ))
        sources.add("WHO Guidelines for Management of Diabetes Mellitus")

    # 2. HbA1c Clinical Assessment (WHO 2011 / ADA 2024)
    # Diagnostic cutoff: HbA1c >= 6.5% (48 mmol/mol)
    # Impaired / Pre-diabetes: 5.7% - 6.4%
    if patient.hba1c_level >= 6.5:
        status = "diabetes_range"
        requires_confirmation = True
        flags.append(ClinicalFlag(
            category="HbA1c",
            severity="critical",
            title="HbA1c in Diabetes Range",
            description=(
                f"HbA1c of {patient.hba1c_level}% meets the diagnostic threshold for diabetes (≥6.5%). "
                "In asymptomatic individuals, repeat laboratory testing on a separate day is required for clinical confirmation."
            ),
            guideline_source="WHO (2011) Use of Glycated Haemoglobin (HbA1c) in the Diagnosis of Diabetes Mellitus"
        ))
        sources.add("WHO (2011) Use of Glycated Haemoglobin (HbA1c) in the Diagnosis of Diabetes Mellitus")
    elif 5.7 <= patient.hba1c_level <= 6.4:
        if status != "diabetes_range":
            status = "elevated_risk"
        flags.append(ClinicalFlag(
            category="HbA1c",
            severity="warning",
            title="HbA1c in Pre-Diabetes / High-Risk Range",
            description=(
                f"HbA1c of {patient.hba1c_level}% indicates intermediate hyperglycemia (5.7%–6.4%), "
                "associated with a high risk of progression to Type 2 diabetes."
            ),
            guideline_source="ADA (2024) Standards of Care / WHO (2019) Classification of Diabetes"
        ))
        sources.add("ADA Standards of Care in Diabetes (2024)")

    # 3. Blood Glucose Contextual Evaluation
    ctx = patient.glucose_context.lower() if patient.glucose_context else "unknown"
    bg = patient.blood_glucose_level

    if ctx == "fasting":
        sources.add("WHO (2006/2019) Definition and Diagnosis of Diabetes Mellitus")
        if bg >= 126:
            status = "diabetes_range"
            requires_confirmation = True
            flags.append(ClinicalFlag(
                category="Fasting Glucose",
                severity="critical",
                title="Fasting Glucose in Diabetes Range",
                description=(
                    f"Fasting blood glucose ({bg} mg/dL) meets the diagnostic threshold (≥126 mg/dL, 7.0 mmol/L). "
                    "Clinical evaluation and confirmatory testing are recommended."
                ),
                guideline_source="WHO (2006/2019) Definition and Diagnosis of Diabetes Mellitus"
            ))
        elif 100 <= bg < 126:
            if status != "diabetes_range":
                status = "elevated_risk"
            flags.append(ClinicalFlag(
                category="Fasting Glucose",
                severity="warning",
                title="Impaired Fasting Glucose (Pre-Diabetes Range)",
                description=(
                    f"Fasting blood glucose ({bg} mg/dL) reflects impaired fasting glucose (100–125 mg/dL). "
                    "Lifestyle intervention and regular monitoring are advised."
                ),
                guideline_source="WHO (2006) / ADA (2024) Diagnostic Criteria"
            ))
    elif ctx == "two_hour_ogtt":
        sources.add("WHO (2006) Definition and Diagnosis of Diabetes Mellitus")
        if bg >= 200:
            status = "diabetes_range"
            requires_confirmation = True
            flags.append(ClinicalFlag(
                category="2-Hour OGTT",
                severity="critical",
                title="2-Hour OGTT Glucose in Diabetes Range",
                description=(
                    f"2-Hour oral glucose tolerance test value ({bg} mg/dL) meets the diagnostic threshold (≥200 mg/dL, 11.1 mmol/L)."
                ),
                guideline_source="WHO (2006) Definition and Diagnosis of Diabetes Mellitus"
            ))
        elif 140 <= bg < 200:
            if status != "diabetes_range":
                status = "elevated_risk"
            flags.append(ClinicalFlag(
                category="2-Hour OGTT",
                severity="warning",
                title="Impaired Glucose Tolerance (IGT)",
                description=f"2-Hour OGTT glucose ({bg} mg/dL) indicates impaired glucose tolerance (140–199 mg/dL).",
                guideline_source="WHO (2006) Definition and Diagnosis of Diabetes Mellitus"
            ))
    elif ctx == "random":
        sources.add("WHO (2006/2019) Definition and Diagnosis of Diabetes Mellitus")
        if bg >= 200:
            status = "diabetes_range"
            requires_confirmation = True
            flags.append(ClinicalFlag(
                category="Random Glucose",
                severity="critical",
                title="Markedly Elevated Random Blood Glucose",
                description=(
                    f"Random blood glucose ({bg} mg/dL) is ≥200 mg/dL. In the presence of symptoms "
                    "(e.g., polyuria, polydipsia, unexplained weight loss), this supports a clinical diagnosis of diabetes."
                ),
                guideline_source="WHO (2006/2019) Definition and Diagnosis of Diabetes Mellitus"
            ))
        elif bg >= 140:
            if status != "diabetes_range":
                status = "elevated_risk"
            flags.append(ClinicalFlag(
                category="Random Glucose",
                severity="warning",
                title="Elevated Random Glucose",
                description=f"Random glucose ({bg} mg/dL) is elevated above normal resting levels (<140 mg/dL). Formal fasting or HbA1c testing is recommended.",
                guideline_source="WHO (2006) Definition and Diagnosis of Diabetes Mellitus"
            ))
    else:  # unknown context
        if bg >= 200:
            status = "diabetes_range"
            requires_confirmation = True
            flags.append(ClinicalFlag(
                category="Blood Glucose (Context Unspecified)",
                severity="critical",
                title="Elevated Glucose (Context Unspecified)",
                description=(
                    f"Blood glucose is {bg} mg/dL. Regardless of fasting state, values ≥200 mg/dL indicate hyperglycemia "
                    "warranting comprehensive medical evaluation."
                ),
                guideline_source="WHO (2006) Definition and Diagnosis of Diabetes Mellitus"
            ))
        elif bg >= 126:
            if status != "diabetes_range":
                status = "requires_clinical_review"
            flags.append(ClinicalFlag(
                category="Blood Glucose (Context Unspecified)",
                severity="warning",
                title="Elevated Blood Glucose",
                description=(
                    f"Blood glucose is {bg} mg/dL. If taken while fasting, this reaches diabetes diagnostic range (≥126 mg/dL). "
                    "Clarify meal timing with a healthcare professional."
                ),
                guideline_source="WHO (2006) / ADA (2024)"
            ))

    # 4. BMI Clinical Assessment (WHO Classification)
    if patient.bmi >= 30.0:
        flags.append(ClinicalFlag(
            category="BMI",
            severity="warning",
            title="Obesity (BMI ≥ 30 kg/m²)",
            description=f"BMI of {patient.bmi} kg/m² falls in the obesity category, a significant modifiable risk factor for insulin resistance.",
            guideline_source="WHO Body Mass Index Classification"
        ))
        sources.add("WHO Body Mass Index Classification")
    elif 25.0 <= patient.bmi < 30.0:
        flags.append(ClinicalFlag(
            category="BMI",
            severity="info",
            title="Overweight (BMI 25.0–29.9 kg/m²)",
            description=f"BMI of {patient.bmi} kg/m² indicates overweight status.",
            guideline_source="WHO Body Mass Index Classification"
        ))
        sources.add("WHO Body Mass Index Classification")

    # 5. Cardiovascular & Blood Pressure Flags
    if patient.hypertension == 1:
        flags.append(ClinicalFlag(
            category="Hypertension",
            severity="info",
            title="Hypertension History Reported",
            description="High blood pressure substantially increases cardiovascular risk in patients with altered glucose metabolism.",
            guideline_source="WHO Package of Essential Noncommunicable Disease Interventions (PEN)"
        ))
        sources.add("WHO Package of Essential Noncommunicable Disease Interventions (PEN)")

    if patient.heart_disease == 1:
        flags.append(ClinicalFlag(
            category="Cardiovascular Disease",
            severity="warning",
            title="Established Heart Disease History",
            description="Personal history of cardiovascular disease requires coordinated vascular and metabolic protection.",
            guideline_source="WHO Global Report on Diabetes (2016)"
        ))
        sources.add("WHO Global Report on Diabetes (2016)")

    # 6. HbA1c Reliability caveat
    if not patient.hba1c_lab_confirmed:
        flags.append(ClinicalFlag(
            category="HbA1c Quality",
            severity="info",
            title="HbA1c Assay Quality Notice",
            description="HbA1c was reported without confirmation of a standardized, NGSP-certified laboratory method.",
            guideline_source="WHO (2011) Diagnostic Recommendations"
        ))

    summary_texts = {
        "diabetes_range": "One or more clinical measurements meet established diagnostic laboratory thresholds for diabetes.",
        "elevated_risk": "Measurements reflect intermediate hyperglycemia or elevated metabolic risk (pre-diabetes range).",
        "hypoglycemia_risk": "Low blood glucose detected requiring clinical attention.",
        "requires_clinical_review": "Measurements are borderline or elevated with unconfirmed measurement context.",
        "normal": "Measurements are within standard physiological reference ranges."
    }

    return ClinicalInterpretation(
        status=status,
        summary=summary_texts.get(status, "Clinical assessment completed."),
        flags=flags,
        requires_confirmatory_testing=requires_confirmation,
        guideline_sources=sorted(list(sources))
    )
