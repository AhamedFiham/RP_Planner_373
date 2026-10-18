"""Build a reviewed 46-class YOLO subset; never train or modify source datasets.

From backend: python3 scripts/diet_dataset/build_diet_training_v1.py --dry-run
             python3 scripts/diet_dataset/build_diet_training_v1.py --execute
"""
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collections import Counter
import argparse
import csv
import hashlib
import json
import shutil
import yaml
from diet_dataset.validation import parse_row
from diet_dataset.outputs import write_csv

BACKEND = Path(__file__).resolve().parents[2]
AMBIGUOUS = {
    'Bonchi': 'Bean synonym/type unresolved against other bean classes',
    'Chicken': 'Generic preparation unresolved against Chicken_Curry',
    'Fish': 'Generic preparation unresolved against specific fish dishes',
    'Coconut_Relish': 'Meaning unresolved against Coconut_Sambol',
    'Meat_Curry': 'Meat type unspecified; broad overlap with specific meat curries',
    'Yoghurt_Milk': 'Original Yougurt Molk label requires visual confirmation',
}
SUSPICIOUS = {'Json','Spoon','Meal_Items','Curb','Del_Curry','Flavourd_Mild_Cartoons'}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def select_classes(config: dict, distribution: list[dict], mapping: list[dict], minimum: int = 20) -> tuple[list[dict],list[dict]]:
    """Select detection-supported classes; preserve semantically distinct foods."""
    dist = {row['food_name']: row for row in distribution}
    selected, excluded = [], []
    for name, info in sorted(config.items()):
        row = dist[name]
        count = int(row['total_annotations'])
        if count != int(info['detection_annotations']):
            raise ValueError(f'Configuration/distribution mismatch: {name}')
        reason = ''
        if name in SUSPICIOUS:
            reason = 'Non-food or suspicious class'
        elif info['status'] == 'data_needed':
            reason = 'data_needed: no usable source dataset'
        elif count == 0:
            reason = 'Classification-only; no YOLO detection annotations'
        elif count < minimum:
            reason = f'Fewer than {minimum} detection annotations'
        elif name in AMBIGUOUS:
            reason = AMBIGUOUS[name]
        elif int(row['valid_annotations']) + int(row['test_annotations']) == 0:
            reason = 'No validation or test annotations; defer until evaluation data exists'
        elif int(row['train_annotations']) == 0:
            reason = 'No training annotations'
        if reason:
            excluded.append(dict(canonical_class_name=name,reason=reason,detection_annotations=count,classification_images=info.get('classification_images',0)))
        else:
            selected.append(dict(new_class_id=len(selected),canonical_class_name=name,category=info['category'],total_annotations=count,train_annotations=int(row['train_annotations']),valid_annotations=int(row['valid_annotations']),test_annotations=int(row['test_annotations']),source_datasets=row['source_datasets']))
    # Include prior excluded source names, even when absent from the canonical registry.
    seen = set(config)
    for row in mapping:
        if str(row['include']).lower() != 'false': continue
        name = row['canonical_class_name'] or '_'.join(word.capitalize() for word in row['source_class_name'].replace('_',' ').split())
        if name not in seen:
            excluded.append(dict(canonical_class_name=name,reason='Excluded in source mapping: '+row['reason'],detection_annotations=0,classification_images=0))
            seen.add(name)
    return selected,excluded


