"""Build annotation-aware training copies with one shared food taxonomy.

Raw and processed sources stay intact. Refuses to overwrite normalized output.
Run from backend: python3 scripts/normalize_diet_classes.py
"""
from pathlib import Path
from collections import Counter
import csv
import json
import re
import shutil
import yaml

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND / 'datasets/diet'


def key(name):
    return re.sub(r'[^a-z0-9]+', ' ', name.casefold()).strip()


ALIASES = {
    'dhal': 'Dhal_Curry', 'dhal curry': 'Dhal_Curry',
    'white rice': 'White_Rice', 'polished rice': 'White_Rice',
    'milk rice': 'Kiribath', 'kiribath': 'Kiribath',
    'gotukola mallum': 'Gotukola_Sambol', 'gotukola sambol': 'Gotukola_Sambol',
    'watalappan': 'Watalappam', 'watalappam': 'Watalappam',
    'papadam': 'Pappadam', 'pappadam': 'Pappadam',
    'bittergourd curry': 'Bitter_Gourd_Curry', 'bitter gourd curry': 'Bitter_Gourd_Curry',
    'prawn curry': 'Shrimp_Curry', 'shrimp curry': 'Shrimp_Curry',
    'tempered sprats': 'Tempered_Sprats', 'sprats tempered': 'Tempered_Sprats',
    'pol sambol': 'Coconut_Sambol', 'coconut sambol': 'Coconut_Sambol',
    'cashew nuwt curry': 'Cashew_Nut_Curry', 'omlet': 'Omelette',
    'basmathi rice': 'Basmati_Rice', 'pastuerized milk': 'Pasteurized_Milk',
    'raddish curry': 'Radish_Curry',
}
DROP = {'json', 'spoon', 'meal items'}
REVIEW = {'beat', 'curb', 'flavourd mild cartoons', 'yougurt molk', 'kotu roti', 'brinjol curry', 'pitu red', 'pitu white', 'fish', 'chicken', 'beans', 'coconut relish', 'mallum', 'common mallum', 'egg', 'potato', 'snake gourd'}


def canonical(name):
    value = key(name)
    if value in DROP:
        return None
    return ALIASES.get(value, '_'.join(part.capitalize() for part in value.split()))


def source_classes(dataset):
    if (dataset / 'classes.json').exists():
        return {int(cid): name for name, cid in json.loads((dataset / 'classes.json').read_text()).items()}
    if (dataset / 'data.yaml').exists():
        config = yaml.safe_load((dataset / 'data.yaml').read_text())
        names = config['names']
        return dict(enumerate(names)) if isinstance(names, list) else {int(k): v for k, v in names.items()}
    paths = list(dataset.glob('*/_annotations.coco.json'))
    if paths:
        return {cat['id']: cat['name'] for cat in json.loads(paths[0].read_text())['categories']}
    return {}


