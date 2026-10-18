# DiaCare AI Backend

FastAPI starter structure for the four research components: diabetes, retinopathy,
wound healing, and diet planning. Component routers are registered under `/api`;
prediction endpoints, trained models, and database integration are not implemented yet.

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

## Diet dataset cleaning

From `backend`, run `python3 scripts/clean_diet_datasets.py` with Pillow and
PyYAML installed. The script handles the seven meal datasets in `datasets/diet/raw/`.
Existing cleaned folders are skipped. Fruits-360 processing is disabled in this
command; the optional standalone Fruits-360 script is retained.
Original images and licenses are preserved; exact pixel duplicates are excluded
and recorded in the cleaning report. Near duplicates need manual review.

`python3 scripts/export_food_names.py` rebuilds `processed/food_names.csv`.
Class IDs are specific to each dataset. `annotation_count` counts annotated
objects for detection/segmentation and labeled images for classification.
Food class names retain the original spelling. The CSV is tracked in Git;
image datasets remain excluded.

## Normalized diet training labels

Use `datasets/diet/normalized/<dataset>/` for the shared food taxonomy. The
original `raw/` and `processed/` annotations retain their source class IDs.
`config/diet_classes.json` defines the shared zero-based IDs;
`config/diet_class_mapping.csv` records every source ID, canonical name, removal,
and decision requiring review. Do not pair the normalized CSV IDs with the
original processed annotation files.

Run `python3 scripts/normalize_diet_classes.py` once after cleaning, then
`python3 scripts/export_food_names.py`. The normalizer refuses to overwrite an
existing normalized folder. Move that folder aside before rebuilding after
source or mapping changes. Existing canonical IDs are preserved in config/diet_classes.json; new
classes are appended. Version this registry with trained models. The CSV exporter uses normalized annotations when a completed
normalization report exists; it otherwise uses the original processed datasets.

Requested merges include Dhal_Curry, White_Rice, Kiribath, and Gotukola_Sambol
(including Gotukola Mallum, as requested). Other clear spelling/alias merges
include Pappadam, Watalappam, Shrimp_Curry, Tempered_Sprats, and Coconut_Sambol.
Generic foods and specific preparations are kept separate: Fish/Fish_Curry,
Chicken/Chicken_Curry, raw vegetables/curries, and red/white/generic pittu and
string hoppers. Ambiguous labels such as Beat, Curb, and Flavourd mild cartoons
are preserved with review_required=True rather than guessed. Ambiguous canonical
labels still require that review before final training.

Annotations for `json` and `spoon` are dropped without changing image pixels,
bounding boxes, or segmentation geometry. Empty labels are retained as background
images. Keep all datasets' splits separate; the previously reported duplicate
across datasets must be resolved before combined training/evaluation.

## Manually collected fruit images

`raw/Fruits/<class>/` is cleaned with `python3 scripts/clean_manual_fruits.py`
(or the main cleaning command). WebP images are supported and original bytes
are preserved. The output is `processed/manual_fruits_classification/images/`.
There are 55 images in 11 classes, without a supplied train/test split. This is
a classification dataset; it has no bounding boxes or segmentation polygons.

Normalization includes these classes under `normalized/manual_fruits_classification/`.
The shared registry currently contains 150 canonical names. The food CSV has
213 dataset-specific rows; annotation_count counts images for classification.
Previous normalized copies are preserved locally in
`datasets/diet/normalized_before_manual_fruits/`. Image folders are excluded
from Git; source code, class mappings, and the food-name CSV are tracked.
