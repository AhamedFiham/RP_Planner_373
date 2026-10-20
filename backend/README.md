# DiaCare AI Backend

FastAPI starter structure for the four research components: diabetes, retinopathy,
wound healing, and diet planning. Component routers are registered under `/api`;
the diet food-detection endpoint uses the packaged YOLOv8n model. Other component
prediction modules remain separate.

## Run locally

From the project root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Health check: http://127.0.0.1:8000/health
API documentation: http://127.0.0.1:8000/docs

## Member work areas

Each member owns their component files in `app/api`, `app/services`, `app/models`,
`app/schemas`, and `app/database/repositories`. Store saved models in the matching
`trained_models` folder. Share reusable processing code in `app/utils`.

Store original datasets in `datasets/<component>/raw/` and cleaned datasets in
`datasets/<component>/processed/`, where `<component>` is `diabetes`,
`retinopathy`, `wound`, or `diet`. Dataset files are excluded from Git; `.gitkeep`
files preserve these folders. Saved trained models belong in `trained_models/`.

Keep local configuration in `.env` and document variable names in `.env.example`.
Uploaded files, generated outputs, and model artifacts are excluded from Git;
`.gitkeep` files preserve the folder structure.

## Account storage

Authentication loads `backend/.env`. Set `MONGODB_URI` and `MONGODB_DATABASE`
to use MongoDB; connection failures return HTTP 503 and never silently discard accounts.
Without `MONGODB_URI`, local development uses persistent SQLite in
`backend/outputs/auth.sqlite3` (excluded from Git). Accounts created by the old
in-memory fallback cannot be recovered after a restart and must be registered again.
Logout removes the browser session, not the saved account. Set a strong
`JWT_SECRET` before deploying.

## Component demo accounts

For development only, run `python -m scripts.seed_demo_accounts` from `backend`
to create diabetes@diabeticcare.com, retinopathy@diabeticcare.com,
wound@diabeticcare.com, and diet@diabeticcare.com, each with password `2026!`.
Existing accounts are not overwritten. Each signs in through `/login` and opens
its component dashboard. These are test identifiers, not verified email inboxes.
New public registrations still require the stronger password policy.

## Diet Dataset Preparation

Diet scripts are isolated under `scripts/diet_dataset/`. From `backend`:

```sh
python3 scripts/diet_dataset/prepare_diet_dataset.py --dry-run
python3 scripts/diet_dataset/prepare_diet_dataset.py --execute
```

The pipeline discovers raw YOLO, COCO, and classification datasets. Raw images
remain unchanged. Classification fruit/drink images remain separate from the
normalized detector. Shared class configuration is under `config/diet_*`.

The prepared subsets are `datasets/diet/training_v1/` and
`datasets/diet/training_v2/`. Their builders are
`scripts/diet_dataset/build_diet_training_v1.py` and
`scripts/diet_dataset/build_diet_training_v2.py`. No model is trained by them.

See [the Diet pipeline documentation](scripts/diet_dataset/README.md) for
conversion rules, class mapping, reports, tests, and rebuild instructions.
The old cleaning scripts and normalization wrapper have been retired.


## Diet food-detection API

From `backend`, install dependencies and start the existing application:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`POST http://127.0.0.1:8000/api/diet/detect-food` accepts `multipart/form-data`
with one **file** field named `image`. Supported extensions/MIME types are
JPG/JPEG (`image/jpeg`), PNG (`image/png`), and WebP (`image/webp`). Filename,
MIME, encoded format, nonempty bytes and decoded dimensions are validated.
Limits: 10 MiB encoded bytes and 20 million decoded pixels. Source uploads and
prediction images are not saved. Boxes are xyxy pixel coordinates in the decoded
image, with no automatic EXIF rotation; detections are sorted by confidence.

```sh
curl -X POST http://127.0.0.1:8000/api/diet/detect-food \
  -F 'image=@/absolute/path/to/meal.jpg;type=image/jpeg'
```

Postman: select **POST**, use the URL above, choose **Body → form-data**, add key
`image`, change its type from Text to **File**, and select a supported image.
Let Postman set the multipart Content-Type and boundary automatically.

Example response (values from the local smoke test, shortened for readability):

