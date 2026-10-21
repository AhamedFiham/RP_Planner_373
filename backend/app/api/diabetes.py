"""API endpoints for explainable diabetes risk prediction and clinical awareness."""
import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, status
from jose import jwt

from app.schemas.diabetes_schema import DiabetesPatientInput
from app.services.diabetes_service import diabetes_service, DiabetesAssessmentResponse

router = APIRouter(prefix="/diabetes", tags=["diabetes"])

METADATA_PATH = Path(__file__).resolve().parents[2] / "trained_models" / "diabetes" / "model_metadata.json"
METRICS_PATH = Path(__file__).resolve().parents[2] / "trained_models" / "diabetes" / "metrics.json"


def _extract_user_email(authorization: Optional[str]) -> Optional[str]:
    """Extracts email from Bearer token if provided, without rejecting unauthenticated requests."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        from app.api.auth import SECRET, ALGORITHM
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return payload.get("sub") or payload.get("email")
    except Exception:
        return None


@router.post(
    "/predict",
    response_model=DiabetesAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate patient diabetes risk, clinical guidelines, SHAP explanations, and awareness"
)
def predict_diabetes_risk(
    patient: DiabetesPatientInput,
    authorization: Optional[str] = Header(default=None)
):
    """Executes multi-layer validation, WHO clinical interpretation, ML prediction,

    SHAP explanation, and personalized awareness generation.
    """
    user_email = _extract_user_email(authorization)
    try:
        response = diabetes_service.process_assessment(patient, user_email=user_email)
        return response
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model resource unavailable: {str(fnf)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process assessment: {str(e)}"
        )


@router.get("/history", summary="Fetch previous assessment history")
def get_assessment_history(
    limit: int = Query(default=20, ge=1, le=100),
    authorization: Optional[str] = Header(default=None)
):
    user_email = _extract_user_email(authorization)
    return diabetes_service.get_history(user_email=user_email, limit=limit)


@router.get("/assessment/{assessment_id}", summary="Fetch specific assessment by ID")
def get_assessment_detail(assessment_id: str):
    record = diabetes_service.get_assessment(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment record not found.")
    return record


@router.get("/model-info", summary="Fetch trained model metadata and performance metrics")
def get_model_info():
    if not METADATA_PATH.exists() or not METRICS_PATH.exists():
        raise HTTPException(status_code=503, detail="Model metadata not yet available.")
    with open(METADATA_PATH, "r") as f:
        meta = json.load(f)
    with open(METRICS_PATH, "r") as f:
        metrics = json.load(f)
    return {
        "metadata": meta,
        "metrics": metrics
    }
