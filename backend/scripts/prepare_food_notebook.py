"""Sanitize the supplied notebook without executing it; export recorded labels.

Recorded notebook labels are references, not verified local image classes or
trained model class IDs. Raw notebook is never modified.
"""
from pathlib import Path
import csv
import json
import re

BACKEND = Path(__file__).resolve().parents[1]
SOURCE = BACKEND / 'datasets/diet/raw/food-recognition-and-calories-estimation-using-ml.ipynb'


def prepare():
    notebook = json.loads(SOURCE.read_text())
    names = set()
    for cell in notebook.get('cells', []):
        for output in cell.get('outputs', []):
            text = output.get('text', '')
            text = ''.join(text) if isinstance(text, list) else text
            match = re.search(r'Labels:\s*\[(.*?)\]', text, re.S)
            if match:
                names.update(re.findall(r"'([^']+)'", match.group(1)))
    if not names:
        raise ValueError('No recorded label list was found in notebook outputs.')
    for cell in notebook['cells']:
        if cell.get('cell_type') != 'code':
            continue
        source = ''.join(cell.get('source', []))
        source = re.sub(r"(['\"]X-Api-Key['\"]\s*:\s*)['\"][^'\"]+['\"]", r"\1os.environ['API_NINJAS_API_KEY']", source)
        source = source.replace("val_filepaths = list(test_dir.glob(r'**/*.jpg'))", "val_filepaths = list(val_dir.glob(r'**/*.jpg'))")
        source = source.replace('    img=img/255', '    img=tf.keras.applications.mobilenet_v2.preprocess_input(img)')
        source = source.replace('target_size=(224,224,3)', 'target_size=(224,224)')
        # Make filesystem dependencies explicit, rather than Kaggle-only paths.
        source = source.replace("Path('../input/fruit-and-vegetable-image-recognition/", "Path(DATASET_ROOT / '")
        source = source.replace("img_path = '/kaggle/input/fruit-and-vegetable-image-recognition/test/apple/Image_1.jpg'", "img_path = str(DATASET_ROOT / 'test/apple/Image_1.jpg')")
        source = source.replace("model.save('FV.h5')", "Path('../../trained_models/diet').mkdir(parents=True, exist_ok=True)\nmodel.save('../../trained_models/diet/FV.h5')")
        cell['source'] = source.splitlines(keepends=True)
        cell['outputs'] = []
        cell['execution_count'] = None
        cell['metadata'] = {}
    setup = "from pathlib import Path\nimport os\nfrom dotenv import load_dotenv\nload_dotenv('../../.env')\nDATASET_ROOT = Path(os.getenv('FRUIT_VEGETABLE_DATASET_DIR', '../../datasets/diet/raw/fruit-and-vegetable-image-recognition')).resolve()\nif not DATASET_ROOT.is_dir():\n    raise FileNotFoundError(f'Download the source dataset first: {DATASET_ROOT}')\n"
    notebook['cells'].insert(0, dict(cell_type='markdown', metadata={}, source=['# Food recognition reference notebook\n', 'The source images are not included. Run from backend/notebooks/diet after installing the notebook dependencies and providing the referenced dataset. Historical outputs were removed; this notebook has not been retrained or validated. API_NINJAS_API_KEY is read from the backend environment. Recorded label names are reference-only and are not model class indices.\n']))
    notebook['cells'].insert(1, dict(cell_type='code', metadata={}, source=setup.splitlines(keepends=True), outputs=[], execution_count=None))
    folder = BACKEND / 'notebooks/diet'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'food_recognition_reference.ipynb'
    output.write_text(json.dumps(notebook, indent=1))
    reference = folder / 'reference_food_names.csv'
    with reference.open('w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['food_name', 'status'])
        writer.writerows((name, 'reference_only_images_missing') for name in sorted(names))
    report = dict(source=SOURCE.name, status='source_images_missing', recorded_food_names=len(names), images_cleaned=0, required_dataset='fruit-and-vegetable-image-recognition', notebook_executed=False, changes=['Removed historical outputs and embedded API key', 'Corrected validation path and inference preprocessing', 'Added local dataset path configuration'])
    (folder / 'preparation_report.json').write_text(json.dumps(report, indent=2))
    print(f'Prepared notebook and {len(names)} reference food names; no source images available.')


if __name__ == '__main__':
    prepare()
