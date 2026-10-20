"""Food detection responses; boxes use pixels in the decoded input image."""
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    x1: float = Field(ge=0, allow_inf_nan=False)
    y1: float = Field(ge=0, allow_inf_nan=False)
    x2: float = Field(gt=0, allow_inf_nan=False)
    y2: float = Field(gt=0, allow_inf_nan=False)

    @model_validator(mode='after')
    def ordered(self):
        if self.x1 >= self.x2 or self.y1 >= self.y2:
            raise ValueError('Bounding box must have positive width and height')
        return self


class FoodDetection(BaseModel):
    class_id: int = Field(ge=0, le=45)
    food_name: str
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    bounding_box: BoundingBox


class FoodDetectionResponse(BaseModel):
    success: bool = True
    detection_count: int = Field(ge=0)
    detections: list[FoodDetection]
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    model_name: str
    confidence_threshold: float = Field(ge=0, le=1)


class DietModelInfo(BaseModel):
    selected_model: str
    dataset_version: str
    class_count: int
    input_image_size: int
    confidence_threshold: float


# V1 deliberately has no numeric gram output or validated serving-size claims.

class PortionEstimate(BaseModel):
    method: Literal['area_based', 'count_based', 'reference_based']
    relative_area: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    count: int | None = Field(default=None, ge=0)
    portion_category: Literal['Small', 'Medium', 'Large', 'Unknown', 'Needs Calibration']
    estimated_grams: None = None
    validated: Literal[False] = False
    calibration_type: Literal['visual_research_baseline'] = 'visual_research_baseline'
    calibration_status: str = 'unknown'
    count_ambiguous: bool = False
    notes: list[str] = Field(default_factory=list)


class FoodDetectionWithPortion(FoodDetection):
    portion: PortionEstimate


class PortionSummary(PortionEstimate):
    class_id: int = Field(ge=0, le=45)
    food_name: str
    observed_detection_count: int = Field(ge=1)


class PortionEstimationResponse(BaseModel):
    success: bool = True
    detection_count: int = Field(ge=0)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    foods: list[FoodDetectionWithPortion]
    portion_summary: list[PortionSummary]
    model_name: str
    confidence_threshold: float = Field(ge=0, le=1)


NUTRITION_NUMERIC_FIELDS = ('energy_kcal', 'energy_kj', 'water_g', 'carbohydrates_g', 'fat_g', 'sfa_g', 'mufa_g', 'pufa_g', 'proteins_g', 'fiber_g', 'vitamin_a_ug', 'vitamin_b1_mg', 'vitamin_b2_mg', 'vitamin_b3_mg', 'vitamin_b6_mg', 'vitamin_b12_mg', 'folate_ug', 'vitamin_c_mg', 'vitamin_d_ug', 'vitamin_e_mg', 'vitamin_k_ug', 'calcium_mg', 'magnesium_mg', 'phosphorus_mg', 'sodium_mg', 'potassium_mg', 'iron_mg', 'zinc_mg', 'selenium_ug', 'copper_mg', 'manganese_mg', 'original_serving_quantity', 'original_energy_kcal', 'original_carbohydrates_g', 'original_proteins_g', 'original_fat_g')


class NutritionReference(BaseModel):
    nutrition_basis: Literal['per_100g', 'per_serving'] | None = None
    energy_kcal: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    energy_kj: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    water_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    carbohydrates_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    fat_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    sfa_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    mufa_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    pufa_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    proteins_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    fiber_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_a_ug: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_b1_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_b2_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_b3_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_b6_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_b12_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    folate_ug: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_c_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_d_ug: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_e_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    vitamin_k_ug: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    calcium_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    magnesium_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    phosphorus_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    sodium_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    potassium_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    iron_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    zinc_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    selenium_ug: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    copper_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    manganese_mg: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    original_serving_quantity: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    original_energy_kcal: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    original_carbohydrates_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    original_proteins_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    original_fat_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    source_food_name: str | None = None
    mapping_status: str
    data_completeness: str
    source_name: str | None = None
    notes: str | None = None
    original_serving_unit: str | None = None
    supplemental_source: str | None = None
    mapping_warning: str | None = None
    data_quality_warnings: list[str] = Field(default_factory=list)


class FoodWithNutrition(FoodDetectionWithPortion):
    nutrition: NutritionReference


class NutritionMappingResponse(PortionEstimationResponse):
    foods: list[FoodWithNutrition]


class ServingWeightEstimate(BaseModel):
    serving_method: Literal['portion_category', 'count_based', 'reference_serving', 'unsupported']
    estimated_serving_weight_g: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    serving_weight_status: Literal['available', 'needs_reference', 'count_unavailable', 'portion_unknown', 'unsupported']
    validated: bool = False
    source_name: str | None = None
    source_reference: str | None = None
    validation_notes: str | None = None
    nutrition_mapping_confirmed: bool = False
    notes: list[str] = Field(default_factory=list)


