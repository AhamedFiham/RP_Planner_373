# DiaCare AI Backend

FastAPI backend for the four research components: diabetes, retinopathy,
wound healing, and diet planning. Component routers are registered under `/api`.
The wound component supports a persistent clinic workflow and private segmentation
analysis through explicitly configured model adapters.

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

On Windows PowerShell, activate a working Python environment and run:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## Wound clinic workflow

Each signed-in account is a clinic workspace. It can register multiple distinct
patients, assign multiple wounds to each patient, then add dated image visits to
each wound. Patients do not need separate login accounts. Every clinic endpoint,
including image retrieval, requires `Authorization: Bearer <access_token>` from the
existing login API. A clinic cannot list or retrieve another account's records.

| Method | Endpoint under `/api/wound` | Purpose |
|---|---|---|
| GET / POST | `/patients` | List/register patients (`patient_code`, `display_name`, optional `notes`) |
| GET / POST | `/patients/{id}/wounds` | List/assign wounds (`label`, `location`, optional `onset_date`, `status`, `notes`) |
| PATCH | `/wounds/{id}` | Set `status` to `active` or `healed` |
| GET / POST | `/wounds/{id}/visits` | Chronological history / upload dated images |
| GET | `/wounds/{id}/progress` | Chronological tissue proportions for a selected `model_id` |
| PATCH | `/visits/{id}/progress-image` | Select one uploaded `image_id` for that visit's trend point |
| GET | `/images/{id}` | Retrieve an owned image privately |
| GET | `/models` | Model choices and selected model availability (optional `model_id` query) |
| GET / POST | `/images/{id}/analysis` | Saved results / analyze `stage` with optional `model_id` |
| GET | `/analysis-artifacts/{id}` | Retrieve an owned saved mask privately |

Patient codes are unique per workspace (case insensitive). Each wound has one
visit per date. Uploads use `multipart/form-data`: `visit_date` (`YYYY-MM-DD`),
optional `notes` (up to 2000 characters), and 1–5 repeated `images` fields. Upload
valid, non-animated JPEG, PNG or WebP files, at most 10 MiB each, 8192 pixels per
side and 20 megapixels. Declared content type must match the decoded image format.
Wounds marked healed must be reopened before adding another visit. Image names
are generated internally; original filenames are display metadata only. Files are
served by the authenticated endpoint, never by a public static directory.

**Images only:** the clinic does not collect wound size, depth, or other physical
measurements. Visit responses contain no measurement fields. Wound and tissue
segmentation are separate analysis stages; alternative trained architectures can
be exposed as selectable model profiles. Without configured models they remain
`not_connected`. Completed wound and tissue masks populate the tissue trend graph
described below. Healing analysis remains `awaiting_method`: no healing percentage,
healing diagnosis, wound-size change, or physical measurement is calculated.

Clinic records persist in `backend/outputs/wound_clinic.sqlite3`; uploaded originals
persist in `backend/outputs/wound_images`. Set `WOUND_DATA_DIR` to relocate both, or
`WOUND_DB_PATH` to select a database file (images default to its parent directory).
An explicit `WOUND_DATA_DIR` also controls images when both variables are set.
Generated masks persist in `backend/outputs/wound_analysis` and are also served
only through the authenticated API. Back up the database, original images and
generated masks together. These paths contain clinic data
and are excluded from Git. They are local development storage, not a deployment,
retention, backup, or clinic access-management solution.

The progress endpoint accepts optional `?model_id=...` and returns `status`
(`ready`, `partial`, or `pending`), the selected model ID, tissue labels/colours,
one chronological point per visit, counts of all and analyzed visits, and
`healing_percentage: null`. Each point identifies its visit, date, selected image,
available visit images, and availability reason. Its `analysis` metadata
identifies the usable wound/tissue run IDs, artifact IDs, and model versions for
the selected image; no filesystem paths are exposed. Retrieve those masks through
the authenticated `/analysis-artifacts/{id}` endpoint. Missing, failed, incompatible,
or empty-wound masks remain visible as gaps rather than zero values.

Each visit uses its first uploaded image by default. Change that selection with
`PATCH /visits/{id}/progress-image` and `{"image_id":"..."}`; the chosen image must
belong to the same visit and workspace. The choice persists across reloads and is
shared by the model choices. Other photos stay available for independent analysis.

