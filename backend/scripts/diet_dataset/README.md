# Diet Dataset Preparation

This pipeline prepares images and annotations only. It does not train a model,
create nutrition values, calculate glycemic load, or recommend meals.

## Immutable originals and preserved history

`raw/` is the permanent archive. The pipeline reads it and records SHA256 hashes
for every file; it never writes, renames, or deletes a raw file. Original
`processed/<legacy dataset>/`, `normalized/<legacy dataset>/`, and both
`normalized_before_manual_*` backup directories are preserved. Generated rebuilds
are archived under `processed/reports/pipeline_backups/`, not silently deleted.

## Run from backend

Install the existing Pillow and PyYAML requirements in your Python environment.

```sh
python3 scripts/diet_dataset/prepare_diet_dataset.py --dry-run
python3 scripts/diet_dataset/prepare_diet_dataset.py --execute
```

Dry run scans and validates the raw datasets, proposes decisions, and writes only
reports under `processed/reports/dry_run/`. It does not copy or move image data,
change class configuration, or change the food-name CSV. Execute publishes new
prepared trees. Repeating execute with the same raw files and pipeline source
is a no-op. Changed inputs require an explicit archived rebuild:

```sh
python3 scripts/diet_dataset/prepare_diet_dataset.py --execute --force
```

`--force` archives only the pipeline's generated output trees. It does not touch
raw files or old historical backups. If an interrupted build leaves
`processed/reports/pipeline_staging/`, preserve/review it before retrying; it will
not be silently overwritten. Use sufficient disk space for originals, staging,
and archived generated copies.

## Layout

```text
raw/                                 original archive (unchanged)
processed/
  yolo_detection/<source>/            cleaned YOLO boxes, shared IDs
  coco_converted/<source>/            supplied COCO boxes converted to YOLO
  classification/fruits|drinks/       separate class-folder images and splits
  reports/dry_run/                    scan, validation, proposed configuration
  reports/pipeline_backups/           archived generated trees/configuration
  food_names.csv                     prepared per-source class counts
normalized/
  detection/
    train|valid|test/images|labels/    merged detection images and paired labels
    data.yaml                        explicit shared canonical class indices
  classification/
    fruits|drinks/train|valid|test/<class>/
  reports/                           final reports, manifest, log, completion marker
```

Only the new `normalized/detection/` and `normalized/classification/` trees are
current training inputs. Older per-source normalized trees have historical class
IDs and are not combined with the new configuration.

## Annotations and conversions

The scanner discovers YOLO, COCO, and class-folder datasets from their layout,
without a hardcoded source list. Supported images are JPG, JPEG, PNG, and WebP.
Images are verified and decoded before acceptance. Image bytes are preserved.
YOLO rows must have valid IDs and finite, normalized, in-bounds geometry. Missing
labels and malformed labels quarantine the image; genuinely empty label files
are reported and retained as background images. Orphan labels are reported.

COCO conversion uses the dataset's supplied bounding boxes only. YOLO polygon
annotations are converted to the axis-aligned extents of their existing points;
this is explicitly recorded as `YOLO_polygon_to_bbox`. No new box is inferred
from image content, and classification images never receive boxes. Non-food
annotations (`json`, `spoon`, and the COCO parent `Meal-items`) are omitted.
Images containing unknown suspicious classes are quarantined pending review.

## Food classes

`backend/config/diet_classes.json` now maps each canonical name to its **id**,
**category**, **status**, and detection/classification counts. It is intentionally
a new configuration schema. IDs are deterministic and alphabetical, matching
`normalized/detection/data.yaml`. They differ from the previous registry; do not
reuse the old ID mapping with this dataset or previously trained models.
`config/diet_class_mapping.csv` lists source IDs, original names, canonical names,
include/exclude status, and reasons. Preserve these files with any future model.

Explicit aliases include Dhal_Curry, White_Rice, Kiribath, Beetroot,
Brinjal_Curry, White_Pittu, Red_Pittu, Potato_Milky_Curry, and Yoghurt_Milk.
Gotukola Mallum maps to Gotukola_Sambol as requested, with a review note.
Kotu_Roti is retained separately from Kottu pending review. Unpolished_Rice is
never renamed Red_Rice. Generic and prepared foods retain their distinctions.
Unknown Curb, Del_Curry, and Flavourd_Mild_Cartoons are quarantined, not guessed.
Missing priority classes have `status: data_needed`, with no fabricated images.

## Duplicates, splits, and leakage

