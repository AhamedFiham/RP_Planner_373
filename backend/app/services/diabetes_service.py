
from app.models.diabetes_model import predict
from app.services.diabetes_explainability_service import (
    explain_prediction,
)
from app.services.diabetes_awareness_service import (
    generate_awareness,
)


DISCLAIMER = (
    "This experimental research system provides model-based "
    "decision support, not a medical diagnosis. Its output "
    "has not been established as clinically validated. "
    "Consult a qualified healthcare professional for medical "
    "assessment and decisions."
)


def assess_diabetes(values: dict) -> dict:
    """Run prediction, explanation and awareness."""

    prediction = predict(values)

    explanations = explain_prediction(values)

    explanation_payload = {
        "predicted_class": prediction["predicted_class"],
        "predicted_probability_class_1": (
            prediction["probability_class_1"]
        ),
        "features": explanations,
    }

    awareness = generate_awareness(
        explanation_payload,
        top_n=3,
    )

    return {
        **prediction,
        "explanations": explanations,
        "awareness": awareness,
        "disclaimer": DISCLAIMER,
    }
