"""Explainable V1 area/count proxies. No inference, grams, nutrition or GI/GL."""
from collections import defaultdict
from pathlib import Path
import json
import math

from app.schemas.diet_schema import (FoodDetection, FoodDetectionResponse,
    FoodDetectionWithPortion, PortionEstimate, PortionEstimationResponse, PortionSummary)

REFERENCE_PATH = Path(__file__).resolve().parents[2] / 'config/portion_reference.json'


class PortionConfigurationError(RuntimeError):
    pass


def load_portion_reference(path: Path | None = None) -> dict:
    """Validate explicit prototype rules; never infer thresholds or serving weights."""
    try:
        config = json.loads((path or REFERENCE_PATH).read_text())
        if config['schema_version'] != 1 or not isinstance(config['foods'], dict):
            raise ValueError('Expected V1 food references')
        baseline = config['research_baseline_thresholds']
        if baseline['validated'] is not False:
            raise ValueError('V1 thresholds must be marked provisional/unvalidated')
        for name, entry in config['foods'].items():
            if not isinstance(name, str) or not name:
                raise ValueError('Invalid food name')
            if not isinstance(entry, dict):
                raise ValueError('Food reference must be an object')
            method = entry['method']
            if method not in {'area_based','count_based','reference_based'}:
                raise ValueError('Unknown portion method')
            if entry['validated'] is not False or entry['serving_weights'] is not None:
                raise ValueError('V1 does not support validated serving weights or grams')
            rules = entry['portion_rules']
            if rules is not None:
                if method == 'reference_based' or entry['threshold_source'] != 'research_baseline_provisional':
                    raise ValueError('Explicit rules must be labelled research_baseline_provisional')
                small, medium = ('small_max_count','medium_max_count') if method == 'count_based' else ('small_max_relative_area','medium_max_relative_area')
                lo, hi = rules[small], rules[medium]
                if method == 'count_based':
                    if type(lo) is not int or type(hi) is not int or not 0 < lo < hi:
                        raise ValueError('Count rules require ordered positive integers')
                elif (type(lo) not in (float,int) or type(hi) not in (float,int)
                      or not math.isfinite(lo) or not math.isfinite(hi) or not 0 < lo < hi <= 1):
                    raise ValueError('Area rules require finite ordered fractions')
        return config
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PortionConfigurationError('Portion references could not be loaded or are invalid.') from exc


def overlap(a, b):
    return min(a.x2,b.x2) > max(a.x1,b.x1) and min(a.y2,b.y2) > max(a.y1,b.y1)


def union_area(boxes):
    """Exact axis-aligned rectangle union; overlapping backgrounds are counted once."""
    xs = sorted({x for b in boxes for x in (b.x1,b.x2)})
    area = 0.0
    for left,right in zip(xs,xs[1:]):
        intervals = sorted((b.y1,b.y2) for b in boxes if b.x1 < right and b.x2 > left)
        covered = 0.0
        end = None
        for low,high in intervals:
            if end is None or low > end:
                covered += high-low
            elif high > end:
                covered += high-end
            end = max(end,high) if end is not None else high
        area += (right-left)*covered
    return area


def category(value, entry):
    rules = entry.get('portion_rules')
    if rules is None or value is None:
        return 'Unknown'
    small,medium = ('small_max_count','medium_max_count') if entry['method']=='count_based' else ('small_max_relative_area','medium_max_relative_area')
    return 'Small' if value <= rules[small] else 'Medium' if value <= rules[medium] else 'Large'