class ConsumedNutrition(BaseModel):
    energy_kcal: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    energy_kj: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    carbohydrates_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    proteins_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    fat_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    fiber_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    scaling_factor: float = Field(gt=0, allow_inf_nan=False)
    calculation_basis: Literal['per_100g_weight_scaling', 'per_serving_gram_scaling_approximation']
    notes: list[str] = Field(default_factory=list)


class ConsumedFoodSummary(BaseModel):
    class_id: int = Field(ge=0, le=45)
    food_name: str
    confidence: float = Field(ge=0, le=1)
    portion: PortionSummary
    nutrition: NutritionReference
    serving_weight: ServingWeightEstimate
    consumed_nutrition: ConsumedNutrition | None = None
    consumed_nutrition_status: str
    detection_count: int = Field(ge=1)
    detection_indices: list[int]


class ConsumedNutritionResponse(BaseModel):
    success: bool = True
    detection_count: int = Field(ge=0)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    detections: list[FoodWithNutrition]
    foods: list[ConsumedFoodSummary]
    portion_summary: list[PortionSummary]
    model_name: str
    confidence_threshold: float = Field(ge=0, le=1)

class FastFoodGuidance(BaseModel):
    matched_food_name: str | None = None
    display_name: str | None = None
    category: str | None = None
    is_fast_food: bool = False
    guidance_available: bool = False
    fried_food: bool = False
    dessert: bool = False
    sweetened_beverage: bool = False
    glucose_state: Literal['low', 'not_low', 'high']
    guidance_title: str | None = None
    guidance_message: str | None = None
    general_action: str | None = None
    low_glucose_role: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    notes: str | None = None

class GlucoseReading(BaseModel):
    value: float = Field(ge=0)
    unit: Literal['mg/dL', 'mmol/L']
    normalized_mg_dl: float = Field(ge=0)
    state: Literal['low', 'not_low', 'high']

class GIReference(BaseModel):
    gi_value: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    gi_category: Literal['Low', 'Medium', 'High'] | None = None
    source_food_name: str | None = None
    mapping_status: Literal['matched', 'representative', 'candidate', 'needs_source']
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    notes: str | None = None

class FoodWithGI(FoodWithNutrition):
    gi: GIReference

class GIMappingResponse(NutritionMappingResponse):
    foods: list[FoodWithGI]

class AvailableCarbohydrateReference(BaseModel):
    reference_value_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    basis: Literal['per_100g', 'per_serving', 'unknown'] | None = None
    source_food_name: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    mapping_status: str
    validated: bool = False
    notes: str | None = None

class ConsumedAvailableCarbohydrate(BaseModel):
    reference_value_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    reference_basis: Literal['per_100g', 'per_serving', 'unknown'] | None = None
    estimated_serving_weight_g: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    consumed_available_carbohydrate_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    calculation_status: Literal['calculated', 'serving_weight_unavailable', 'reference_unavailable', 'per_serving_reference_unavailable', 'unvalidated_serving_weight']
    validated: bool = False

class FoodWithAvailableCarbohydrate(ConsumedFoodSummary):
    available_carbohydrate: ConsumedAvailableCarbohydrate

class AvailableCarbohydrateResponse(ConsumedNutritionResponse):
    foods: list[FoodWithAvailableCarbohydrate]


class GlycemicLoadResult(BaseModel):
    gi_value: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    consumed_available_carbohydrate_g: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    glycemic_load: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    gl_category: Literal['Low', 'Medium', 'High'] | None = None
    calculation_status: Literal['calculated', 'gi_unavailable', 'consumed_carbohydrate_unavailable', 'invalid_input']
    notes: str | None = None

class PersonalizedDietRecommendation(BaseModel):
    recommendation_title: str
    recommendation_message: str
    recommendation_level: Literal['informational', 'portion_attention', 'higher_attention', 'low_glucose_priority']
    glucose_state: str | None = None
    portion_action: str | None = None
    alternative_suggestion: str | None = None
    factors_used: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

class GuidanceFood(ConsumedFoodSummary):
    fast_food_guidance: FastFoodGuidance
    available_carbohydrate: ConsumedAvailableCarbohydrate | None = None
    gi: GIReference | None = None
    glycemic_load: GlycemicLoadResult | None = None
    personalized_recommendation: PersonalizedDietRecommendation | None = None

class GlycemicLoadFood(ConsumedFoodSummary):
    available_carbohydrate: ConsumedAvailableCarbohydrate | None = None
    gi: GIReference | None = None
    glycemic_load: GlycemicLoadResult

class GlycemicLoadResponse(ConsumedNutritionResponse):
    foods: list[GlycemicLoadFood]

class MealGuidanceResponse(ConsumedNutritionResponse):
    current_glucose: GlucoseReading
    foods: list[GuidanceFood]