For the supplied prototype, each tissue proportion equals its labelled pixel count
**inside the binary wound foreground**, divided by the total wound foreground
pixels, multiplied by 100. Displayed series are epithelialization, granulation,
slough, necrosis, bone/tendon/muscle, other, and unclassified. Tissue background
inside the wound is unclassified; pixels outside the wound do not contribute.
Fibrin is unavailable in the supplied model and is not plotted. Values describe
composition and sum to 100% for a usable point; they do not measure wound area or
healing. A tissue point uses a completed wound/tissue pair from the same image,
selected model, and current checkpoint/preprocessing fingerprints. Results from
different models or superseded configurations are not combined across visits.
Custom adapters need a known compatible class mapping before their masks can
populate this graph. No healing percentage or clinical healing interpretation has
been defined yet.

The frontend Overview card summarizes analyzed visits, latest tissue composition,
and earliest-to-latest changes. Its Compare visits action opens the Tissue
comparison tab with the earliest and latest usable analyzed visits selected.
Users can choose another ordered pair and compare original photos, private tissue
masks, exact tissue proportions, and later-minus-earlier changes in percentage
points. The full visit trend chart remains available below the comparison.

For selected visits without usable results, Analyze selected visits calls the
existing image-analysis endpoint in wound-then-tissue order for each selected
photo and model. Usable saved results are reused; failed stages remain visible
and can be retried. The comparison does not calculate a healing percentage.

Run isolated backend checks (clinic files and authentication integration accounts
use temporary directories; focused tests mock account lookups; real accounts are
untouched):

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Segmentation model configuration

Set `WOUND_MODEL_CONFIG` to a server-owned JSON file. No weights path, factory
module, or preprocessing parameters are accepted from HTTP clients. An omitted
configuration means `not_configured`; no default or synthetic prediction runs.
The registry supports a flat object with `wound_segmentation` and
`tissue_segmentation` entries (implicit profile ID `default`), or named profiles:

```json
{
  "default_model_id": "your_model_id",
  "profiles": {
    "your_model_id": {
      "label": "Your trained segmentation model",
      "wound_segmentation": {
        "adapter": "your_backend_module:build_wound_adapter",
        "weights_path": "trained_models/wound/your-model.pt",
        "model_version": "your-model-v1",
        "parameters": {}
      },
      "tissue_segmentation": {
        "adapter": "your_backend_module:build_tissue_adapter",
        "weights_path": "trained_models/wound/your-model.pt",
        "model_version": "your-model-v1",
        "parameters": {}
      }
    }
  }
}
```

This is a contract example: replace the module names and weights with the actual
trained model implementation. Relative weights paths resolve from the JSON file's
directory. On PowerShell, before starting the backend:

```powershell
$env:WOUND_MODEL_CONFIG = (Resolve-Path .\wound-models.local.json).Path
python -m uvicorn app.main:app --reload
```

Each trusted factory receives keyword arguments `weights_path: Path`,
`model_version: str`, and `parameters: dict`, and returns an adapter implementing
`app/models/wound_model.py`. The wound adapter implements `predict(image_path)`;
the tissue adapter implements `predict(image_path, wound_mask)`. Tissue analysis
requires a saved completed wound result for the same image **and model profile**;
that result must match the current wound model/checkpoint/preprocessing fingerprint.
Its `input_analysis_id` permanently records that dependency. The adapter decides
how that mask is used according to the actual training and inference code.

The adapter must implement the exact trained architecture, input preprocessing,
inference and output decoding. A `.pt` extension alone does not define these.
It returns `SegmentationResult` or `TissueResult` with its configured version and
an existing mask image path. Masks must have the original uploaded image's pixel
dimensions, be non-animated and fit the upload pixel limits; outputs are copied
losslessly to PNG without guessing class labels, thresholds or overlay colours.
An adapter may implement `release(result)` to remove its temporary output once
the service has copied it; otherwise the adapter owns temporary-file cleanup.

`GET /models` returns `models: [{id, label}]`, `default_model_id`,
`selected_model_id`, and status/version for each analysis stage. Select another
profile with `?model_id=...`. Availability is `not_configured`, `weights_missing`,
`configured`, `ready`, or `error`; filesystem paths and internal errors stay
private. `configured` means the adapter has not been initialized yet, and `ready`
means it was initialized successfully. Factories load lazily and inference is
serialized per stage; only the current adapter per stage is retained. Model
loading/runtime dependencies belong to the actual adapter, rather than a guessed
global PyTorch installation.

