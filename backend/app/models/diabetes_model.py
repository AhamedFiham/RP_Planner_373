"""Domain model definitions for diabetes risk assessment records."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class DiabetesAssessmentModel(BaseModel):
    id: str
    user_email: Optional[str] = None
    timestamp: str
    prediction_label: str
    probability: float
    threshold: float
    model_version: str
    clinical_status: str
    input_data: dict[str, Any]
    clinical_assessment: dict[str, Any]
    explainability: dict[str, Any]
    risk_factors: dict[str, Any]
    personalized_awareness: dict[str, Any]
