"""Clean manually collected Fruits class folders; preserve raw image bytes."""
from pathlib import Path
from collections import Counter
import csv
import json
import shutil
from clean_fruits_dataset import inspect

ROOT = Path(__file__).resolve().parents[1] / 'datasets/diet'


def clean_manual_dataset(source_name, dataset_name):
    source, target = ROOT / 'raw' / source_name, ROOT / 'processed' / dataset_name
    if target.exists():
        print(f'Skipped {source_name}: cleaned folder already exists.')
        return
    classes = {p.name: i for i, p in enumerate(sorted(p for p in source.iterdir() if p.is_dir()))}
    rows, seen = [], {}
    target.mkdir(parents=True)
    for name, cid in classes.items():
        for index, path in enumerate(sorted((source/name).iterdir()), 1):
            if path.suffix.lower() not in {'.webp', '.jpg', '.jpeg', '.png'}:
                continue
            digest, error, size = inspect(path)
            row = dict(split='unsplit', class_id=cid, food_name=name, original=str(path.relative_to(source)), cleaned='', status='excluded', reason=error)
            if digest and digest in seen:
                row['reason'] = 'duplicate decoded pixels of ' + seen[digest]
            elif digest:
                seen[digest] = row['original']
                dest = target/'images'/name/f'{name}_{index:04d}{path.suffix.lower()}'
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                row.update(cleaned=str(dest.relative_to(target)), status='kept', reason='')
            rows.append(row)
    (target/'classes.json').write_text(json.dumps(classes, indent=2))
    with (target/'manifest.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    report = dict(source=source_name, counts=dict(Counter(r['status'] for r in rows)), classes=len(classes), excluded=[r for r in rows if r['status']=='excluded'], limitations=['No train/test split supplied; unsplit classification only', 'Near duplicates and semantic labels need manual review'])
    (target/'cleaning_report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


def clean_manual_fruits():
    clean_manual_dataset('Fruits', 'manual_fruits_classification')


if __name__ == '__main__':
    clean_manual_fruits()