def estimate_portions(detections, image_width, image_height, *, model_name='YOLOv8n', confidence_threshold=.25) -> PortionEstimationResponse:
    """Accept FoodDetection objects or dictionaries; preserve per-detection identities.

Count summaries refer to observed regions, never hidden pieces or verified units.
Any same-class box intersection suppresses a count rather than applying an invented
IoU rule. Individual count-method records defer group counts to portion_summary.
    """
    if type(image_width) is not int or type(image_height) is not int or image_width<=0 or image_height<=0:
        raise ValueError('Image dimensions must be positive integers.')
    items = [FoodDetection.model_validate(d) for d in detections]
    groups = defaultdict(list)
    ids, names = {}, {}
    for d in items:
        if d.bounding_box.x2 > image_width or d.bounding_box.y2 > image_height:
            raise ValueError('Bounding box exceeds input image dimensions.')
        if (d.class_id in ids and ids[d.class_id]!=d.food_name) or (d.food_name in names and names[d.food_name]!=d.class_id):
            raise ValueError('Detection IDs and food names must be consistent.')
        ids[d.class_id],names[d.food_name] = d.food_name,d.class_id
        groups[d.food_name].append(d)
    config = load_portion_reference()
    image_area = image_width * image_height
    summaries, per_food = [], {}
    for name, group in groups.items():
        entry = config['foods'].get(name, {'method':'reference_based','portion_rules':None})
        method = entry['method']
        boxes = [d.bounding_box for d in group]
        ambiguous = method=='count_based' and any(overlap(a,b) for i,a in enumerate(boxes) for b in boxes[i+1:])
        notes = []
        if method=='area_based':
            value = min(1.0,max(0.0,union_area(boxes)/image_area))
            estimate = PortionEstimate(method=method,relative_area=value,portion_category=category(value,entry),
                notes=['Rectangle-union/image area: a visible-area proxy, not food segmentation, volume or mass.'])
        elif method=='count_based':
            count = None if ambiguous else len(group)
            notes = ['Count refers to detected regions; individual food units inside a region are not verified. Hidden pieces are never inferred.']
            if ambiguous:
                notes.append('Same-food boxes overlap; count is withheld because duplicate detections or occluded units cannot be distinguished.')
            estimate = PortionEstimate(method=method,count=count,count_ambiguous=ambiguous,
                portion_category='Unknown' if ambiguous else category(count,entry),notes=notes)
        else:
            estimate = PortionEstimate(method='reference_based',portion_category='Unknown',
                notes=['No reliable area/count rule: a validated serving reference is required.'])
        estimate.calibration_status = entry.get('calibration_status', 'reference_required' if method=='reference_based' else 'not_calibrated')
        if entry.get('portion_rules') is not None:
            estimate.notes.append('Category uses explicit research_baseline_provisional rules; it has not been scientifically validated.')
        summaries.append(PortionSummary(**estimate.model_dump(),class_id=group[0].class_id,
            food_name=name,observed_detection_count=len(group)))
        per_food[name] = (entry,estimate)
    foods = []
    for d in items:
        entry,summary = per_food[d.food_name]
        if summary.method=='area_based':
            b = d.bounding_box
            value = (b.x2-b.x1)*(b.y2-b.y1)/image_area
            portion = PortionEstimate(method='area_based',relative_area=min(1.0,value),portion_category=category(value,entry),
                notes=['Per-detection bounding rectangle/image area. Use portion_summary for non-overlapping same-food coverage.'])
            if entry.get('portion_rules') is not None:
                portion.notes.append('Category uses unvalidated research_baseline_provisional rules.')
        elif summary.method=='count_based':
            portion = PortionEstimate(method='count_based',portion_category=summary.portion_category,
                count_ambiguous=summary.count_ambiguous,notes=['Food-level detected-region count is provided once in portion_summary.'])
        else:
            portion = summary.model_copy(deep=True)
        portion.calibration_status = summary.calibration_status
        foods.append(FoodDetectionWithPortion(**d.model_dump(),portion=portion))
    return PortionEstimationResponse(detection_count=len(items),foods=foods,portion_summary=summaries,
        image_width=image_width,image_height=image_height,model_name=model_name,confidence_threshold=confidence_threshold)


def estimate_from_detection(result: FoodDetectionResponse):
    return estimate_portions(result.detections,result.image_width,result.image_height,
        model_name=result.model_name,confidence_threshold=result.confidence_threshold)
