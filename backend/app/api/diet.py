"""Food-detection endpoints for the diet component."""
import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from app.schemas.diet_schema import DietModelInfo, FoodDetectionResponse, PortionEstimationResponse, NutritionMappingResponse, ConsumedNutritionResponse, MealGuidanceResponse, GIMappingResponse, AvailableCarbohydrateResponse, GlycemicLoadResponse
from app.services import diet_service, portion_estimation_service, nutrition_mapping_service, consumed_nutrition_service, fast_food_guidance_service, gi_mapping_service, available_carbohydrate_service, glycemic_load_service, personalized_diet_recommendation_service
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


@router.post('/estimate-portions', response_model=PortionEstimationResponse,
             responses={400: {'description': 'Missing, empty, unsupported or invalid image'},
                        500: {'description': 'Detection or portion configuration failure'}})
async def estimate_portions(image: UploadFile | None = File(default=None)):
    # Reuse the existing bounded upload validation and singleton detector unchanged.
    detection = await detect_food(image)
    try:
        return await run_in_threadpool(portion_estimation_service.estimate_from_detection, detection)
    except Exception:
        logger.exception('Diet portion estimation request failed')
        raise HTTPException(status_code=500, detail='Portion estimation is unavailable. Please try again later.') from None


@router.post('/map-nutrition', response_model=NutritionMappingResponse,
             responses={400: {'description': 'Missing, empty, unsupported or invalid image'},
                        500: {'description': 'Detection, portion or nutrition configuration failure'}})
async def map_nutrition(image: UploadFile | None = File(default=None)):
    portions = await estimate_portions(image)
    try:
        return await run_in_threadpool(nutrition_mapping_service.map_nutrition, portions)
    except Exception:
        logger.exception('Diet nutrition reference mapping request failed')
        raise HTTPException(status_code=500, detail='Nutrition reference mapping is unavailable. Please try again later.') from None


@router.post('/map-gi', response_model=GIMappingResponse,
             responses={400: {'description': 'Missing, empty, unsupported or invalid image'},
                        500: {'description': 'Detection, portion, nutrition or GI configuration failure'}})
async def map_gi(image: UploadFile | None = File(default=None)):
    mapped = await map_nutrition(image)
    try:
        return await run_in_threadpool(gi_mapping_service.map_gi, mapped)
    except Exception:
        logger.exception('Diet GI reference mapping request failed')
        raise HTTPException(status_code=500, detail='GI reference mapping is unavailable. Please try again later.') from None


@router.post('/estimate-available-carbohydrate', response_model=AvailableCarbohydrateResponse)
async def estimate_available_carbohydrate(image: UploadFile | None = File(default=None)):
    mapped = await map_nutrition(image)
    try:
        consumed = await run_in_threadpool(consumed_nutrition_service.estimate_consumed_nutrition, mapped)
        return await run_in_threadpool(available_carbohydrate_service.estimate, consumed)
    except Exception:
        logger.exception('Available carbohydrate estimation failed')
        raise HTTPException(status_code=500, detail='Available carbohydrate estimation is unavailable. Please try again later.') from None


@router.post('/estimate-consumed-nutrition', response_model=ConsumedNutritionResponse,
             responses={400: {'description': 'Invalid or missing image'},
                        500: {'description': 'Analysis or serving-reference configuration failure'}})
async def estimate_consumed_nutrition(image: UploadFile | None = File(default=None)):
    mapped = await map_nutrition(image)
    try:
        return await run_in_threadpool(consumed_nutrition_service.estimate_consumed_nutrition, mapped)
    except Exception:
        logger.exception('Diet consumed nutrition request failed')
        raise HTTPException(status_code=500, detail='Consumed nutrition estimation is unavailable. Please try again later.') from None


@router.post('/calculate-glycemic-load', response_model=GlycemicLoadResponse)
async def calculate_glycemic_load(image: UploadFile | None = File(default=None)):
    mapped = await map_nutrition(image)
    consumed = await run_in_threadpool(consumed_nutrition_service.estimate_consumed_nutrition, mapped)
    available = await run_in_threadpool(available_carbohydrate_service.estimate, consumed)
    payload = consumed.model_dump()
    av = {(f['class_id'], f['food_name']): f['available_carbohydrate'] for f in available.model_dump()['foods']}
    foods=[]
    for food in consumed.foods:
        gi=gi_mapping_service.gi_for_food(food.food_name, food.class_id)
        ac=av[(food.class_id,food.food_name)]
        foods.append({**food.model_dump(),'available_carbohydrate':ac,'gi':gi.model_dump(),'glycemic_load':glycemic_load_service.calculate(gi, ac).model_dump()})
    payload['foods']=foods
    return payload