def normalize():
    target = ROOT / 'normalized'
    if target.exists():
        raise FileExistsError('Normalized output already exists; preserve or move it before rebuilding.')
    datasets = {d.name: (d, source_classes(d)) for d in sorted((ROOT / 'processed').iterdir()) if d.is_dir()}
    datasets = {name: item for name, item in datasets.items() if item[1]}
    names = sorted({canonical(name) for _, classes in datasets.values() for name in classes.values()} - {None})
    registry = BACKEND / 'config/diet_classes.json'
    ids = json.loads(registry.read_text()) if registry.exists() else {}
    if set(ids.values()) != set(range(len(ids))):
        raise ValueError('Existing class registry must contain contiguous IDs.')
    for name in names:
        if name not in ids:
            ids[name] = len(ids)
    names = [name for name, index in sorted(ids.items(), key=lambda item: item[1])]
    mapping = []
    for dataset, (_, classes) in datasets.items():
        for old, name in classes.items():
            mapped = canonical(name)
            mapping.append(dict(dataset=dataset, original_class_id=old, original_name=name, canonical_class_id=ids[mapped] if mapped else '', canonical_name=mapped or '', action='keep' if mapped else 'drop', review_required=key(name) in REVIEW, decision='user_requested_merge' if key(name) in {'dhal','dhal curry','white rice','polished rice','milk rice','kiribath','gotukola mallum','gotukola sambol'} else 'alias_or_spelling' if key(name) in ALIASES else 'remove_nonfood' if not mapped else 'preserve_meaning_format_only'))
    target.mkdir()
    (target / 'classes.json').write_text(json.dumps(ids, indent=2))
    (BACKEND / 'config/diet_classes.json').write_text(json.dumps(ids, indent=2))
    summary = {}
    for dataset, (source, classes) in datasets.items():
        dest = target / dataset
        dest.mkdir()
        remap = {old: ids[canonical(name)] if canonical(name) else None for old, name in classes.items()}
        if (source / 'classes.json').exists():
            shutil.copytree(source / 'images', dest / 'images')
            with (source / 'manifest.csv').open() as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                old = int(row['class_id'])
                row['class_id'] = remap[old]
                row['food_name'] = canonical(classes[old])
            with (dest / 'manifest.csv').open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
            (dest / 'classes.json').write_text(json.dumps({canonical(name): remap[old] for old, name in classes.items()}, indent=2))
            summary[dataset] = dict(kept_images=sum(r['status']=='kept' for r in rows), split='unsplit', task='classification')
            continue
        counts = Counter()
        empty = 0
        for split in ('train', 'valid', 'test'):
            src, dst = source / split, dest / split
            shutil.copytree(src, dst)
            if (src / 'labels').exists():
                for label in (dst / 'labels').glob('*.txt'):
                    lines = []
                    for line in label.read_text().splitlines():
                        if not line.strip():
                            continue
                        fields = line.split()
                        new = remap[int(fields[0])]
                        if new is None:
                            counts['removed_annotations'] += 1
                            continue
                        lines.append(str(new) + ' ' + ' '.join(fields[1:]))
                        counts['kept_annotations'] += 1
                    label.write_text('\n'.join(lines) + ('\n' if lines else ''))
                    if not lines:
                        empty += 1
            else:
                path = dst / '_annotations.coco.json'
                data = json.loads(path.read_text())
                annotations = []
                for ann in data['annotations']:
                    new = remap[ann['category_id']]
                    if new is None:
                        counts['removed_annotations'] += 1
                        continue
                    ann['category_id'] = new
                    annotations.append(ann)
                    counts['kept_annotations'] += 1
                data['annotations'] = annotations
                data['categories'] = [dict(id=i, name=name, supercategory='food') for name, i in ids.items()]
                used = {ann['image_id'] for ann in annotations}
                empty += sum(img['id'] not in used for img in data['images'])
                path.write_text(json.dumps(data, indent=2))
        if (source / 'data.yaml').exists():
            config = yaml.safe_load((source / 'data.yaml').read_text())
            config.update(path=str(dest.resolve()), names=names, nc=len(names), train='train/images', val='valid/images', test='test/images')
            (dest / 'data.yaml').write_text(yaml.safe_dump(config, sort_keys=False))
        for filename in ('README.roboflow.txt', 'README.dataset.txt'):
            if (source / filename).exists():
                shutil.copy2(source / filename, dest / filename)
        summary[dataset] = dict(counts, background_images=empty)
    report = dict(canonical_classes=len(ids), datasets=summary, limitations=['Ambiguous original meanings retained and marked review_required in mapping CSV', 'Gotukola Mallum merged into Gotukola_Sambol at user request', 'Removed-class objects are omitted; images with no remaining annotations are background images', 'Dataset formats and train/valid/test splits are separate and unchanged', 'Existing cross-dataset duplicate warning still applies'])
    (target / 'normalization_report.json').write_text(json.dumps(report, indent=2))
    output = BACKEND / 'config/diet_class_mapping.csv'
    with output.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mapping[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(mapping)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    normalize()
