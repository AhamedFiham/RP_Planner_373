"""Food-detection endpoints for the diet component."""
import logging
from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from app.schemas.diet_schema import DietModelInfo, FoodDetectionResponse
from app.services import diet_service
from app.utils.image_processing import MAX_IMAGE_BYTES, decode_image, validate_image_upload

class DietRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def checked(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                if any(tuple(error['loc']) == ('body', 'image') for error in exc.errors()):
                    raise HTTPException(status_code=400, detail='Image must be an uploaded file with a filename.') from None
                raise
        return checked


router = APIRouter(prefix='/diet', tags=['diet'], route_class=DietRoute)
logger = logging.getLogger(__name__)


def _process(data: bytes, image_format: str):
    try:
        image = decode_image(data, image_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return diet_service.detect_food(image)
    finally:
        image.close()


@router.post('/detect-food', response_model=FoodDetectionResponse,
             responses={400: {'description': 'Missing, empty, unsupported or invalid image'},
                        500: {'description': 'Model loading or inference failure'}})
async def detect_food(image: UploadFile | None = File(default=None)):
    if image is None:
        raise HTTPException(status_code=400, detail='Image file is required (form field: image).')
    try:
        try:
            image_format = validate_image_upload(image.filename, image.content_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        data = await image.read(MAX_IMAGE_BYTES + 1)
        return await run_in_threadpool(_process, data, image_format)
    except HTTPException:
        raise
    except Exception:
        logger.exception('Diet detection request failed')
        raise HTTPException(status_code=500, detail='Food detection is unavailable. Please try again later.') from None
    finally:
        await image.close()


@router.get('/model-info', response_model=DietModelInfo)
def model_info():
    try:
        return diet_service.model_info()
    except Exception:
        logger.exception('Diet model information unavailable')
        raise HTTPException(status_code=500, detail='Diet model information is unavailable.') from None