Exact SHA256 duplicates and decoded-RGB duplicates retain one deterministic
canonical image, prioritizing original test, then valid, then train images.
Existing detection splits and supplied classification splits are respected.
Unsplit classification images use seed 42 and per-class approximate 70/20/10
splitting. Tiny classes reserve at least one validation and one test example
when possible; exact percentages are impossible for five images.

64-bit dHash distances of at most two (with a similar aspect ratio) propose
near duplicates. Cross-split candidates are conservatively quarantined for
manual review; same-split candidates are flagged, not automatically removed.
These matches are not proof of semantic equivalence. No raw files are deleted,
and no oversampling or augmentation is performed. Removal/quarantine can change
the final split percentages. Every retained image is listed in image_manifest.csv.

## Reports

`normalized/reports/` contains:

- `dataset_summary.csv`, `conversion_report.csv`
- `class_distribution.csv`, `class_imbalance.csv`, `classification_counts.csv`
- `classes_needing_manual_review.csv`, `missing_priority_classes.csv`
- `duplicates.csv`, `data_leakage.csv`
- `broken_images.csv`, `annotation_issues.csv`, `ignored_inputs.csv`
- `diet_class_mapping.csv`, `food_names.csv`, `proposed_diet_classes.json`
- `image_manifest.csv`, `raw_integrity_manifest.json`, `summary.json`
- `pipeline_metadata.json`, `diet_dataset_preparation.log`

Logs are kept inside diet report directories because this task permits writes
only under datasets/diet, config, and scripts; no log is written to backend/outputs.

Imbalance is a development heuristic: Critical <20; Very_Low 20–49; Low 50–99;
Acceptable 100–199; Good 200–499; Strong >=500. Detection annotations and
classification image counts are reported separately. Five fruit photos do not
become five detection examples, and no augmentation inflates independent counts.

## Tests and legacy commands

Tests live inside the allowed scripts directory:

```sh
PYTHONPATH=scripts python3 -m unittest discover -s scripts/diet_dataset/tests -v
```

`export_food_names.py` uses the completed pipeline report when available.
The legacy standalone cleaners and normalization wrapper have been removed;
use `prepare_diet_dataset.py` for dataset preparation.

After adding raw files, first run dry-run, review reports, and explicitly rebuild
with --execute --force. Exporting CSV alone does not validate new raw images.

## Version 1 detection subset

The reviewed Version 1 builder reads the current global class configuration,
source mapping, class distribution, and imbalance reports. From backend:

```sh
python3 scripts/diet_dataset/build_diet_training_v1.py --dry-run
python3 scripts/diet_dataset/build_diet_training_v1.py --execute
```

`datasets/diet/training_v1/` contains a separate 46-class YOLO dataset, with
sequential IDs 0–45 and its own data.yaml and selected_classes.json. It preserves
normalized image bytes and split assignments. Only selected label rows remain
in mixed images; excluded foods are outside the Version 1 taxonomy. Images with
no selected objects are omitted. No classification-only images are copied.

The selection requires >=20 detection annotations and at least one validation
or test annotation. Unresolved broad labels are deferred. Sparse evaluation
coverage is still a limitation: reports/evaluation_coverage_warnings.csv lists
classes with fewer than five validation or test annotations. Class selection
is based on dataset readiness and Sri Lankan food relevance, not a claim that
included foods are medically recommended.

Reports include selected_classes.csv, excluded_classes.csv,
v1_class_distribution.csv, v1_split_summary.csv, image_manifest.csv, and
build_metadata.json. Repeat execute is a no-op for unchanged sources; changed
inputs require preserving the existing training_v1 folder before rebuilding.
The builder never modifies raw, normalized, or global configuration files.

## Version 2 group-aware evaluation splits

V2 preserves all 46 V1 class names and IDs (0–45), all 2,427 images, and all
6,046 annotations. Only whole related-image groups are reassigned. It never
modifies V1 or raw inputs, augments images, or trains a model.

From backend:

```sh
python3 scripts/diet_dataset/build_diet_training_v2.py --dry-run
python3 scripts/diet_dataset/build_diet_training_v2.py --execute
```

The builder groups Roboflow filename families within source datasets, byte/RGB
hash matches, dHash candidates, and transitive links through existing duplicate
reports (including excluded raw-image provenance). These are conservative
heuristics, not a guarantee that every visually related photo is discoverable.
Groups stay intact. Seed 42 makes the multilabel optimizer repeatable. It uses
coordinate descent and group swaps; optimality is not claimed.

