"""Null-safe available-carbohydrate references; never infer total carbohydrate."""
import csv, math
from pathlib import Path
from threading import Lock
from app.schemas.diet_schema import ConsumedAvailableCarbohydrate, AvailableCarbohydrateResponse
from app.services.serving_weight_service import get_serving_weights, estimate_serving_weight
BACKEND=Path(__file__).resolve().parents[2]
CSV_PATH=BACKEND/'datasets/diet/raw/diet_available_carbohydrate_46_classes.csv'
CLASSES=BACKEND/'trained_models/diet/class_names.json'
_lock=Lock(); _catalog=None

def _load():
 with CLASSES.open() as f:
  import json; names={int(k):v for k,v in json.load(f).items()}
 with CSV_PATH.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 if len(rows)!=46 or {int(r['class_id']) for r in rows}!=set(range(46)) or len({r['food_name'] for r in rows})!=46: raise ValueError('Available carbohydrate CSV must contain exactly 46 unique detector classes')
 out={}
 for r in rows:
  if names[int(r['class_id'])]!=r['food_name']: raise ValueError('Available carbohydrate taxonomy mismatch')
  value=r.get('available_carbohydrate_g','').strip() or None
  if value is not None and (float(value)<0 or not math.isfinite(float(value))): raise ValueError('Invalid available carbohydrate value')
  out[r['food_name']]={'reference_value_g':float(value) if value is not None else None,'basis':r.get('carbohydrate_basis') or 'unknown','source_food_name':r.get('source_food_name') or None,'source_name':r.get('source_name') or None,'source_url':r.get('source_url') or None,'mapping_status':r.get('mapping_status','needs_source'),'validated':r.get('validated','False').lower()=='true','notes':r.get('notes') or None}
 return out

def get_catalog():
 global _catalog
 with _lock:
  if _catalog is None: _catalog=_load()
  return _catalog

def reference_for(food_name):
 return get_catalog().get(food_name, {'reference_value_g':None,'basis':'unknown','source_food_name':None,'source_name':None,'source_url':None,'mapping_status':'needs_source','validated':False,'notes':'No exact available-carbohydrate reference exists.'})

def consumed_for(food_name, portion_category, count=None, count_ambiguous=False):
 ref=reference_for(food_name); value=ref['reference_value_g']
 if value is None: return ConsumedAvailableCarbohydrate(reference_value_g=None,reference_basis=ref['basis'],calculation_status='reference_unavailable',validated=False)
 weight=estimate_serving_weight(food_name,portion_category,count,count_ambiguous=count_ambiguous)
 if weight.estimated_serving_weight_g is None: return ConsumedAvailableCarbohydrate(reference_value_g=value,reference_basis=ref['basis'],calculation_status='serving_weight_unavailable',validated=False)
 if not weight.validated: return ConsumedAvailableCarbohydrate(reference_value_g=value,reference_basis=ref['basis'],estimated_serving_weight_g=weight.estimated_serving_weight_g,calculation_status='unvalidated_serving_weight',validated=False)
 if ref['basis']=='per_100g':
  return ConsumedAvailableCarbohydrate(reference_value_g=value,reference_basis='per_100g',estimated_serving_weight_g=weight.estimated_serving_weight_g,consumed_available_carbohydrate_g=value*weight.estimated_serving_weight_g/100,calculation_status='calculated',validated=True)
 return ConsumedAvailableCarbohydrate(reference_value_g=value,reference_basis=ref['basis'],estimated_serving_weight_g=weight.estimated_serving_weight_g,calculation_status='per_serving_reference_unavailable',validated=False)

def estimate(result):
 refs={}
 for food in result.foods:
  key=(food.class_id,food.food_name)
  if key not in refs: refs[key]=consumed_for(food.food_name, food.portion.portion_category, food.portion.count, food.portion.count_ambiguous)
 payload=result.model_dump(); payload['foods']=[{**food.model_dump(),'available_carbohydrate':refs[(food.class_id,food.food_name)]} for food in result.foods]
 return AvailableCarbohydrateResponse(**payload)
