# Food recognition reference

The supplied `.ipynb` is a training notebook, not an image dataset. It references
`fruit-and-vegetable-image-recognition` under Kaggle input paths. Those source
images are not present locally, so no images were cleaned or added for it.

`food_recognition_reference.ipynb` is a sanitized copy with historical outputs
and the embedded API key removed. Validation image selection and inference
preprocessing were corrected. It has not been executed or trained locally.
Run it with the working directory `backend/notebooks/diet`. It needs TensorFlow,
NumPy, pandas, matplotlib, Pillow, requests, and python-dotenv; these notebook
training packages are not installed automatically as backend runtime dependencies.

Provide the source dataset with `train/`, `test/`, and `validation/` class folders
under `backend/datasets/diet/raw/fruit-and-vegetable-image-recognition/`, or set
`FRUIT_VEGETABLE_DATASET_DIR` to its absolute path. The optional nutrition request
reads `API_NINJAS_API_KEY` from the backend environment. No credential is included.

`reference_food_names.csv` records 36 names from the original notebook's saved
label-list output, preserving spelling. In the shared `food_names.csv`, these
rows use dataset `fruit_vegetable_notebook_reference`, an empty class_id, and
annotation_count 0. These are neither verified image counts nor model class IDs.
The 68 existing dataset class entries remain unchanged.

Regenerate with `python3 scripts/prepare_food_notebook.py`, then
`python3 scripts/export_food_names.py`, from `backend`.