The current result is 1,869 train, 279 validation, and 279 test images
(approximately 77% / 11.5% / 11.5%), organized under training_v2/. Every class
retains >=15 training annotations and a strict majority of its annotations in
training. Some minimum evaluation targets are mathematically impossible for the
available group sizes. Other preferred targets are unachieved under the current
coupled heuristic; these are not described as proven impossible.

Review reports/evaluation_coverage.csv, coverage_limitations.csv,
v1_vs_v2_comparison.csv, image_groups.csv, split_changes.csv, and leakage_check.csv.
validation_results.json is available both at the V2 root and in reports/.
No raw/V1 files or bounding-box coordinates changed. V2 supports an exploratory
YOLO baseline, but Dried_Halmasso and Omelette have no test examples and seven
classes remain below 3 examples in at least one evaluation split. Do not claim
reliable evaluation of all 46 classes.

Existing matching V2 output is preserved on repeated execution; different inputs
require archiving the existing training_v2 folder before rebuilding. Neither
--force nor an implicit overwrite is supported by this builder.

## Compact script organization

The helper modules are consolidated to keep the folder small:

- `dataset_sources.py`: food names, source discovery, annotation loading, audit.
- `validation.py`: image decoding, YOLO validation, and COCO box conversion.
- `image_groups.py`: duplicate checks, family grouping, and split balancing.
- `outputs.py`: reports and safe output publication.
- `prepare_diet_dataset.py`: dataset preparation command.
- `build_diet_training_v1.py` and `build_diet_training_v2.py`: subset commands.
- `export_food_names.py`: CSV export command.

`__init__.py` marks the Python package. Tests remain in `tests/`.
Command paths stay the same; this refactor does not rebuild existing datasets.

## Final V2 verification (no training or repairs)

From backend:

```sh
python3 scripts/diet_dataset/verify_training_v2.py
```

The verifier audits YAML (including duplicate keys), class registry, every image,
every strict five-column YOLO row, image-label pairs, pixel-space boxes, actual
class counts, direct SHA256/RGB/dHash matches, and reconstructed source families.
It only writes verification reports and visual copies. Raw, V1, and V2 source
images/labels/configuration remain unchanged.

Forty seeded coverage-aware samples (20 train, 10 valid, 10 test) are drawn under
training_v2/reports/visual_checks/. They collectively cover all 46 classes.
Read final_dataset_readiness.json for the current result. Automated format and
leakage checks pass, but visual review identified three unresolved source-label
quality concerns: an apparent fried egg labeled Omelette, an over-wide Kokis
box, and an extra White_Rice box outside the rice portion. Findings are in
reports/visual_annotation_review.csv; images and boxes were not changed.

The conservative readiness decision is currently **false pending label review**.
This is separate from sparse evaluation-coverage warnings. A stored manual review
is tied to a source-file fingerprint; it cannot automatically certify changed
data. Rerunning the verifier preserves unresolved review findings.

## Corrected Version 3

`training_v3/` is derived only from V2's three approved visual-review cases.
The exact incorrect Omelette row and approved extra White_Rice row are removed.
The uncertain Kokis image is excluded with its sole annotation; no identity or
new bounding box is guessed. No other label rows, retained image bytes, class IDs,
or split assignments change. Raw, V1, and V2 remain immutable.

```sh
python3 scripts/diet_dataset/correct_training_v3.py
```

The command refuses differing existing output and preserves matching V3 output.
A newly generated V3 stays pending until its fresh comparisons are inspected;
the current output's three comparisons were inspected and marked resolved.
See training_v3/reports/annotation_corrections.csv, final_visual_review.csv,
v2_vs_v3_comparison.csv, and visual_checks/corrections/.
The final dataset has 2,426 images and 6,043 annotations, with the same 46 classes
and IDs 0–45. Its readiness JSON is true for an exploratory baseline. Existing
zero-test classes Dried_Halmasso and Omelette remain evaluation limitations.
No training, augmentation, rebalancing, or unrelated relabeling was performed.

## First YOLOv8n baseline training

Training is explicitly authorized only for YOLOv8n on V3. From backend:

```sh
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/diet_dataset/train_yolov8n.py --check
python3 scripts/diet_dataset/train_yolov8n.py
```

The script chooses CUDA, MPS, or CPU automatically. It uses yolov8n.pt,
640-pixel inputs, up to 30 epochs, patience 20, seed 42, workers 0, and batch
4 for MPS/CPU or 8 for CUDA. It stores experiment configuration, progress,
metrics, plots, and best/last checkpoints under outputs/diet/yolov8n_baseline/.
Ultralytics label caches are redirected there to preserve source datasets.
Only online training-time augmentation is used; source images remain intact.
trained_models/diet/ is not used for this baseline. Nothing trains v8s or v8m.

