"""Exact-match fast-food and glucose-aware meal guidance."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / 'datasets/diet/raw/sri_lankan_fast_food_reference.csv'
CONFIG_PATH = ROOT / 'config/diet_glucose_guidance.json'
ALIASES_PATH = ROOT / 'config/diet_fast_food_aliases.json'

def _bool(v): return str(v).strip().lower() == 'true'
def _load():
    with CSV_PATH.open(encoding='utf-8-sig', newline='') as f: rows=list(csv.DictReader(f))
    ids=[r['fast_food_id'] for r in rows]; names=[r['food_name'] for r in rows]
    if len(ids)!=len(set(ids)) or len(names)!=len(set(names)): raise ValueError('Fast-food IDs and names must be unique')
    return {r['food_name']: r for r in rows}
FOODS = _load()
ALIASES = json.loads(ALIASES_PATH.read_text())
CONFIG = json.loads(CONFIG_PATH.read_text())

def normalize_glucose(value, unit='mg/dL'):
    value=float(value)
    if value < 0: raise ValueError('Glucose level must be non-negative')
    if unit == 'mmol/L': return value * 18
    if unit != 'mg/dL': raise ValueError('Glucose unit must be mg/dL or mmol/L')
    return value

def glucose_state(value, unit='mg/dL'):
    mg=normalize_glucose(value, unit)
    if mg < float(CONFIG['low_threshold_mg_dl']): return 'low', mg
    high=CONFIG.get('high_threshold_mg_dl')
    if high is not None and mg > float(high): return 'high', mg
    return 'not_low', mg

def guidance_for(food_name, current_glucose, glucose_unit='mg/dL'):
    state, mg=glucose_state(current_glucose, glucose_unit)
    matched=ALIASES.get(food_name, food_name)
    row=FOODS.get(matched)
    base={'matched_food_name': matched if row else None, 'display_name': row.get('display_name') if row else None,
          'category': row.get('category') if row else None, 'is_fast_food': bool(row), 'guidance_available': bool(row),
          'fried_food': _bool(row.get('fried_food')) if row else False, 'dessert': _bool(row.get('dessert')) if row else False,
          'sweetened_beverage': _bool(row.get('sweetened_beverage')) if row else False, 'glucose_state': state,
          'general_action': row.get('general_action') if row else None, 'low_glucose_role': row.get('low_glucose_role') if row else None,
          'source_name': row.get('source_name') if row else None, 'source_url': row.get('source_url') if row else None,
          'notes': row.get('notes') if row else None}
    if not row: return base | {'guidance_title': None, 'guidance_message': None}
    if state == 'low':
        base['guidance_title']='Treat Low Glucose First'
        role=row.get('low_glucose_role')
        if role == 'possible_fast_acting_carb_if_measured': base['guidance_message']='Use only a measured portion that provides fast-acting carbohydrate according to your hypo treatment plan.'
        elif role == 'not_preferred_hypoglycemia_treatment': base['guidance_message']='This food is not preferred for treating low glucose. Use a fast-acting carbohydrate source according to your hypo treatment plan.'
        else: base['guidance_message']='Treat the low glucose first. This food should not be used as the treatment.'
    elif state == 'high' and row.get('high_glucose_message'):
        base['guidance_title']='Choose a Lower-Carbohydrate Option'; base['guidance_message']=row['high_glucose_message']
    else:
        labels={'portion_control':'Watch Your Portion','limit_or_modify':'Choose Carefully','avoid_or_rare':'Best as an Occasional Choice'}
        base['guidance_title']=labels.get(row.get('general_action'),'Meal Guidance'); base['guidance_message']=row.get('in_range_message') or row.get('general_action')
    return base

def all_foods(): return FOODS
