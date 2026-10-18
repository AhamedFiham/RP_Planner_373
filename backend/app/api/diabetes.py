
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.schemas.diabetes_schema import (
    DiabetesPredictionRequest,
    DiabetesPredictionResponse,
)
from app.services.diabetes_service import assess_diabetes


router = APIRouter(
    prefix="/diabetes",
    tags=["diabetes"],
)


@router.post(
    "/predict",
    response_model=DiabetesPredictionResponse,
)
def predict_diabetes(
    request: DiabetesPredictionRequest,
):
    try:
        values = request.model_dump()

        result = assess_diabetes(values)

        return result

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="The trained model or required research data is unavailable.",
        ) from exc

    except (ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Keep detailed internal errors out of the response.
        # The server logs should be used for debugging.
        import logging

        logging.getLogger(__name__).exception(
            "Diabetes assessment failed"
        )

        raise HTTPException(
            status_code=500,
            detail="The diabetes assessment could not be completed.",
        ) from exc
