
from typing import Any


# --------------------------------------------------
# 1. FEATURE INFORMATION
# --------------------------------------------------

FEATURE_GUIDANCE = {
    "Glucose": {
        "category": "potentially_manageable",
        "label": "Glucose measurement",
        "message": (
            "Your glucose measurement contributed to the "
            "model output. Discuss the result with a "
            "qualified healthcare professional and follow "
            "their advice about appropriate glucose testing."
        ),
    },
    "BMI": {
        "category": "potentially_manageable",
        "label": "Body mass index (BMI)",
        "message": (
            "BMI contributed to the model output. If weight "
            "management is appropriate for you, discuss "
            "safe, sustainable options with a healthcare "
            "professional. BMI alone does not determine "
            "whether someone has diabetes."
        ),
    },
    "BloodPressure": {
        "category": "potentially_manageable",
        "label": "Blood pressure measurement",
        "message": (
            "Your blood pressure measurement influenced "
            "the model output. Follow appropriate blood "
            "pressure monitoring and healthcare advice."
        ),
    },
    "Insulin": {
        "category": "clinical_measurement",
        "label": "Insulin measurement",
        "message": (
            "This measurement was unavailable in the "
            "sample because its zero value was treated as "
            "missing. A healthcare professional can advise "
            "whether any additional measurement is needed."
        ),
    },
    "SkinThickness": {
        "category": "clinical_measurement",
        "label": "Skin thickness measurement",
        "message": (
            "This measurement was unavailable in the "
            "sample because its zero value was treated as "
            "missing. It should not be interpreted as an "
            "actual skin thickness of zero."
        ),
    },
    "Age": {
        "category": "non_modifiable",
        "label": "Age",
        "message": (
            "Age is not modifiable. It contributed to the "
            "model output, but it does not determine an "
            "individual's future health on its own."
        ),
    },
    "Pregnancies": {
        "category": "clinical_history",
        "label": "Pregnancy history",
        "message": (
            "Pregnancy history contributed to the model "
            "output. Discuss relevant medical history with "
            "a healthcare professional if appropriate."
        ),
    },
    "DiabetesPedigreeFunction": {
        "category": "family_history_indicator",
        "label": "Diabetes pedigree indicator",
        "message": (
            "This dataset indicator contributed to the "
            "model output. Its exact interpretation depends "
            "on the dataset definition and should not be "
            "treated as a direct diagnosis or a confirmed "
            "family-history assessment."
        ),
    },
}


# --------------------------------------------------
# 2. BUILD AWARENESS FROM ACTUAL SHAP VALUES
# --------------------------------------------------

def generate_awareness(
    explanation: dict[str, Any],
    top_n: int = 3,
) -> dict[str, Any]:

    features = explanation.get("features", [])

    if not isinstance(features, list) or not features:
        raise ValueError(
            "The explanation must contain a non-empty features list."
        )

    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    explained_features = []

    for item in features:
        name = item.get("feature")
        shap_value = item.get("shap_value")

        if name not in FEATURE_GUIDANCE:
            continue

        if not isinstance(shap_value, (int, float)):
            continue

        guidance = FEATURE_GUIDANCE[name]

        explained_features.append({
            "feature": name,
            "label": guidance["label"],
            "observed_value": item.get("observed_value"),
            "shap_value": float(shap_value),
            "direction": (
                "increases_model_output"
                if shap_value > 0
                else "decreases_model_output"
                if shap_value < 0
                else "no_contribution"
            ),
            "category": guidance["category"],
            "awareness_message": guidance["message"],
        })

    # Rank by absolute SHAP contribution.
    explained_features.sort(
        key=lambda item: abs(item["shap_value"]),
        reverse=True,
    )

    highlighted = explained_features[:top_n]

    return {
        "title": "Your personalized diabetes awareness",
        "basis": (
            "Messages are selected from reviewed feature "
            "guidance and ranked model explanations."
        ),
        "highlighted_factors": highlighted,
        "important_notice": (
            "This is an experimental research decision-support "
            "tool, not a medical diagnosis. SHAP values explain "
            "model behaviour and do not establish causation. "
            "Consult a qualified healthcare professional about "
            "personal medical decisions."
        ),
    }
