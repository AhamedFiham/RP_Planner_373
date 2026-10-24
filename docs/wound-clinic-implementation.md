# Wound clinic implementation

## Goal and scope

Build a persistent clinic workflow with trained segmentation models and tissue
trends across dated visits:

`Signed-in clinic workspace → Patient → Wound → Dated visit → Wound images → Model results`

The clinic creates separate patient records. Each patient can have several wounds,
and every wound has its own ID and ordered visit history. Patients are clinic
records, not new login accounts. The current account identifies the clinic
workspace; sharing records between multiple staff accounts needs an explicit
clinic membership and permission model in a later step.

The application accepts images only. The clinic does not collect wound size,
depth, or other physical measurements. The progress chart compares tissue
proportions inside the segmented wound across visits. The user chose to show
tissue trends first and define a healing percentage later; no healing percentage
or clinical healing assessment is currently calculated.

## Step 1 — Records and storage (implemented)

- Create patients with a unique clinic patient ID, display name, and optional notes.
- Assign wounds with an automatic wound ID, label, anatomical location, optional
  onset date, and notes.
- Save one visit per wound per date, with notes and up to five wound images.
- Keep patients and wounds separate through database foreign keys and authenticated
  ownership checks. A guessed record or image ID cannot access another workspace.
- Persist records in SQLite and image originals on the backend. Refreshing the
  page or restarting the API does not discard records.
- Mark wounds healed and reopen them while preserving their history.

See `backend/README.md` for endpoints, storage settings, and upload limits.

## Step 2 — Clinic screens and progress interface (implemented)

Open `/dashboard/wound` from the existing wound login/dashboard navigation.
`/dfu` opens the same workspace, and `/wound` redirects there.

1. Create or search for a patient in the patient list.
2. Assign a wound, then select it from the wound selector.
3. Record the visit date and upload wound photographs.
4. Review images and notes in chronological visit history.
5. Open Overview, select a visit and image, and review model availability and
   persisted segmentation results. Analysis stays disabled until a real model
   and its inference adapter are configured.
6. Review the tissue trend chart in Overview, or open Tissue comparison to
   compare two visits. Choose the photograph that represents each visit; the
   choice persists, with the first uploaded photograph selected by default.

The Overview comparison card now shows the analyzed-visit count, earliest and
latest analyzed dates, latest tissue composition, and largest changes in
percentage points. Its Compare visits button opens the dedicated Tissue
comparison tab. The tab initially selects the earliest and latest usable
analyzed visits; both date selectors can choose another ordered pair. Original
photos and saved tissue masks appear side by side with the exact tissue
percentages and later-minus-earlier changes for every class.

Visits without usable results remain selectable. Analyze selected visits runs
wound segmentation before tissue segmentation for each selected photo and model,
reuses already usable saved results, and refreshes the comparison. Photo choices
and result displays stay scoped to the selected wound and model. No healing
percentage or healing classification is inferred from these differences.

Visits are ordered by their visit date, including dates entered out of order.
`GET /api/wound/wounds/{id}/progress?model_id=...` returns every visit, including
visits whose selected image has no usable analysis. Each point has a date, image,
status, availability reason, private analysis metadata for its usable wound and
tissue masks, and either tissue percentages or `null`. Metadata identifies the
saved run, artifact, and model version; masks still require the authenticated
artifact endpoint. Missing and
failed results leave gaps rather than plotting zero. The response also includes
the model ID, tissue legend, total and analyzed visit counts, and
`healing_percentage: null`. `PATCH /api/wound/visits/{id}/progress-image` with an
`image_id` saves the representative photograph without combining multiple photos
or counting a visit more than once.

For each supported tissue class, the chart uses its predicted pixels inside the
binary wound foreground divided by all wound-foreground pixels, times 100.
Background tissue pixels inside the wound are unclassified; tissue predictions
outside the wound are excluded. The series use the trained tissue colours:
epithelialization, granulation, slough, necrosis, bone/tendon/muscle, other, and
unclassified. Fibrin is unsupported and omitted. The plotted values sum to 100%
when masks are usable. An empty wound mask yields a gap, not a claim that the
wound is healed. These are tissue-composition trends, with no wound-size estimate,
healing score, clinical outcome, or assumed baseline percentage.

The backend accepts only a same-image wound/tissue pair for the selected model
and its current checkpoint/preprocessing fingerprints. Old or incompatible runs
stay in history but are not combined into the trend chart. Custom adapters need
a known compatible tissue-class mapping to populate it.

## Step 3 — Segmentation model integration (implemented)

The supplied checkpoint folder contains three alternative dual-head segmentation
architectures: U-Net/ResNet18, DeepLabV3+/MobileNetV2, and SegFormer/MiT-B0. Each
predicts both wound and tissue masks. There is no healing-outcome model in those
checkpoints. Saved segmentation masks now populate tissue trends; healing
assessment remains pending the user's definition.