```json
{
  "success": true,
  "detection_count": 1,
  "detections": [{
    "class_id": 9,
    "food_name": "Chicken_Curry",
    "confidence": 0.73396,
    "bounding_box": {"x1": 221.376, "y1": 71.553, "x2": 920.769, "y2": 584.176}
  }],
  "image_width": 940,
  "image_height": 640,
  "model_name": "YOLOv8n",
  "confidence_threshold": 0.25
}
```

No detections returns HTTP 200, `success: true`, `detection_count: 0`, and
`detections: []`. Invalid uploads return HTTP 400; model/configuration/inference
failures return HTTP 500 with a generic public message and details in server logs.

`GET /api/diet/model-info` returns selected model, dataset version, class count,
input image size and confidence threshold without local filesystem paths.

The cached lazy loader reads `trained_models/diet/best.pt`, checks its SHA256
against metadata, and verifies the 46 IDs (0–45) and canonical names against
`class_names.json`. One model is loaded per server worker process; concurrent
first requests cannot duplicate loading. The first diet request incurs load
latency. Prediction uses CPU and a per-process lock around the shared predictor.
Multiple workers each allocate a separate model. Model-info also validates/loads
the package. `/health` remains lightweight and does not promise diet model readiness.

Set `DIET_DETECTION_CONFIDENCE=0.25` in `backend/.env` (default 0.25, finite range
0–1). Restart the server after configuration changes. The threshold is a baseline,
not a calibrated production choice. No new nutrition, portion, carbohydrate,
GI/GL, glucose-personalization or recommendation processing is included.

Run focused tests (mocked inference plus one actual package-load test):

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p test_diet_detection.py -v
```

A one-image real inference request was also checked locally through FastAPI's
ASGI TestClient. The recorded response and protected-file verification are in
`outputs/diet/api_integration_verification.json`; this is an integration smoke
test, not a new model evaluation or benchmark.


## Portion Estimation V1 — visual research categories

`POST /api/diet/estimate-portions` reuses food detection and returns per-detection
`foods` plus a food-level `portion_summary`. The original `/detect-food` endpoint
remains unchanged. Upload one image under multipart field `image`:

```sh
curl http://127.0.0.1:8000/api/diet/estimate-portions \
  -F 'image=@/absolute/path/to/meal.jpg;type=image/jpeg'
