"""Read-only Glycemic Index (GI) references for the 46 Sri Lankan food classes.

Provides food-level reference GI values and categories (Low, Medium, High).
No Glycemic Load, meal averaging, or unvalidated inferences.
"""
import csv
import json
import math
from pathlib import Path
from threading import Lock

from app.schemas.diet_schema import (
    GIReference,
    FoodWithGI,
    GIMappingResponse,
    NutritionMappingResponse,
)

BACKEND = Path(__file__).resolve().parents[2]
CSV_PATH = BACKEND / 'datasets/diet/raw/diet_gi_46_classes.csv'
CLASSES_PATH = BACKEND / 'trained_models/diet/class_names.json'
_REQUIRED = {'class_id', 'food_name', 'mapping_status'}
_STATUSES = {'matched', 'representative', 'candidate', 'needs_source'}
_lock = Lock()
_catalog = None


class GIConfigurationError(RuntimeError):
    """Configuration, parsing or validation failure for GI reference data."""


def _text(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


def load_gi_reference(csv_path: Path | None = None, classes_path: Path | None = None) -> dict:
    """Validate and load GI reference records. Never estimate or invent GI values."""
    try:
        names = {int(k): v for k, v in json.loads((classes_path or CLASSES_PATH).read_text()).items()}
        if set(names) != set(range(46)) or len(set(names.values())) != 46:
            raise ValueError('Expected a unique 46-class detector mapping')

        with (csv_path or CSV_PATH).open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not _REQUIRED <= set(reader.fieldnames):
                raise ValueError('Required GI columns are missing or duplicated')
            rows = list(reader)

        if len(rows) != 46:
            raise ValueError('GI CSV must contain exactly 46 records')

        result = {}
        seen = set()
        for row in rows:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Malformed CSV record shape')

            cid = int(row['class_id'])
            name = row['food_name']
            if cid in seen or name in result or names.get(cid) != name:
                raise ValueError('GI IDs/names do not match the detector taxonomy')
            seen.add(cid)

            status = row['mapping_status']
            if status not in _STATUSES:
                raise ValueError(f'Invalid GI mapping status: {status}')

            raw_gi = _text(row.get('gi_value'))
            raw_cat = _text(row.get('gi_category'))
            source_food_name = _text(row.get('source_food_name'))
            source_name = _text(row.get('source_name'))
            source_url = _text(row.get('source_url'))
            source_type = _text(row.get('source_type'))
            notes = _text(row.get('notes'))

            gi_value = None
            gi_category = None

            if raw_gi is not None:
                gi_value = float(raw_gi)
                if not math.isfinite(gi_value) or gi_value <= 0:
                    raise ValueError(f'GI value must be a positive finite number, got {raw_gi}')
                expected_category = 'Low' if gi_value <= 55 else 'Medium' if gi_value <= 69 else 'High'
                if raw_cat != expected_category:
                    raise ValueError(f'GI category mismatch for {name}: {raw_cat} vs expected {expected_category}')
                gi_category = expected_category
                if status == 'needs_source':
                    raise ValueError(f'{name} has GI value but status is needs_source')
            else:
                if raw_cat is not None:
                    raise ValueError(f'{name} has GI category without a valid GI value')
                if status != 'needs_source':
                    raise ValueError(f'{name} without GI value must have status needs_source')

            record = GIReference(
                gi_value=gi_value,
                gi_category=gi_category,
                source_food_name=source_food_name,
                mapping_status=status,
                source_name=source_name,
                source_url=source_url,
                source_type=source_type,
                notes=notes,
            )
            result[name] = (cid, record)

        if seen != set(range(46)):
            raise ValueError('Incomplete detector-class coverage')

        return result
    except (OSError, ValueError, TypeError, KeyError, csv.Error) as exc:
        raise GIConfigurationError('GI reference configuration is missing, malformed or inconsistent with detector classes.') from exc


def get_gi_catalog() -> dict:
    """Thread-safe singleton catalog loader."""
    global _catalog
    with _lock:
        if _catalog is None:
            _catalog = load_gi_reference()
        return _catalog


def gi_for_food(food_name: str, class_id: int | None = None) -> GIReference:
    """Look up GI reference for a single detector food name."""
    catalog = get_gi_catalog()
    if food_name not in catalog:
        return GIReference(mapping_status='needs_source', notes='No exact detector-name GI mapping exists.')
    cid, record = catalog[food_name]
    if class_id is not None and cid != class_id:
        raise GIConfigurationError(f'Food name "{food_name}" and class ID {class_id} disagree with GI reference (expected {cid}).')
    return record.model_copy(deep=True)


def map_gi(result: NutritionMappingResponse) -> GIMappingResponse:
    """Attach GI reference data to mapped nutrition response."""
    get_gi_catalog()
    payload = result.model_dump()
    payload['foods'] = [
        {
            **food.model_dump(),
            'gi': gi_for_food(food.food_name, food.class_id),
        }
        for food in result.foods
    ]
    return GIMappingResponse(**payload)


def all_gi_foods() -> dict:
    """Return dictionary of all 46 foods and their GI reference records."""
    catalog = get_gi_catalog()
    return {name: record for name, (_, record) in catalog.items()}