To resume this same experiment after interruption when last.pt exists:

```sh
python3 scripts/diet_dataset/train_yolov8n.py --resume
```

No training result is available until the training command finishes.

The baseline now defaults to 30 total epochs. To continue the interrupted
100-epoch run toward a new total of 30 without restarting:

```sh
python3 scripts/diet_dataset/train_yolov8n.py --resume --epochs 30
```

The script overrides the restored trainer epoch limit in memory, because this
Ultralytics version ignores a normal epochs argument on resume. Original
checkpoint files are not edited to change their saved training configuration.

## Saved baseline evaluation

From backend (no training):

```sh
.venv/bin/python scripts/diet_dataset/evaluate_yolov8n.py
```

Evaluates saved `outputs/diet/yolov8n_baseline/weights/best.pt` on V3 validation
and test separately. Reports, test plots, 20 prediction samples, and a seeded
50-image latency benchmark go under `outputs/diet/yolov8n_baseline/evaluation/`.
Per-class absent-ground-truth metrics stay blank, including Dried_Halmasso and
Omelette on test. Root plots describe test; each split also has its own plots.
The benchmark records its selected device and includes loading and preprocessing.
Label caches are redirected to evaluation outputs; V3 and checkpoint hashes are
checked before and after. Re-running replaces evaluation outputs only.

## YOLOv8s comparison baseline

```sh
.venv/bin/python scripts/diet_dataset/train_yolov8s.py --check
.venv/bin/python scripts/diet_dataset/train_yolov8s.py
```

The YOLOv8s runner checks the recorded YOLOv8n configuration and uses the same
V3 dataset, 640 image size, 30 epochs, patience 20, seed 42, workers 0, and fixed
batch 4 on MPS. It also checks the installed PyTorch and Ultralytics versions.
Test images are not used during training. Outputs are isolated under
`outputs/diet/yolov8s_baseline/`; the runner does not publish to trained_models.
The summary includes best epoch, validation metrics, invocation duration and
best checkpoint size. Use `--resume` only for an interrupted run with last.pt.

### YOLOv8s evaluation

```sh
.venv/bin/python scripts/diet_dataset/evaluate_yolov8s.py --device cpu
```

This entry point calls the same evaluation implementation as YOLOv8n, changing
only the run directory and report title. CPU matches the recorded YOLOv8n
benchmark device. Both runs use the same validation/test splits, metrics,
thresholds, seeded 50-image test benchmark with five warmups, and 20 prediction
samples. Results go under `outputs/diet/yolov8s_baseline/evaluation/`.
Zero-instance test classes have blank metrics and NOT_EVALUABLE_ON_TEST status.
No training or publishing to trained_models takes place.

### Compare saved baselines (no inference or training)

```sh
python3 scripts/diet_dataset/compare_yolo_models.py
```

Reads both baselines' saved metrics, per-class reports, configurations and CPU
benchmarks. Validates matching settings/support and benchmark image selection,
then writes the four comparison artifacts under `outputs/diet/model_comparison/`.
Signed differences are s minus n; relative changes use n as the denominator.
Zero-instance classes remain blank; classes with fewer than five test instances
are flagged. The recommendation is provisional and documents training-history,
operating-point, sparse-support and single-run benchmark limitations.

### Document the final selected model

```sh
python3 scripts/diet_dataset/select_best_yolo_model.py
```

Reads existing comparison/evaluation reports, verifies their metrics and hashes,
and records the application-specific final selection in
`outputs/diet/model_comparison/final_model_selection.json` and `.md`.
Conflicting source evidence stops selection before outputs are written.
No inference, training, checkpoint opening/copying, or FastAPI integration occurs.
The documents retain recall, per-class, training-history and dataset limitations.


## Train-only visual portion calibration

```sh
.venv/bin/python scripts/diet_dataset/calibrate_portion_categories.py
```

Reads the V3 taxonomy and train labels only; per-food normalized box areas produce
linear Q33/Q67 boundaries with minimum support 10. Updates `config/portion_reference.json`
and writes reports under `outputs/diet/portion_calibration/`. The explicit count
rule is 1 Small, 2 Medium, 3+ Large. References, insufficient support and degenerate
quantiles remain Unknown. No detector or dataset is modified. These are visual
research bins, not validated serving masses; grams remain null.
