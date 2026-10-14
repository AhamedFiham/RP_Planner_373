"""Validate and organize Fruits-360 classification images without editing raw data."""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
import csv
import hashlib
import json
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'datasets' / 'diet'


def inspect(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            if image.getexif().get(274, 1) != 1:
                raise ValueError('EXIF rotation requires review')
            rgb = image.convert('RGB')
            digest = hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()
            return digest, '', image.size
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        return None, str(exc), None


def clean_fruits():
    source = ROOT / 'raw' / 'fruits-360-100x100-main'
    target = ROOT / 'processed' / 'fruits360_classification'
    if target.exists():
        print(f'Skipped Fruits-360: {target} already exists.', flush=True)
        return
    classes = sorted({d.name for split in ('Training', 'Test') for d in (source / split).iterdir() if d.is_dir()})
    ids = {name: index for index, name in enumerate(classes)}
    target.mkdir(parents=True)
    (target / 'classes.json').write_text(json.dumps(ids, indent=2))
    seen, counts, exclusions, conflicts, dimensions = {}, Counter(), [], [], Counter()
    total = 0
    with (target / 'manifest.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['split', 'class_id', 'food_name', 'original', 'cleaned', 'status', 'reason'])
        writer.writeheader()
        for original_split, split in (('Test', 'test'), ('Training', 'train')):
            paths = sorted(p for p in (source / original_split).rglob('*') if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
            with ThreadPoolExecutor(max_workers=8) as pool:
                for index, (path, result) in enumerate(zip(paths, pool.map(inspect, paths)), 1):
                    digest, error, size = result
                    name = path.parent.name
                    row = dict(split=split, class_id=ids[name], food_name=name, original=str(path.relative_to(source)), cleaned='', status='excluded', reason=error)
                    if digest:
                        dimensions[str(size)] += 1
                        previous = seen.get(digest)
                        if previous:
                            row['reason'] = 'duplicate decoded pixels of ' + previous['original']
                            if previous['food_name'] != name:
                                conflicts.append({'original':row['original'], 'class':name, 'duplicate_of':previous})
                                row['reason'] = 'duplicate pixels with conflicting class; manual review required: ' + previous['original']
                        else:
                            seen[digest] = {'original': row['original'], 'food_name': name, 'split': split}
                            dest = target / split / name / f'{split}_{index:06d}{path.suffix.lower()}'
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(path, dest)
                            row.update(cleaned=str(dest.relative_to(target)), status='kept', reason='')
                    counts[f'{split}_{row["status"]}'] += 1
                    if row['status'] == 'excluded':
                        exclusions.append(row)
                    writer.writerow(row)
                    total += 1
                    if total % 10000 == 0:
                        print(f'Fruits-360: checked {total} images', flush=True)
            handle.flush()
    for name in ('LICENSE', 'README.md'):
        if (source / name).exists():
            shutil.copy2(source / name, target / ('SOURCE_README.md' if name == 'README.md' else name))
    report = dict(source=source.name, total_images=total, classes=len(classes), counts=dict(counts), dimensions=dict(dimensions), excluded=exclusions, conflicting_labels=conflicts, duplicate_policy='Exact RGB pixel hashes; retain test before train. Conflicting duplicate labels excluded for review. Near duplicates not checked.')
    (target / 'cleaning_report.json').write_text(json.dumps(report, indent=2))
    (target / 'README.md').write_text('# Fruits-360 classification\n\nImages are organized as train/<class>/ and test/<class>/. Original bytes and class names are preserved. No validation split was invented. classes.json assigns stable alphabetical class IDs. manifest.csv maps originals to outputs. cleaning_report.json records exclusions and label conflicts. Raw files remain untouched. Near duplicates and semantic labels have not been reviewed.\n')
    print('Fruits-360 complete:', json.dumps(dict(counts)), flush=True)


if __name__ == '__main__':
    clean_fruits()