`POST /images/{id}/analysis` accepts
`{"stage":"wound_segmentation","model_id":"your_model_id"}` or
`tissue_segmentation`. Omitting `model_id` selects the configured default.
The request runs synchronously in FastAPI's worker thread; no background queue is
claimed. It returns a persisted result with `status` `completed` or `failed`,
timestamps, model ID/version, dependency ID and private artifact IDs. Failures
have a safe fixed message and no artifacts. Unavailable models return HTTP 503
without creating a run; missing tissue prerequisites return 409. Invalid model
choices return 400, and unsupported stages (including healing) return 422.
Visit summaries describe the default profile, or the profile selected by an
optional `model_id` query on `GET /wounds/{id}/visits`. Per-image history includes
all profiles, with an explicit model ID on each run.

Successful results are reused only for the same image, stage, profile, dependency
and fingerprint of adapter/parameters/weights content. Changing checkpoint bytes
or preprocessing parameters invalidates that cache even if the version label was
not updated. Use distinct version labels for reproducible releases. Adapters
which delegate to another inference service must also ensure that service has
loaded those checkpoint bytes. The supplied dedicated `wound_runtime` verifies
the requested SHA-256 against each checkpoint and reloads its cached model when
the checkpoint changes. Runtime access requires the private token shared through
ignored local configuration. It uses port 8010 by default; the earlier standalone
prototype on port 8001 is independent of this integration.
Missing stored masks trigger a fresh run. Older completed and failed runs remain
in history, returned newest first by `GET /images/{id}/analysis`.

A partial unique database index prevents duplicate running records for one image,
profile and stage. Each running inference holds an OS file lock in
`wound_analysis_locks` next to the clinic database. Reading analysis history or
requesting another analysis recovers abandoned running records only when their
OS lock can be acquired; live workers remain protected. Interrupted records
become failed and can be retried. This recovery uses local filesystem locks and
does not introduce a task queue. Existing clinic tables are preserved; analysis
tables and compatible optional columns are added when the repository opens.

## Supplied three-model prototype

The concrete adapter `app.models.prototype_adapter` connects U-Net/ResNet18,
DeepLabV3+/MobileNetV2, and SegFormer/MiT-B0. Each checkpoint has independent wound
and tissue heads. These are three selectable segmentation architectures. Their
saved masks support tissue proportions across visits; no healing model is supplied.

Run the one-time local setup from `backend` with the clinic Python environment:

```powershell
python -m scripts.configure_wound_models
```

By default, checkpoints are read from these project-local paths:

```text
trained_models/wound/unet_resnet18/final.pt
trained_models/wound/deeplabv3plus_mobilenet_v2/final.pt
trained_models/wound/segformer_mit_b0/final.pt
```

The checkpoint binaries are excluded from Git. To use a different folder, pass
`--checkpoint-root "C:\path\to\models"`; an output folder containing `runs` is
also accepted. The command verifies
the three `final.pt` paths, creates checkpoint-derived versions and writes ignored
`wound-models.local.json`, `wound-runtime.local.json`, and the model-config setting
in `.env`. Other existing `.env` settings remain in place. The generated runtime
token is private and never returned to the browser.

Start `python -m scripts.run_wound_runtime` from `backend` using the separate
compatible Python 3.12/PyTorch environment, then run/restart the normal clinic API.
See [the runtime README](wound_runtime/README.md). The runtime binds to loopback
port 8010; the frontend continues to use the clinic API on port 8000. The bridge
checks model ID, checkpoint hash, output geometry, mask labels, and source type.
Only numeric masks are retained, with the original training palette for display.
The graph calculates wound-restricted tissue proportions from those masks. The
source pipeline's percentages and other unrelated outputs are not reused.

Run `python -m scripts.smoke_wound_models` in a backend development-test environment
to exercise all three actual models across two synthetic visits, check tissue
proportions against their saved masks, and verify private access and history. The optional
`--reference-url http://127.0.0.1:8001` compares with the original standalone service.
No real patient files or account records are used or changed by this check.

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
