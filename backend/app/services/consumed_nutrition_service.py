"""Per-food estimates only, conditional on separate sourced serving-mass evidence."""
from collections import defaultdict
from app.schemas.diet_schema import ConsumedFoodSummary, ConsumedNutrition, ConsumedNutritionResponse
from app.services.serving_weight_service import estimate_serving_weight, get_serving_weights

CONSUMED_FIELDS=('energy_kcal','energy_kj','carbohydrates_g','proteins_g','fat_g','fiber_g')


def calculate_consumed_nutrition(reference, serving_weight):
    """Return (nullable nutrient object, status). Null never becomes zero."""
    weight=serving_weight.estimated_serving_weight_g
    if weight is None or not serving_weight.validated or serving_weight.serving_weight_status!='available' or not serving_weight.source_name or not serving_weight.source_reference:
        return None,'serving_weight_unavailable'
    if reference.mapping_status=='needs_source':return None,'nutrition_reference_unavailable'
    if (reference.mapping_status.startswith('candidate_') or reference.mapping_status=='representative_full') and not serving_weight.nutrition_mapping_confirmed:
        return None,'nutrition_mapping_requires_confirmation'
    notes=['Consumed nutrition is estimated from a referenced serving weight and food composition data. It is not a laboratory measurement.']
    if reference.nutrition_basis=='per_100g':
        factor=weight/100
        basis='per_100g_weight_scaling'
    elif reference.nutrition_basis=='per_serving' and reference.original_serving_unit=='g' and reference.original_serving_quantity is not None and reference.original_serving_quantity>0:
        factor=weight/reference.original_serving_quantity
        basis='per_serving_gram_scaling_approximation'
        notes.append('Proportional scaling from a gram-denominated reference serving is an approximation and assumes comparable food composition.')
    else:return None,'nutrition_basis_not_scalable'
    values={key:None if getattr(reference,key) is None else getattr(reference,key)*factor for key in CONSUMED_FIELDS}
    if all(value is None for value in values.values()):return None,'nutrition_reference_unavailable'
    if reference.mapping_warning:notes.append(reference.mapping_warning)
    if reference.data_quality_warnings:notes.extend(reference.data_quality_warnings)
    return ConsumedNutrition(**values,scaling_factor=factor,calculation_basis=basis,notes=notes),'estimated'


def estimate_consumed_nutrition(result):
    """Return one mass/nutrient estimate per food; retain raw boxes separately."""
    get_serving_weights()
    groups=defaultdict(list)
    for index,food in enumerate(result.foods):groups[(food.class_id,food.food_name)].append((index,food))
    summaries={(p.class_id,p.food_name):p for p in result.portion_summary}
    foods=[]
    for (cid,name),items in groups.items():
        portion=summaries[(cid,name)]
        weight=estimate_serving_weight(name,portion.portion_category,portion.count,count_ambiguous=portion.count_ambiguous)
        reference=items[0][1].nutrition
        consumed,status=calculate_consumed_nutrition(reference,weight)
        foods.append(ConsumedFoodSummary(class_id=cid,food_name=name,confidence=max(food.confidence for _,food in items),
            portion=portion,nutrition=reference,serving_weight=weight,consumed_nutrition=consumed,consumed_nutrition_status=status,
            detection_count=len(items),detection_indices=[index for index,_ in items]))
    return ConsumedNutritionResponse(success=result.success,detection_count=result.detection_count,
        image_width=result.image_width,image_height=result.image_height,detections=result.foods,foods=foods,
        portion_summary=result.portion_summary,model_name=result.model_name,confidence_threshold=result.confidence_threshold)
