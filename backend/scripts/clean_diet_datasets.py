"""Create validated, consistently named diet dataset copies; never modify raw data.

Run from backend: python scripts/clean_diet_datasets.py
Requires Pillow and PyYAML. Skips existing output directories without modifying them.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import math
import shutil
from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1] / 'datasets' / 'diet'
SOURCES = {
    'sl_meal_recognition_coco': 'SL Meal Recognition.v1i.coco-segmentation',
    'sri_lankan_food_detection_yolov8': 'sri-lankan-food-detection.v2i.yolov8',
    'food_detect2_yolov8': 'food_detetct2.v1i.yolov8',
}


def inspect_image(path):
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        im.load()
        if im.getexif().get(274, 1) != 1:
            raise ValueError('EXIF rotation needs annotation-aware manual review')
        rgb = im.convert('RGB')
        digest = hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()
        return im.size, digest


def clean(key, source_name):
    source, target = ROOT / 'raw' / source_name, ROOT / 'processed' / key
    if target.exists():
        print(f'Skipped {key}: output already exists at {target}.')
        print('Existing output was not changed or revalidated. Use a new output directory to clean updated raw data.')
        return
    # Validate before writing, so invalid labeled samples can be excluded together.
    rows, issues, seen, plans = [], [], {}, {}
    coco = key.endswith('coco')
    config = None
    if not coco:
        config = yaml.safe_load((source / 'data.yaml').read_text())
        names = config['names']
        class_ids = set(range(len(names))) if isinstance(names, list) else {int(i) for i in names}
        if int(config['nc']) != len(class_ids) or class_ids != set(range(len(class_ids))):
            raise ValueError('YOLO class names and nc must describe contiguous class IDs.')
    for split in ('test', 'valid', 'train'):
        folder = source / split
        data = json.loads((folder / '_annotations.coco.json').read_text()) if coco else None
        paths = sorted(folder.glob('*.jpg')) if coco else sorted((folder / 'images').glob('*.jpg'))
        metadata = {r['file_name']: r for r in data['images']} if coco else {}
        categories = {r['id'] for r in data['categories']} if coco else class_ids
        annotations = {}
        if coco:
            for ann in data['annotations']:
                annotations.setdefault(ann['image_id'], []).append(ann)
        accepted = []
        for index, path in enumerate(paths, 1):
            row = {'split': split, 'original': str(path.relative_to(source)), 'cleaned': '', 'status': '', 'reason': ''}
            try:
                (width, height), digest = inspect_image(path)
                if coco:
                    if path.name not in metadata:
                        raise ValueError('image missing COCO metadata')
                    record = dict(metadata[path.name])
                    if (record['width'], record['height']) != (width, height):
                        issues.append({'file': row['original'], 'warning': 'corrected COCO image dimensions'})
                    record.update(width=width, height=height)
                    labels = annotations.get(record['id'], [])
                    for ann in labels:
                        if ann['category_id'] not in categories:
                            raise ValueError('unknown COCO category')
                        box = ann.get('bbox', [])
                        if len(box) != 4 or not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
                            raise ValueError('invalid COCO bounding box')
                        x, y, w, h = box
                        if x < -1 or y < -1 or x+w > width+1 or y+h > height+1:
                            issues.append({'file': row['original'], 'warning': 'bounding box outside image; preserved for review', 'annotation_id': ann['id']})
                        seg = ann.get('segmentation', [])
                        if isinstance(seg, list):
                            for polygon in seg:
                                if len(polygon) < 6 or len(polygon) % 2 or not all(math.isfinite(v) for v in polygon):
                                    raise ValueError('invalid COCO polygon')
                else:
                    label = folder / 'labels' / (path.stem + '.txt')
                    if not label.exists():
                        raise ValueError('missing YOLO label')
                    labels = label.read_text()
                    for line in labels.splitlines():
                        values = [float(v) for v in line.split()]
                        if not values:
                            continue
                        if not all(math.isfinite(v) for v in values):
                            raise ValueError('nonfinite YOLO coordinates')
                        cls = values[0]
                        if not cls.is_integer() or int(cls) not in categories or not all(0 <= v <= 1 for v in values[1:]):
                            raise ValueError('invalid YOLO class or coordinates')
                        if len(values) == 5:
                            x, y, w, h = values[1:]
                            if min(w, h) <= 0:
                                raise ValueError('invalid YOLO bounding box')
                            if x-w/2 < -0.001 or y-h/2 < -0.001 or x+w/2 > 1.001 or y+h/2 > 1.001:
                                issues.append({'file': row['original'], 'warning': 'bounding box outside image; preserved for review'})
                        elif len(values) >= 7 and len(values) % 2 == 1:
                            points = list(zip(values[1::2], values[2::2]))
                            area = abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))) / 2
                            if area <= 0:
                                raise ValueError('zero-area YOLO polygon')
                        else:
                            raise ValueError('invalid YOLO box or polygon row')
                if digest in seen:
                    row.update(status='excluded', reason='duplicate decoded pixels of ' + seen[digest])
                else:
                    seen[digest] = row['original']
                    name = f'{split}_{index:05d}.jpg'
                    row.update(status='kept', cleaned=f'{split}/{name}' if coco else f'{split}/images/{name}')
                    if coco:
                        record['file_name'] = name
                        accepted.append((path, name, record, labels))
                    else:
                        accepted.append((path, name, labels))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                row.update(status='excluded', reason=str(exc))
            rows.append(row)
        if coco:
            existing = {p.name for p in paths}
            for name in metadata.keys() - existing:
                issues.append({'file': f'{split}/{name}', 'warning': 'COCO references missing image; excluded'})
        else:
            stems = {p.stem for p in paths}
            for label in (folder / 'labels').glob('*.txt'):
                if label.stem not in stems:
                    issues.append({'file': str(label.relative_to(source)), 'warning': 'orphan label; excluded'})
        plans[split] = (data, accepted)
    target.mkdir(parents=True)
    for split, (data, accepted) in plans.items():
        folder = target / split
        (folder if coco else folder / 'images').mkdir(parents=True)
        if not coco:
            (folder / 'labels').mkdir()
        for item in accepted:
            path, name = item[:2]
            shutil.copy2(path, folder / name if coco else folder / 'images' / name)
            if not coco:
                (folder / 'labels' / (Path(name).stem + '.txt')).write_text(item[2])
        if coco:
            data['images'] = [item[2] for item in accepted]
            data['annotations'] = [ann for item in accepted for ann in item[3]]
            (folder / '_annotations.coco.json').write_text(json.dumps(data, indent=2))
    for p in source.iterdir():
        if p.is_file() and p.suffix.lower() == '.txt':
            shutil.copy2(p, target / p.name)
    if not coco:
        config.update(path=str(target), train='train/images', val='valid/images', test='test/images')
        (target / 'data.yaml').write_text(yaml.safe_dump(config, sort_keys=False))
    with (target / 'manifest.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['split', 'original', 'cleaned', 'status', 'reason'])
        writer.writeheader()
        writer.writerows(rows)
    report = {'source': source_name, 'counts': dict(Counter(r['status'] for r in rows)), 'splits': {s: len(p[1]) for s, p in plans.items()}, 'issues': issues, 'excluded': [r for r in rows if r['status'] != 'kept'], 'duplicate_policy': 'Decoded RGB pixel hash; retain test, then valid, then train. Near duplicates and semantic labels need manual review.'}
    (target / 'cleaning_report.json').write_text(json.dumps(report, indent=2))
    (target / 'README.md').write_text('# Cleaned diet dataset\n\nOriginal images are copied without resizing or re-encoding. Names and annotation references are updated together. Original class names and IDs are preserved. Exact decoded-pixel duplicates and invalid samples are excluded; see manifest.csv and cleaning_report.json. Near duplicates and semantic annotation correctness have not been reviewed.\n')
    print(key, json.dumps({k: report[k] for k in ('counts', 'splits')}), 'warnings:', len(issues))


if __name__ == '__main__':
    for key, source_name in SOURCES.items():
        clean(key, source_name)
