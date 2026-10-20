"""Separate serving-mass evidence. No default or visual-area-to-gram assumptions."""
import json
import math
from pathlib import Path
from threading import Lock
from app.schemas.diet_schema import ServingWeightEstimate

BACKEND=Path(__file__).resolve().parents[2]
REFERENCE_PATH=BACKEND/'config/diet_serving_weights.json'
CLASSES_PATH=BACKEND/'trained_models/diet/class_names.json'
_lock=Lock()
_reference=None
_WEIGHT_FIELDS={'small_g','medium_g','large_g','grams_per_unit','reference_serving_g'}
_METHODS={'portion_category','count_based','reference_serving','unsupported'}


class ServingWeightConfigurationError(RuntimeError):pass


def load_serving_weights(path=None, classes_path=None):
    try:
        data=json.loads((path or REFERENCE_PATH).read_text())
        names=json.loads((classes_path or CLASSES_PATH).read_text())
        if set(names)!=set(map(str,range(46))) or len(set(names.values()))!=46:
            raise ValueError('Expected a unique 46-class taxonomy')
        if data['schema_version']!=1 or set(data['foods'])!=set(names.values()):
            raise ValueError('Serving references must cover all 46 foods exactly')
        for entry in data['foods'].values():
            method=entry['serving_method']
            if method not in _METHODS or type(entry['validated']) is not bool or type(entry.get('nutrition_mapping_confirmed',False)) is not bool:
                raise ValueError('Invalid serving reference metadata')
            if entry['status'] not in {'available','needs_reference'}:
                raise ValueError('Invalid serving reference status')
            for key in _WEIGHT_FIELDS:
                value=entry.get(key)
                if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<=0):
                    raise ValueError('Serving masses must be positive finite numbers or null')
            relevant={'portion_category':{'small_g','medium_g','large_g'},'count_based':{'grams_per_unit'},'reference_serving':{'reference_serving_g'},'unsupported':set()}[method]
            provisional = entry.get('mapping_status') == 'provisional' and entry['validated'] is False
            preserve_category_metadata = entry.get('mapping_status') == 'validated_reference_serving' and entry['validated'] is True
            allowed = relevant | ({'small_g','medium_g','large_g'} if provisional or preserve_category_metadata else set())
            if any(entry.get(k) is not None for k in _WEIGHT_FIELDS-allowed):
                raise ValueError('Weight fields disagree with serving method')
            has_weight=any(entry.get(k) is not None for k in relevant)
            if has_weight:
                if provisional:
                    if entry['status'] != 'needs_reference':
                        raise ValueError('Provisional weights must remain needs_reference')
                elif not entry['validated'] or entry['status']!='available' or not all(isinstance(entry.get(k),str) and entry[k].strip() for k in ['source_name','source_reference','validation_notes']):
                    raise ValueError('Available weights require sourced, validated mapping evidence')
            elif entry['status']=='available' or entry['validated']:
                raise ValueError('Available/validated status requires a usable serving mass')
            category_weights=[entry.get(k) for k in ['small_g','medium_g','large_g'] if entry.get(k) is not None]
            if category_weights!=sorted(category_weights):raise ValueError('Category weights must be ordered')
            if method=='reference_serving' and has_weight and entry.get('reference_match_confirmed') is not True and entry.get('mapping_status') != 'validated_reference_serving':
                raise ValueError('A reference serving requires evidence or an explicit validated reference-serving status')
        return data
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        raise ServingWeightConfigurationError('Serving-weight references are missing, malformed or lack validated source evidence.') from exc


def get_serving_weights():
    global _reference
    with _lock:
        if _reference is None:_reference=load_serving_weights()
        return _reference


def estimate_serving_weight(food_name, portion_category, count=None, *, count_ambiguous=False):
    entry=get_serving_weights()['foods'].get(food_name)
    if entry is None:
        return ServingWeightEstimate(serving_method='unsupported',serving_weight_status='needs_reference',notes=['No exact food-name serving reference exists.'])
    method=entry['serving_method']
    base=dict(serving_method=method,source_name=entry.get('source_name'),source_reference=entry.get('source_reference'),validation_notes=entry.get('validation_notes'),nutrition_mapping_confirmed=entry.get('nutrition_mapping_confirmed',False))
    if entry['status']!='available' or entry['validated'] is not True:
        return ServingWeightEstimate(**base,serving_weight_status='needs_reference',notes=['Visual size and CSV reference quantities do not establish detected serving mass.'])
    weight=None;status='needs_reference';notes=[]
    if method=='portion_category':
        key={'Small':'small_g','Medium':'medium_g','Large':'large_g'}.get(portion_category)
        weight=entry.get(key) if key else None
        if not key:status='portion_unknown'
    elif method=='count_based':
        if count_ambiguous or type(count) is not int or count<=0:
            status='count_unavailable'
        elif entry.get('grams_per_unit') is not None:
            weight=count*entry['grams_per_unit']
            notes.append('Count × sourced grams per unit; individual-unit interpretation must be established by the reference evidence.')
    elif method=='reference_serving':
        if entry.get('reference_match_confirmed') is True and entry.get('matching_portion_category')==portion_category:
            weight=entry.get('reference_serving_g')
            notes.append('One reference serving matched using explicit validated mapping evidence, not inferred from nutrition_basis.')
        else:status='portion_unknown'
    else:status='unsupported'
    if weight is not None and not math.isfinite(weight):raise ServingWeightConfigurationError('Calculated serving weight is non-finite.')
    return ServingWeightEstimate(**base,estimated_serving_weight_g=weight,serving_weight_status='available' if weight is not None else status,validated=weight is not None,notes=notes)