The model selector chooses the architecture for both segmentation stages. The
clinic API on port 8000 uses an authenticated loopback model runtime on port 8010.
The runtime uses a separate compatible Python 3.12/PyTorch 2.6 environment and the
actual `.pt` files; no model weights are copied into Git. This avoids changing
the clinic API's Python environment.

The runtime implements the supplied architecture, black RGB letterbox,
ImageNet normalization, original-size logits restoration, and class decoding.
It verifies the requested checkpoint hash against the bytes it loads and reloads
changed checkpoints. Palette PNGs preserve the numeric mask labels and the known
training colours. Fibrin has no training examples and remains suppressed, matching
the supplied inference implementation. No physical measures or healing scores are
calculated.

Adapters are in `backend/app/models/prototype_adapter.py`. The analysis request,
private mask storage, result retrieval, model status, and frontend display are
connected. Every result is linked to its model, checkpoint identity, exact image,
and visit; tissue analysis records the current wound-mask dependency for that same
model and image. The two trained output heads remain independent: tissue predictions
are not clipped to the open-wound mask.

1. **Wound segmentation:** run inference for a selected visit image, preserve the
   original, and store a versioned segmentation mask linked to the image and visit.
2. **Tissue segmentation:** use the image and wound mask to produce labeled tissue
   masks. Store the class mapping and model version with each result.
3. **Tissue trends:** derive wound-restricted tissue proportions from saved masks
   for every visit, using one representative photo and one selected model.
   **Healing process analysis** remains pending: define its percentage and
   interpretation with the user before implementing a healing outcome.
4. The analysis endpoint runs the configured adapter in its request and records
   running/completed/failed results. It is not a background job queue. A later
   queue can support longer model requests without changing visit uploads.
5. Persist analysis runs separately from originals, link every output to the
   exact image/visit, and make reruns auditable. Preserve unavailable visits as
   gaps in the chart and never infer zero tissue values from missing analysis.
6. Verify inference against known validation examples before displaying model
   outputs in the clinic interface.

The checkpoint root is configured through
`python -m scripts.configure_wound_models`, using the project-local checkpoints in
`backend/trained_models/wound/<model_id>/final.pt`.
The setup script writes ignored local configuration and a private runtime token,
preserving existing authentication settings and original checkpoints. Start
`python -m scripts.run_wound_runtime` from `backend` using the compatible model
environment, then restart the clinic API. Detailed runtime dependencies are in
`backend/wound_runtime/requirements.txt` and startup instructions in its README.

In the page, select a patient, wound, visit, image, and model. Run wound
segmentation first, then tissue segmentation. Saved masks and model-specific run
history appear in the analysis panels. The tissue trend chart becomes available
as visits receive both masks; no new model inference is needed to read the chart.

The backend model configuration and adapter contract are documented in
`backend/README.md`. The configuration is server controlled; a browser request
selects a stored image and analysis stage, never a model file or Python module.

## Running locally

Use two terminals with a working Python environment activated for the backend.

```powershell
cd C:\Projects\RP_Planner_373\backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

```powershell
cd C:\Projects\RP_Planner_373\frontend
npm.cmd install
npm.cmd run dev
```

Login and clinic requests use `NEXT_PUBLIC_API_URL`, defaulting to
`http://127.0.0.1:8000`. If changing it, put the setting in
`frontend/.env.local` and restart the frontend. Open
`http://127.0.0.1:3000/dashboard/wound`. Existing demo accounts remain documented
in `backend/README.md`.

After pulling this change, reinstall backend requirements and restart the API;
the new image-upload endpoints need Pillow and python-multipart.

## Verification

Backend checks run with temporary clinic files and isolated account lookups:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Frontend build:

```powershell
cd frontend
npm.cmd run build
```

Verify two patients with multiple wounds, image persistence
after refresh, out-of-order visit dates, duplicate-date rejection, and switching
between wounds without sharing their images. Without model configuration, analysis
controls stay disabled and each visit remains listed with unavailable chart data.
Check that representative-photo selection persists, switching models keeps
results separate, and missing masks create gaps. Unit tests use explicitly
synthetic masks to check storage, permissions, proportions, and stale-result
handling. A real-checkpoint smoke check uses two synthetic drawings on separate
visits with temporary accounts/clinic files:

```powershell
cd backend
python -m scripts.smoke_wound_models
```

An optional `--reference-url` compares numeric masks with the original standalone
prototype's inference. It also verifies tissue proportions directly against saved
masks and checks chronological points for both visits. This checks integration
and inference compatibility; it does not establish model
accuracy or clinical performance. Real clinic records and images are untouched by
the smoke check.
