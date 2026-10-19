# """Request and response validation for the diabetes component."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DiabetesPredictionRequest(BaseModel):
    """Validated input for one diabetes model assessment."""

    model_config = ConfigDict(extra="forbid")

    Pregnancies: Optional[int] = Field(default=0, ge=0, le=100)
    Glucose: float = Field(ge=0, le=1000)
    BloodPressure: float = Field(ge=0, le=500)
    SkinThickness: float = Field(ge=0, le=300)
    Insulin: float = Field(ge=0, le=5000)
    BMI: float = Field(ge=0, le=200)
    DiabetesPedigreeFunction: float = Field(ge=0, le=100)
    Age: int = Field(ge=1, le=120)


class DiabetesPredictionResponse(BaseModel):
    """Prediction and explanation returned by the API."""

    predicted_class: int
    probability_class_1: float
    model_name: str
    explanations: list[dict]
    awareness: dict
    disclaimer: str
