"""Export dataset class names and annotation/image counts to processed/food_names.csv."""
from pathlib import Path
from collections import Counter
import csv
import json
import yaml

ROOT = Path(__file__).resolve().parents[1] / 'datasets' / 'diet' / 'processed'


def export_food_names():
    rows = []
    for dataset in sorted(ROOT.iterdir()):
        if not dataset.is_dir():
            continue
        counts = Counter()
        if (dataset / 'classes.json').exists():
            classes = json.loads((dataset / 'classes.json').read_text())
            with (dataset / 'manifest.csv').open() as handle:
                for row in csv.DictReader(handle):
                    if row['status'] == 'kept':
                        counts[int(row['class_id'])] += 1
            pairs = [(cid, name) for name, cid in classes.items()]
        elif (dataset / 'data.yaml').exists():
            names = yaml.safe_load((dataset / 'data.yaml').read_text())['names']
            pairs = list(enumerate(names)) if isinstance(names, list) else [(int(cid), name) for cid, name in names.items()]
            for label in dataset.glob('*/labels/*.txt'):
                for line in label.read_text().splitlines():
                    if line.strip():
                        counts[int(line.split()[0])] += 1
        else:
            files = sorted(dataset.glob('*/_annotations.coco.json'))
            if not files:
                continue
            data = [json.loads(p.read_text()) for p in files]
            for split in data:
                counts.update(ann['category_id'] for ann in split['annotations'])
            pairs = [(cat['id'], cat['name']) for cat in data[0]['categories'] if counts[cat['id']]]
        for cid, name in sorted(pairs):
            rows.append(dict(dataset=dataset.name, class_id=cid, food_name=name, annotation_count=counts[cid]))
    reference = Path(__file__).resolve().parents[1] / 'notebooks/diet/reference_food_names.csv'
    if reference.exists():
        with reference.open() as handle:
            for row in csv.DictReader(handle):
                rows.append(dict(dataset='fruit_vegetable_notebook_reference', class_id='', food_name=row['food_name'], annotation_count=0))
    output = ROOT / 'food_names.csv'
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['dataset', 'class_id', 'food_name', 'annotation_count'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(f'Exported {len(rows)} class entries to {output}', flush=True)


if __name__ == '__main__':
    export_food_names()