@router.post('/analyze-meal-guidance', response_model=MealGuidanceResponse)
async def analyze_meal_guidance(image: UploadFile | None = File(default=None), current_glucose: float = Form(...), glucose_unit: str = Form('mg/dL')):
    if image is None:
        raise HTTPException(status_code=400, detail='Image file is required (form field: image).')
    try:
        state, normalized = await run_in_threadpool(fast_food_guidance_service.glucose_state, current_glucose, glucose_unit)
        mapped = await estimate_consumed_nutrition(image)
        available = await run_in_threadpool(available_carbohydrate_service.estimate, mapped)
        payload = mapped.model_dump()
        available_by_food = {(f['class_id'], f['food_name']): f['available_carbohydrate'] for f in available.model_dump()['foods']}
        payload['current_glucose'] = {'value': current_glucose, 'unit': glucose_unit, 'normalized_mg_dl': normalized, 'state': state}
        for food in payload['foods']:
            food['available_carbohydrate'] = available_by_food.get((food['class_id'], food['food_name']))
            food['fast_food_guidance'] = await run_in_threadpool(fast_food_guidance_service.guidance_for, food['food_name'], current_glucose, glucose_unit)
            food['gi'] = await run_in_threadpool(gi_mapping_service.gi_for_food, food['food_name'], food['class_id'])
            gi_obj = await run_in_threadpool(gi_mapping_service.gi_for_food, food['food_name'], food['class_id'])
            food['glycemic_load'] = glycemic_load_service.calculate(gi_obj, available_by_food.get((food['class_id'], food['food_name']))).model_dump()
            gl_obj = glycemic_load_service.calculate(gi_obj, available_by_food.get((food['class_id'], food['food_name'])))
            food['personalized_recommendation'] = personalized_diet_recommendation_service.build_personalized_recommendation(state, food['food_name'], food.get('portion'), food.get('nutrition'), food.get('consumed_nutrition'), gi_obj, gl_obj).model_dump()
        return payload
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception('Diet meal guidance request failed')
        raise HTTPException(status_code=500, detail='Meal guidance is unavailable. Please try again later.') from None


@router.post('/personalized-recommendation', response_model=MealGuidanceResponse)
async def personalized_recommendation(image: UploadFile | None = File(default=None), current_glucose: float = Form(...), glucose_unit: str = Form('mg/dL')):
    if image is None:
        raise HTTPException(status_code=400, detail='Image file is required (form field: image).')
    try:
        state, normalized = await run_in_threadpool(fast_food_guidance_service.glucose_state, current_glucose, glucose_unit)
        mapped = await estimate_consumed_nutrition(image)
        available = await run_in_threadpool(available_carbohydrate_service.estimate, mapped)
        av = {(f.class_id, f.food_name): f.available_carbohydrate for f in available.foods}
        payload = mapped.model_dump(); payload['current_glucose'] = {'value': current_glucose, 'unit': glucose_unit, 'normalized_mg_dl': normalized, 'state': state}
        foods=[]
        for food in mapped.foods:
            gi = await run_in_threadpool(gi_mapping_service.gi_for_food, food.food_name, food.class_id)
            ac = av[(food.class_id, food.food_name)]; gl = glycemic_load_service.calculate(gi, ac)
            rec = personalized_diet_recommendation_service.build_personalized_recommendation(state, food.food_name, food.portion, food.nutrition, food.consumed_nutrition, gi, gl)
            foods.append({**food.model_dump(), 'available_carbohydrate': ac.model_dump(), 'gi': gi.model_dump(), 'glycemic_load': gl.model_dump(), 'personalized_recommendation': rec.model_dump()})
        payload['foods'] = foods; return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        logger.exception('Personalized diet recommendation failed')
        raise HTTPException(status_code=500, detail='Personalized meal guidance is unavailable. Please try again later.') from None