```

### Train-only calibration

```sh
.venv/bin/python scripts/diet_dataset/calibrate_portion_categories.py
```

The script reads `training_v3/data.yaml` for the 46-class mapping and reads only
`training_v3/train/labels/*.txt` for observations. It never reads validation/test
labels or images, changes dataset files, imports a model runtime or trains a
model. Each normalized detection contributes `width * height` to its own class.
Q33 and Q67 use linear interpolation at `(n-1)*p`, with p=0.33 and p=0.67.
Normalized-edge serialization tolerance is 1e-6, matching existing validation;
width and height are used unchanged. Malformed labels stop calibration rather
than silently biasing the distributions.

- Small: area <= the food's Q33.
- Medium: Q33 < area <= the food's Q67.
- Large: area > the food's Q67.
- Fewer than 10 usable training annotations: Unknown, with calibration status
  `insufficient_training_support` and no fabricated thresholds.
- Equal/nonseparable quantiles: Unknown with `degenerate_training_distribution`.

The actual run used 1,868 train label files and 4,604 annotations. All 37
area-based classes had sufficient support and separable quantiles. Thresholds,
training sample counts and provenance are stored in `config/portion_reference.json`.
Reports are in `outputs/diet/portion_calibration/`: `portion_thresholds.csv`,
`portion_calibration_summary.json`, and `portion_calibration_report.md`.
The JSON summary preserves hashes for the mapping and train label inputs.

### Area, count and reference methods

Area methods apply to the existing 37 rice/curry/vegetable/condiment classes
listed in the reference config. Per-detection area is rectangle area divided by
image area. Same-food summaries use exact rectangle-union area, capped at 1,
so overlaps are not counted twice. No grams are calculated. Per-detection area
is retained internally; the UI uses only grouped categorical summaries.

Boiled_Eggs, Hoppers, Cutlet, Pappadam, Kavum and Kokis use the explicit provisional
count policy in the config: 1 detected region → Small; 2 → Medium; 3+ → Large.
Any positive-area same-food overlap suppresses the count and yields Unknown.
Regions are not verified individual units, and hidden pieces are never inferred.
Counts are returned once in `portion_summary`; per-detection categories refer to
the same grouped category, not separate physical portions.

String_Hoppers, Pittu and Kottu remain reference-based/Unknown. Missing food
entries also fall back to reference mode. A missing or invalid configuration file
fails clearly with sanitized API error handling. `estimated_grams` remains null,
`validated` and `validated_physical_portion` remain false, and the schema records
`calibration_type: visual_research_baseline`. Serving-weight mappings are not
accepted by V1. The `research_baseline_thresholds` section explicitly marks the
rules as unvalidated research policies.

### Interpretation and limitations

**Small / Medium / Large are research-baseline visual portion categories, not
validated physical serving weights.** They describe where an observed image
coverage falls relative to that food's training-box distribution. Quantile bins
are not clinical or nutritional portion standards. Framing, camera angle/distance,
background, scale, food height/depth, preparation and density all matter. Visible
area is not volume; volume is not mass. Segmentation could improve area estimates
without establishing physical mass by itself.

Training samples are individual annotated boxes, whereas grouped runtime coverage
can be a union of several boxes; that is a sampling-unit mismatch/extrapolation.
Predicted boxes may also differ from ground-truth annotation distributions.
These effects, annotation/source dependence and category stability need independent
validation. Calibrating only on train does not establish scientific serving-size
validity or correct previous model-selection limitations.

Real gram estimates would require food-specific paired photographs and measured
serving masses, verified unit annotations, scale/reference geometry, relevant
imaging conditions and independent validation with uncertainty estimates. A
volume-based approach would additionally need height/depth and density data.
No nutrition, calories, carbohydrate, GI/GL, glucose input or recommendations are
implemented by this module.

The frontend shows one portion summary per food, with detection confidence and
counts where applicable. Internal relative-area fractions remain in the API for
research, but portion-area percentages and unavailable-weight rows are hidden.
Individual bounding boxes remain on the image. Unknown cases are not forced into
a size category.

Run regression tests:

```sh
python -m unittest discover -s tests -v
```


## Nutrition Reference Mapping

`POST /api/diet/map-nutrition` accepts the same multipart image field and calls
the existing detection and portion flow once, then looks up each canonical
`food_name` exactly. `/detect-food` and `/estimate-portions` keep their existing
contracts. The response retains per-detection boxes/portions and `portion_summary`
and adds `nutrition` to each food. Duplicate foods receive identical references;
no nutrients are summed, scaled by visual category, or labelled consumed amounts.

```sh
curl http://127.0.0.1:8000/api/diet/map-nutrition \
  -F 'image=@/absolute/path/to/meal.jpg;type=image/jpeg'
```

### Reference data and validation

The exact source is
`datasets/diet/raw/diet_nutrition_46_classes_v3.csv` (not earlier CSV versions).
It contains all 46 packaged detector names/IDs. The lazy, locked reference cache
loads once per worker process. It validates required columns, row shape, unique
IDs/names, exact taxonomy alignment, allowed basis/status and finite non-negative
numeric values. A missing, malformed or inconsistent file fails with a clear
internal configuration exception and sanitized HTTP 500. Restart the worker after
CSV changes; references are not hot-reloaded. No new dependencies are needed.

Source labels in this user-provided CSV cite the Sri Lankan Food Composition
Database / Opatha et al. 2025 and a supplemental user-provided Sri Lankan
serving-based table. Integration preserves those labels, notes, numeric units and
values; it does not independently verify the publication, recipes or measurements.
The cited source name is provenance supplied by the CSV, not a new validation claim.

### Basis, blanks and uncertainty

- `per_100g` stays per 100 g. `per_serving` stays per serving, preserving original
  serving quantity/unit and original macros. No automatic basis conversion occurs.
- Blanks become JSON null. Numeric zero remains zero. Missing nutrients are never
  fabricated. All listed macros, fats, vitamins and minerals preserve CSV units.
- `matched_full`, `matched_macro`, and `matched_serving` preserve direct CSV match
  status. The UI's Verified Reference badge describes that match status only;
  it does not mean independent source/laboratory or clinical validation.
- `candidate_*` includes an explicit manual-confirmation warning; preparation or
  food-identity differences must be reviewed.
- `representative_full` includes a recipe-variation warning, not an exact match claim.
- `needs_source` returns a normal reference object with null nutrients/basis and
  completeness `none`, not 404. Empty detections return success with empty foods.
- Five supplemental per-serving rows are labelled `data_completeness=none` in the
  CSV while containing known macros. The label is preserved, and supplied values
  are retained rather than erased; only missing fields are null. This source
  metadata inconsistency should be reviewed.

The CSV has 13 needs_source, 10 candidate, 2 representative and 21 matched rows.
Unavailable foods: Capsicum_Curry, Cauliflower_Curry, Chili_Paste, Cutlet, Fish_Curry, Fried_Potato, Kokis, Lunu_Sambol, Mallum, Omelette, Pea_Curry, Pork_Curry, Watalappam.
Some mapped records have macros only; serving-based records lack most
micronutrients. Candidate mappings and original nutrient units require source
review. In particular, Shrimp_Curry reports water_g=109.37 on a per-100-g basis.
The value is preserved and returned with a data-quality warning rather than
silently corrected. This reference is not ready to justify clinical conclusions.

### Frontend and interpretation

The standalone reference flow calls `/map-nutrition`; the current Diet page uses
the combined serving endpoint described below and shows food identity,
confidence, visual portion category and Reference Nutrition. The main card shows
energy/carbohydrates/protein/fat/fiber. An expandable section shows non-null
micronutrients, including explicit zeros when present. Per-serving references show
the original serving quantity/unit. Candidate/representative warnings, sources
and source notes remain visible or expandable; unavailable references are neutral
empty states. Local CSV/checkpoint paths and CSV row numbers are not exposed.

**Nutrition values are reference values from the mapped food source and do not
represent the exact amount consumed.** Visual Small/Medium/Large categories have
no validated gram mapping. Therefore reference mapping alone calculates no consumed nutrients. The separate
serving stage below can calculate per-food estimates only with sourced mass
evidence; meal totals, GI/GL, glucose logic and recommendations remain excluded. Actual consumed-nutrient estimates would first require validated
portion mass and confirmed food/preparation/reference mappings.

Run tests with `python -m unittest discover -s tests -v`. Nutrition API tests mock
detection. They verify source validation, basis preservation, blanks/zeros,
cache behavior, warnings, unchanged older routes, failures and empty results.


## Serving-weight Mapping and Estimated Consumed Nutrition

The new endpoint is `POST /api/diet/estimate-consumed-nutrition`, with the same
multipart `image` field. It invokes the existing detection/portion/reference flow
once, then attaches serving-weight evidence and optional consumed estimates.
Older `/detect-food`, `/estimate-portions`, and `/map-nutrition` contracts remain
unchanged.

```sh
curl http://127.0.0.1:8000/api/diet/estimate-consumed-nutrition \
  -F 'image=@/absolute/path/to/meal.jpg;type=image/jpeg'
```

### Evidence file and current availability

`config/diet_serving_weights.json` covers all 46 exact detector food names and is
loaded once per worker. **0 foods currently have valid serving-weight mappings;
all 46 need reference evidence.** Every production mass is null. A nutrition CSV
serving quantity (e.g. a reference quantity for Pappadam or Lunu_Miris) is not
proof of mass per detected object or per visual category, so it is never promoted
automatically into this separate mapping.

Supported methods:

- `portion_category`: explicitly sourced `small_g`, `medium_g`, `large_g`.
- `count_based`: grouped count × explicitly sourced `grams_per_unit`. Current
  count foods are Boiled_Eggs, Hoppers, Cutlet, Pappadam, Kavum and Kokis. Counts
  must be trustworthy; overlap ambiguity or absent counts prevents mass estimates.
- `reference_serving`: one sourced gram-denominated reference serving, usable only
  with explicit evidence that the observed visual category matches that serving
  (`reference_match_confirmed` and `matching_portion_category`). No implicit match
  is made merely because nutrition_basis is per_serving.
- `unsupported`: safe fallback without a mass estimate. Unknown exact names also
  return a needs_reference fallback.

Numeric mappings require positive finite masses, appropriate method-specific
fields, `status: available`, `validated: true`, `source_name`, `source_reference`
and `validation_notes`. Here validated is a curator's evidence declaration for
the serving-mapping relationship, not a claim about the whole detector or clinical
suitability. Do not enable it merely because a food has a published serving size:
the mapping from visual category or observed unit must also be justified. Record
preparation, portion definition, source citation and applicability in the notes.
After a reviewed configuration change, restart server workers to reload the cache.

### Conditional formulas and null handling

Only a sourced, available and validated mass permits calculation. For the six
supported output nutrients (kcal, kJ, carbohydrates, protein, fat, fiber):

```text
per_100g: consumed_value = reference_value * serving_weight_g / 100
per_serving with known original quantity in g:
          consumed_value = reference_value * serving_weight_g / original_serving_quantity
```

Per-serving proportional scaling is explicitly labelled an approximation that
assumes comparable composition. With exactly one equal-mass reference serving the
factor is one. A non-gram/unknown/zero original quantity cannot be scaled. Missing
reference nutrients stay null; explicit numeric zero stays zero. Missing mass
returns `consumed_nutrition: null`, not fabricated zeros. References themselves
remain untouched and keep their original basis.

Candidate and representative nutrition mappings require a separate explicit
`nutrition_mapping_confirmed` declaration after review before consumed estimates
are allowed. needs_source nutrition never produces a consumed object. A valid
mass can therefore exist while consumed nutrition is still unavailable. Failure
statuses distinguish absent serving evidence, missing nutrition, unconfirmed
mapping, and a non-scalable basis. No unit conversion from pieces/cups to grams
is inferred.

### Grouping and API shape

`foods` in this **new endpoint** is a unique food-level list. Each record contains
class/name, highest individual confidence, grouped portion summary, reference
nutrition, serving_weight, nullable consumed_nutrition, status, detection_count and
detection_indices. `detections` retains all original detection-level boxes and
references; root detection_count remains the number of boxes. `portion_summary`
is preserved. Food-level masses and nutrients occur only once, preventing the
same grouped count/area from being assigned as several consumed portions.
No meal-level calories/carbohydrates or partial totals are returned.

Current response excerpt (extra fields omitted):

```json
{
  "food_name": "White_Rice",
  "serving_weight": {
    "serving_method": "portion_category",
    "estimated_serving_weight_g": null,
    "serving_weight_status": "needs_reference",
    "validated": false
  },
  "consumed_nutrition": null,
  "consumed_nutrition_status": "serving_weight_unavailable"
}
```

### Frontend and limitations

The Diet page makes one request to the new endpoint. It preserves Reference
Nutrition and separately labels Estimated Serving Weight and Estimated Consumed
Nutrition. Missing mass shows Not available yet and explains why consumed values
cannot be calculated. Available values show source evidence, nullable nutrients
and any proportional-scaling caveat. Raw image boxes remain unchanged.

Visual Small/Medium/Large is not grams. Single-image framing, scale, density,
depth, preparation, count-unit ambiguity and detector errors remain limitations.
References need food-specific evidence and independent mass-mapping validation.
**Consumed nutrition is estimated from a referenced serving weight and food
composition data. It is not a laboratory measurement.** No GI/GL, glucose logic,
recommendations, meal totals or clinical advice are implemented.

Run `python -m unittest discover -s tests -v`. Formula/available-state tests use
explicitly synthetic TEST-ONLY mass records, never values written into production
serving references. Tests do not establish real serving weights or retrain YOLO.

## Glycemic Index reference mapping

The Diet component reads `datasets/diet/raw/diet_gi_46_classes.csv`, which contains
one exact row for each of the 46 detector classes. GI is food and preparation
specific; blank GI values remain unavailable and are never treated as zero. The
`POST /api/diet/map-gi` endpoint reuses detection and nutrition mapping and adds
food-level GI references. The guidance endpoint may include the same optional GI
object. No meal GI or Glycemic Load is calculated; Glycemic Load is planned for a
later stage using validated carbohydrate amounts.
