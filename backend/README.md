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
