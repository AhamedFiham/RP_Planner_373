"""Export dataset class names and annotation/image counts to processed/food_names.csv."""
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collections import Counter
import csv
import json
import yaml

ROOT = Path(__file__).resolve().parents[2] / 'datasets' / 'diet' / 'processed'


def export_food_names():
    prepared = ROOT.parent / 'normalized/reports'
    if (prepared / 'pipeline_metadata.json').exists():
        import shutil
        shutil.copy2(prepared / 'food_names.csv', ROOT / 'food_names.csv')
        print('Exported food names from the validated modular pipeline reports.')
        return
    rows = []
    normalized = ROOT.parent / 'normalized'
    using_normalized = (normalized / 'normalization_report.json').exists()
    source_root = normalized if using_normalized else ROOT
    for dataset in sorted(source_root.iterdir()):
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
            if using_normalized and not counts[cid]:
                continue
            rows.append(dict(dataset=dataset.name, class_id=cid, food_name=name, annotation_count=counts[cid]))
    output = ROOT / 'food_names.csv'
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['dataset', 'class_id', 'food_name', 'annotation_count'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(f'Exported {len(rows)} class entries to {output}', flush=True)


if __name__ == '__main__':
    export_food_names()