def build(backend: Path, execute: bool = False) -> dict:
    diet = backend/'datasets/diet'
    source = diet/'normalized/detection'
    reports = diet/'normalized/reports'
    config = json.loads((backend/'config/diet_classes.json').read_text())
    mapping = read_csv(backend/'config/diet_class_mapping.csv')
    distribution = read_csv(reports/'class_distribution.csv')
    imbalance = {row['food_name']: row for row in read_csv(reports/'class_imbalance.csv')}
    selected,excluded = select_classes(config,distribution,mapping)
    for row in selected:
        if int(imbalance[row['canonical_class_name']]['detection_annotations']) != row['total_annotations']:
            raise ValueError('Imbalance and distribution reports disagree')
    if not 40 <= len(selected) <= 60:
        raise ValueError(f'Review selection policy: {len(selected)} classes is outside the V1 target of 40–60')
    global_yaml = yaml.safe_load((source/'data.yaml').read_text())
    for name,info in config.items():
        if global_yaml['names'][info['id']] != name: raise ValueError('Global class IDs disagree with data.yaml')
    new_ids = {config[row['canonical_class_name']]['id']: row['new_class_id'] for row in selected}
    valid_global_ids = {v['id'] for v in config.values()}
    manifest = {row['normalized_path']: row for row in read_csv(reports/'image_manifest.csv') if row['task']=='detection'}
    tasks = [];counts = Counter();split_counts = Counter();source_fingerprint = hashlib.sha256()
    for path in [backend/'config/diet_classes.json',backend/'config/diet_class_mapping.csv',reports/'class_distribution.csv',reports/'class_imbalance.csv']:
        source_fingerprint.update(path.read_bytes())
    source_fingerprint.update(Path(__file__).read_bytes())
    skipped = Counter()
    for split in ('train','valid','test'):
        image_dir,label_dir = source/split/'images', source/split/'labels'
        images = {p.stem:p for p in image_dir.iterdir() if p.is_file()}
        labels = {p.stem:p for p in label_dir.glob('*.txt')}
        if set(images) != set(labels): raise ValueError(f'Image-label mismatch in {split}')
        for stem,image in sorted(images.items()):
            label = labels[stem]
            source_fingerprint.update(image.name.encode());source_fingerprint.update(label.read_bytes())
            image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
            source_fingerprint.update(image_hash.encode())
            relative = str(image.relative_to(diet/'normalized'))
            record = manifest[relative]
            if image_hash != record['sha256']: raise ValueError(f'Image changed since normalized audit: {image}')
            keep = []
            for line in label.read_text().splitlines():
                if not line.strip(): continue
                cid,box,mode = parse_row(line,valid_global_ids)
                if mode != 'YOLO_detection': raise ValueError('V1 requires normalized detection boxes')
                if cid in new_ids:
                    fields = line.split()
                    keep.append(str(new_ids[cid])+' '+' '.join(fields[1:]))
                    counts[(new_ids[cid],split)] += 1
            if keep:
                tasks.append(dict(image=image,label=label,split=split,lines=keep,record=record,sha256=image_hash))
                split_counts[split] += 1
            else: skipped[split] += 1
    summary = dict(classes=len(selected),images=dict(split_counts),annotations=sum(counts.values()),omitted_images_without_selected_objects=dict(skipped),selected=[r['canonical_class_name'] for r in selected],excluded=excluded)
    if not execute: return summary
    target = diet/'training_v1'
    signature = source_fingerprint.hexdigest()
    if target.exists():
        completion = target/'reports/build_metadata.json'
        if completion.exists() and json.loads(completion.read_text())['source_fingerprint']==signature:
            print('Version 1 is unchanged; existing output preserved.')
            return summary
        raise FileExistsError('training_v1 already exists with different inputs or no completion record. Preserve it before rebuilding.')
    stage = diet/'processed/reports/training_v1_staging'
    if stage.exists(): raise FileExistsError('Previous V1 staging exists; preserve/review it before retrying.')
    stage.mkdir(parents=True)
    for split in ('train','valid','test'):
        for folder in ('images','labels'): (stage/split/folder).mkdir(parents=True)
    traced = [];seen = set()
    for task in tasks:
        record = task['record']
        if record['pixel_hash'] in seen: raise ValueError('Duplicate image in V1 source')
        seen.add(record['pixel_hash'])
        image = task['image'];split = task['split']
        shutil.copy2(image,stage/split/'images'/image.name)
        (stage/split/'labels'/task['label'].name).write_text('\n'.join(task['lines'])+'\n')
        traced.append(dict(split=split,image=image.name,source=str(image.relative_to(backend)),source_dataset=record['dataset'],sha256=task['sha256'],pixel_hash=record['pixel_hash'],annotations=len(task['lines'])))
    output_reports = stage/'reports';output_reports.mkdir()
    selected_fields = ['new_class_id','canonical_class_name','category','total_annotations','train_annotations','valid_annotations','test_annotations','source_datasets']
    write_csv(output_reports/'selected_classes.csv',selected,selected_fields)
    write_csv(output_reports/'excluded_classes.csv',excluded,['canonical_class_name','reason','detection_annotations','classification_images'])
    actual = []
    coverage = []
    for row in selected:
        item = dict(row)
        for split in ('train','valid','test'):
            item[split+'_annotations'] = counts[(row['new_class_id'],split)]
        item['total_annotations'] = sum(item[s+'_annotations'] for s in ('train','valid','test'))
        if item != row: raise ValueError('V1 exported counts differ from proposed selection')
        actual.append(item)
        if min(row['valid_annotations'],row['test_annotations']) < 5:
            coverage.append(dict(food_name=row['canonical_class_name'],valid_annotations=row['valid_annotations'],test_annotations=row['test_annotations'],warning='Sparse or missing evaluation coverage; collect more independently sourced images'))
    write_csv(output_reports/'v1_class_distribution.csv',actual,selected_fields)
    write_csv(output_reports/'v1_split_summary.csv',[dict(split=s,images=split_counts[s],annotations=sum(counts[(r['new_class_id'],s)] for r in selected),classes_present=sum(counts[(r['new_class_id'],s)]>0 for r in selected),omitted_images_without_selected_objects=skipped[s]) for s in ('train','valid','test')],['split','images','annotations','classes_present','omitted_images_without_selected_objects'])
    write_csv(output_reports/'evaluation_coverage_warnings.csv',coverage,['food_name','valid_annotations','test_annotations','warning'])
    write_csv(output_reports/'image_manifest.csv',traced,['split','image','source','source_dataset','sha256','pixel_hash','annotations'])
    payload = dict(version=1,task='object_detection',minimum_detection_annotations=20,policy='Sri Lankan meal-focused; unresolved meanings and classes without any evaluation examples deferred',mixed_images='Only selected-class annotation rows retained; excluded objects remain outside the V1 taxonomy',classes=[dict(row,global_class_id=config[row['canonical_class_name']]['id']) for row in selected])
    (stage/'selected_classes.json').write_text(json.dumps(payload,indent=2))
    (stage/'data.yaml').write_text(yaml.safe_dump(dict(path=str(target.resolve()),train='train/images',val='valid/images',test='test/images',nc=len(selected),names={r['new_class_id']:r['canonical_class_name'] for r in selected}),sort_keys=False))
    (output_reports/'build_metadata.json').write_text(json.dumps(dict(source_fingerprint=signature,classes=len(selected),images=sum(split_counts.values()),annotations=sum(counts.values()),evaluation_warning_classes=len(coverage),training_performed=False),indent=2))
    (stage/'README.md').write_text('# Diet training Version 1\n\n46 selected detection classes with sequential IDs, sourced exclusively from normalized/detection. Original split assignments and image bytes are preserved. Images without selected objects are omitted; mixed-image labels retain only selected classes, leaving other objects outside this taxonomy. No augmentation or training was performed. Reports document exclusions, counts, provenance, and sparse evaluation coverage. These IDs differ from the global taxonomy. Do not mix V1 labels with global data.yaml.\n')
    stage.rename(target)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run',action='store_true');mode.add_argument('--execute',action='store_true')
    args = parser.parse_args()
    result = build(BACKEND,args.execute)
    print(json.dumps({k:v for k,v in result.items() if k not in {'selected','excluded'}},indent=2))
    if args.dry_run:
        print('Selected:',', '.join(result['selected']))
        for row in result['excluded']: print('Excluded:',row['canonical_class_name'],'-',row['reason'])
