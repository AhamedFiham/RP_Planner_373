"""Per-food Glycemic Load; requires measured GI and validated consumed carbohydrate."""
import json, math
from pathlib import Path
from app.schemas.diet_schema import GlycemicLoadResult
CONFIG=json.loads((Path(__file__).resolve().parents[2]/'config/diet_glycemic_load.json').read_text())
def calculate(gi, consumed):
    gi_value = gi if isinstance(gi,(int,float)) else (getattr(gi,'gi_value',None) if gi is not None else None)
    carb = consumed if isinstance(consumed,(int,float)) else (getattr(consumed,'consumed_available_carbohydrate_g',None) if consumed is not None else None)
    if gi_value is None: return GlycemicLoadResult(gi_value=None,consumed_available_carbohydrate_g=carb,glycemic_load=None,gl_category=None,calculation_status='gi_unavailable')
    if carb is None: return GlycemicLoadResult(gi_value=gi_value,consumed_available_carbohydrate_g=None,glycemic_load=None,gl_category=None,calculation_status='consumed_carbohydrate_unavailable')
    if not math.isfinite(gi_value) or gi_value<=0 or not math.isfinite(carb) or carb<0: return GlycemicLoadResult(gi_value=gi_value,consumed_available_carbohydrate_g=carb,glycemic_load=None,gl_category=None,calculation_status='invalid_input')
    value=gi_value*carb/100
    category='Low' if value<=CONFIG['low_max'] else 'Medium' if value<CONFIG['medium_max'] else 'High'
    return GlycemicLoadResult(gi_value=gi_value,consumed_available_carbohydrate_g=carb,glycemic_load=value,gl_category=category,calculation_status='calculated')
