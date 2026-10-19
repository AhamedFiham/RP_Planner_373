"""Read-only nutrition references. No consumed quantities, scaling or unit conversion."""
import csv
import json
import math
from pathlib import Path
from threading import Lock
from app.schemas.diet_schema import (NUTRITION_NUMERIC_FIELDS, NutritionReference,
    NutritionMappingResponse, PortionEstimationResponse)

BACKEND = Path(__file__).resolve().parents[2]
CSV_PATH = BACKEND/'datasets/diet/raw/diet_nutrition_46_classes_v3.csv'
CLASSES_PATH = BACKEND/'trained_models/diet/class_names.json'
_REQUIRED = {'class_id','food_name','mapping_status','nutrition_basis','energy_kcal',
             'carbohydrates_g','proteins_g','fat_g','fiber_g','data_completeness','source_name'}
_STATUSES = {'matched_full','matched_macro','matched_serving','representative_full',
             'candidate_full','candidate_macro','candidate_serving','needs_source'}
_lock = Lock()
_catalog = None


class NutritionConfigurationError(RuntimeError):
    pass


def _text(value):
    return value.strip() or None if value is not None else None


def load_nutrition_reference(csv_path=None, classes_path=None):
    """Uncached validation routine; production uses the locked singleton below."""
    try:
        names = {int(k):v for k,v in json.loads((classes_path or CLASSES_PATH).read_text()).items()}
        if set(names)!=set(range(46)) or len(set(names.values()))!=46:
            raise ValueError('Expected a unique 46-class detector mapping')
        with (csv_path or CSV_PATH).open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle)
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or not _REQUIRED<=set(reader.fieldnames):
                raise ValueError('Required nutrition columns are missing or duplicated')
            rows=list(reader)
        if len(rows)!=46:raise ValueError('Nutrition CSV must contain exactly 46 records')
        result={};seen=set()
        for row in rows:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Malformed CSV record shape')
            cid=int(row['class_id']);name=row['food_name']
            if cid in seen or name in result or names.get(cid)!=name:
                raise ValueError('Nutrition IDs/names do not match the detector taxonomy')
            seen.add(cid)
            status=row['mapping_status'];completeness=row['data_completeness']
            if status not in _STATUSES or completeness not in {'full_macro_micro','macronutrients_only','none'}:
                raise ValueError('Invalid nutrition mapping metadata')
            record={field:_text(row.get(field)) for field in ['nutrition_basis','source_food_name','source_name','notes','original_serving_unit','supplemental_source']}
            for field in NUTRITION_NUMERIC_FIELDS:
                value=_text(row.get(field))
                record[field]=None if value is None else float(value)
                if record[field] is not None and (not math.isfinite(record[field]) or record[field]<0):
                    raise ValueError('Nutrients must be finite non-negative numbers or blank')
            if record['nutrition_basis'] not in {None,'per_100g','per_serving'}:
                raise ValueError('Unsupported nutrition reference basis')
            if status=='needs_source' and (record['nutrition_basis'] is not None or any(record[k] is not None for k in NUTRITION_NUMERIC_FIELDS)):
                raise ValueError('needs_source records must not contain fabricated nutrient values')
            if any(record[k] is not None for k in NUTRITION_NUMERIC_FIELDS) and record['nutrition_basis'] is None:
                raise ValueError('Numeric nutrition values require an explicit basis')
            warning = ('Candidate nutrition mapping; manual confirmation recommended.' if status.startswith('candidate_') else
                       'Representative prepared-food nutrition reference; recipe variation may affect values.' if status=='representative_full' else None)
            quality=[]
            if record['nutrition_basis']=='per_100g' and record['water_g'] is not None and record['water_g']>100:
                quality.append('Source reports water above 100 g for a per-100-g record; source review is required. Values are preserved, not corrected.')
            result[name]=(cid,NutritionReference(**record,mapping_status=status,data_completeness=completeness,
                mapping_warning=warning,data_quality_warnings=quality))
        if seen!=set(range(46)):raise ValueError('Incomplete detector-class coverage')
        return result
    except (OSError,ValueError,TypeError,KeyError,csv.Error) as exc:
        raise NutritionConfigurationError('Nutrition reference configuration is missing, malformed or inconsistent with detector classes.') from exc


def get_nutrition_catalog():
    global _catalog
    with _lock:
        if _catalog is None:_catalog=load_nutrition_reference()
        return _catalog


def nutrition_for_food(food_name: str, class_id: int | None = None) -> NutritionReference:
    catalog=get_nutrition_catalog()
    if food_name not in catalog:
        raise NutritionConfigurationError('No exact detector-name nutrition mapping exists.')
    cid,record=catalog[food_name]
    if class_id is not None and cid!=class_id:
        raise NutritionConfigurationError('Food name and class ID disagree with nutrition reference.')
    return record.model_copy(deep=True)


def map_nutrition(result: PortionEstimationResponse) -> NutritionMappingResponse:
    # Validate/cache even for empty detections; do not sum duplicate references.
    get_nutrition_catalog()
    payload=result.model_dump()
    payload['foods']=[{**food.model_dump(),'nutrition':nutrition_for_food(food.food_name,food.class_id)} for food in result.foods]
    return NutritionMappingResponse(**payload)
