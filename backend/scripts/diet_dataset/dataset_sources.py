"""Food taxonomy, dynamic dataset discovery, and input auditing."""
import re
from pathlib import Path
import json
import yaml
from collections import Counter, defaultdict
import hashlib
import logging
from PIL.Image import DecompressionBombError as ImageError
from .validation import inspect_image, EXTENSIONS
from .validation import parse_row
from .validation import convert_bbox
from .image_groups import deduplicate


# Normalize classes

ALIASES = {
 'dhal':'Dhal_Curry','dhal curry':'Dhal_Curry','white rice':'White_Rice','polished rice':'White_Rice',
 'milk rice':'Kiribath','kiribath':'Kiribath','beat':'Beetroot','beetroot':'Beetroot',
 'brinjol curry':'Brinjal_Curry','brinjal curry':'Brinjal_Curry',
 'pitu white':'White_Pittu','pittu white':'White_Pittu','pitu red':'Red_Pittu','pittu red':'Red_Pittu',
 'gotukola mallum':'Gotukola_Sambol','gotukola sambol':'Gotukola_Sambol',
 'cashew nuwt curry':'Cashew_Nut_Curry','omlet':'Omelette','basmathi rice':'Basmati_Rice',
 'potato milkycurry':'Potato_Milky_Curry','yougurt molk':'Yoghurt_Milk',
 'pastuerized milk':'Pasteurized_Milk','raddish curry':'Radish_Curry',
 'bittergourd curry':'Bitter_Gourd_Curry','bitter gourd curry':'Bitter_Gourd_Curry',
 'watalappan':'Watalappam','watalappam':'Watalappam','papadam':'Pappadam','pappadam':'Pappadam',
 'prawn curry':'Shrimp_Curry','shrimp curry':'Shrimp_Curry',
 'sprats tempered':'Tempered_Sprats','tempered sprats':'Tempered_Sprats',
 'pol sambol':'Coconut_Sambol','coconut sambol':'Coconut_Sambol',
}

EXCLUDED = {'json':'Metadata label','spoon':'Non-food object','meal items':'COCO parent category, not a food'}

SUSPICIOUS = {'curb','del curry','flavourd mild cartoons'}

REVIEW = {'kotu roti','fish','chicken','beans','coconut relish','mallum','common mallum','brinjal'}

PRIORITY = ['Red_Rice','Cashew','Almond','Walnut','Pistachio','Papaya_Juice','Orange_Juice','Wood_Apple_Juice']

def key(name: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',name.casefold()).strip()

def decision(name: str) -> tuple[str | None, str, bool]:
    value = key(name)
    if value in EXCLUDED:
        return None, EXCLUDED[value], False
    if value in SUSPICIOUS:
        return None, 'Unknown meaning; quarantine pending manual review', True
    mapped = ALIASES.get(value, '_'.join(word.capitalize() for word in value.split()))
    reason = 'Explicit reviewed alias' if value in ALIASES else 'Formatting only; preparation distinctions retained'
    if value == 'gotukola mallum':
        reason = 'User-requested merge into Gotukola_Sambol; verify preparation distinction'
    return mapped, reason, value in REVIEW or value == 'gotukola mallum'

def category(name: str) -> str:
    if name in {'Apple','Green_Apple','Avocado','Banana','Guava','Mango','Orange','Papaya','Pineapple','Watermelon','Wood_Apple'}: return 'Fruits'
    if name in {'Peanut','Cashew','Almond','Walnut','Pistachio'}: return 'Nuts_Seeds'
    if name in {'Dhal_Curry','Chickpeas','Greengram_Boiled','Boiled_Cowpea','Pea_Curry','Soya_Curry'}: return 'Legumes'
    if name in {'Kavum','Kokis','Watalappam'}: return 'Traditional_Sweets'
    if any(w in name for w in ('Juice','Tea','Milk','Falooda','King_Coconut','Soft_Drinks')) and name != 'Potato_Milky_Curry': return 'Drinks'
    if any(w in name for w in ('Fish','Shrimp','Crab','Sprat','Cuttlefish','Halmasso')): return 'Fish_Seafood'
    if any(w in name for w in ('Chicken','Beef','Mutton','Pork','Egg','Omelette','Sausage','Organ_Meat')): return 'Protein'
    if name in {'Kiribath','Basmati_Rice','White_Rice','Red_Rice','Yellow_Rice','Unpolished_Rice'}: return 'Rice'
    if name in {'Fried_Rice','Kottu','Kotu_Roti','Chicken_Kottu'}: return 'Mixed_Meals'
    if any(w in name for w in ('Hopper','Pittu','Roti','Thosai','Bread','Noodles','Pasta','Oats','Muesli','Corn_Flakes','Sweet_Potato','Manioc')): return 'Cereal_Staples'
    if any(w in name for w in ('Sambol','Relish','Miris','Sauce','Chili_Paste','Jam')): return 'Condiments'
    if any(w in name for w in ('Yoghurt','Ice_Cream','Curd')): return 'Dairy'
    if any(w in name for w in ('Cake','Pudding','Jelly','Wada','Pappadam','Cutlet','French_Fries')): return 'Snacks'
    if any(w in name for w in ('Curry','Mallum','Beans','Carrot','Beetroot','Brinjal','Cucumber','Potato','Gourd','Onion','Salad','Vegetable','Jackfruit')): return 'Vegetables'
    return 'Other'


# Scan datasets

def slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+','_',name.lower()).strip('_')

def discover(raw: Path) -> tuple[list[dict],list[dict]]:
    datasets, ignored = [], []
    for folder in sorted(raw.iterdir()):
        if not folder.is_dir():
            if not folder.name.startswith('.'): ignored.append(dict(path=str(folder),reason='Not a dataset directory'))
            continue
        configs = sorted(folder.rglob('data.yaml'))
        cocos = sorted(folder.rglob('_annotations.coco.json'))
        if configs:
            for config in configs:
                data = yaml.safe_load(config.read_text());names = data['names']
                classes = dict(enumerate(names)) if isinstance(names,list) else {int(k):v for k,v in names.items()}
                if int(data.get('nc',len(classes)))!=len(classes): raise ValueError(f'nc mismatch: {config}')
                datasets.append(dict(id=slug(str(config.parent.relative_to(raw))),root=config.parent,format='yolo',classes=classes))
        elif cocos:
            roots = sorted({p.parent.parent for p in cocos})
            for root in roots:
                data = json.loads(next(root.rglob('_annotations.coco.json')).read_text())
                datasets.append(dict(id=slug(str(root.relative_to(raw))),root=root,format='coco',classes={c['id']:c['name'] for c in data['categories']}))
        else:
            split_dirs = [p for p in folder.iterdir() if p.is_dir() and p.name.lower() in {'train','training','test','valid','val','validation'}]
            class_roots = sorted({p.name for split in split_dirs for p in split.iterdir() if p.is_dir()}) if split_dirs else []
            classes = [p for p in sorted(folder.iterdir()) if p.is_dir() and any(x.suffix.lower() in {'.jpg','.jpeg','.png','.webp'} for x in p.rglob('*') if x.is_file())]
            if class_roots:
                datasets.append(dict(id=slug(folder.name),root=folder,format='classification',classes=dict(enumerate(class_roots)),class_layout='split'))
                continue
            if classes:
                datasets.append(dict(id=slug(folder.name),root=folder,format='classification',classes={i:p.name for i,p in enumerate(classes)}))
            else: ignored.append(dict(path=str(folder),reason='No recognized dataset structure'))
    ids=[d['id'] for d in datasets]
    if len(set(ids))!=len(ids): raise ValueError('Dataset name collision after normalization')
    return datasets,ignored

SPLITS={'train':'train','training':'train','valid':'valid','val':'valid','validation':'valid','test':'test'}

def read_annotations(dataset: dict, issues: list[dict], fingerprints: dict, backend: Path) -> list[dict]:
    """Load annotations only; image decoding is performed in the audit stage."""
    root=dataset['root'];records=[];classes=dataset['classes'];task=dataset['format']
    def stamp(path: Path) -> None:
        fingerprints[str(path.relative_to(backend))]=hashlib.sha256(path.read_bytes()).hexdigest()
    if task=='classification':
        folders = [(root, 'unsplit')]
        if dataset.get('class_layout')=='split':
            folders = [(p, SPLITS[p.name.lower()]) for p in sorted(root.iterdir()) if p.is_dir() and p.name.lower() in SPLITS]
        for folder, split in folders:
            for cid,name in classes.items():
                if not (folder/name).exists(): continue
                for path in sorted((folder/name).rglob('*')):
                    if path.is_file(): records.append(dict(path=path,split=split,annotations=[(cid,None)],task='classification',preserve_split=split!='unsplit'))
    elif task=='yolo':
        stamp(root/'data.yaml')
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or folder.name.lower() not in SPLITS: continue
            split=SPLITS[folder.name.lower()];images=folder/'images';labels=folder/'labels'
            paths=sorted(p for p in images.rglob('*') if p.is_file()) if images.exists() else []
            stems={p.stem for p in paths if p.suffix.lower() in EXTENSIONS}
            if labels.exists():
                for label in sorted(labels.glob('*.txt')):
                    stamp(label)
                    if label.stem not in stems: issues.append(dict(dataset=dataset['id'],path=str(label),issue='missing image for label'))
            for path in paths:
                if path.suffix.lower() not in EXTENSIONS:
                    records.append(dict(path=path,split=split,annotations=[],task='detection'));continue
                label=labels/(path.stem+'.txt');annotations=[];invalid=False;modes=set()
                if not label.exists():
                    issues.append(dict(dataset=dataset['id'],path=str(path),issue='missing label; image excluded'));invalid=True
                else:
                    text=label.read_text()
                    if not text.strip(): issues.append(dict(dataset=dataset['id'],path=str(label),issue='empty label; retained as background'))
                    for line_no,line in enumerate(text.splitlines(),1):
                        if not line.strip(): continue
                        try:
                            cid,box,mode=parse_row(line,set(classes));annotations.append((cid,box));modes.add(mode)
                        except ValueError as exc:
                            issues.append(dict(dataset=dataset['id'],path=str(label),issue=f'row {line_no}: {exc}; image excluded'));invalid=True
                records.append(dict(path=path,split=split,annotations=annotations,task='detection',invalid=invalid,conversion=','.join(sorted(modes)) or 'YOLO_detection'))
    else:
        for annotation_path in sorted(root.rglob('_annotations.coco.json')):
            stamp(annotation_path);data=json.loads(annotation_path.read_text());split=SPLITS.get(annotation_path.parent.name.lower())
            if not split: raise ValueError(f'Unknown COCO split: {annotation_path.parent}')
            by_image=defaultdict(list);image_ids={img['id'] for img in data['images']}
            for ann in data['annotations']:
                if ann['image_id'] not in image_ids: issues.append(dict(dataset=dataset['id'],path=str(annotation_path),issue='orphan COCO annotation'))
                by_image[ann['image_id']].append(ann)
            for image in data['images']:
                path=annotation_path.parent/image['file_name']
                if not path.resolve().is_relative_to(root.resolve()): raise ValueError('COCO filename escapes dataset root')
                annotations=[];invalid=False
                for ann in by_image[image['id']]:
                    try:
                        if ann['category_id'] not in classes: raise ValueError('unknown COCO category')
                        annotations.append((ann['category_id'],convert_bbox(ann.get('bbox',[]),image['width'],image['height'])))
                    except (ValueError,TypeError) as exc:
                        issues.append(dict(dataset=dataset['id'],path=str(path),issue=f'{exc}; image excluded'));invalid=True
                records.append(dict(path=path,split=split,annotations=annotations,task='detection',invalid=invalid,conversion='COCO_supplied_bbox',expected_size=(image['width'],image['height'])))
    for row in records: row['dataset']=dataset['id']
    return records

def audit(raw: Path) -> dict:
    backend = raw.parents[2]
    datasets,ignored=discover(raw)
    records=[];issues=[];broken=[];fingerprints={};mapping=[];review=[];source_counts=Counter();input_counts=Counter()
    for dataset in datasets:
        logging.info('Scanning %s (%s)',dataset['id'],dataset['format'])
        rows=read_annotations(dataset,issues,fingerprints,backend)
        mapped={cid:decision(name) for cid,name in dataset['classes'].items()}
        for row in rows:
            path=row['path']
            if path.name.startswith('.'):
                continue
            if path.suffix.lower() not in EXTENSIONS:
                broken.append(dict(dataset=dataset['id'],path=str(path),reason='unsupported file'));continue
            input_counts[dataset['id']]+=1
            try:
                info=inspect_image(path)
                fingerprints[str(path.relative_to(backend))]=info['sha256']
                if 'expected_size' in row and tuple(row['expected_size'])!=(info['width'],info['height']):
                    raise ValueError('COCO dimension metadata does not match decoded image')
                row.update(info)
            except (OSError,ValueError,ImageError) as exc:
                broken.append(dict(dataset=dataset['id'],path=str(path),reason=str(exc)));continue
            annotations=[];quarantine=False
            for cid,box in row['annotations']:
                source_counts[(dataset['id'],cid)]+=1
                name,reason,needs_review=mapped[cid]
                if key(dataset['classes'][cid]) in SUSPICIOUS: quarantine=True
                if name: annotations.append((name,box))
            if row.get('invalid') or quarantine: continue
            row['annotations']=annotations
            if row['task']=='classification':
                if not annotations: continue
                row['canonical']=annotations[0][0]
            records.append(row)
        for cid,name in dataset['classes'].items():
            canonical,reason,needs_review=mapped[cid]
            mapping.append(dict(source_dataset=dataset['id'],source_class_id=cid,source_class_name=name,canonical_class_name=canonical or '',include=bool(canonical),reason=reason))
            if needs_review:
                review.append(dict(dataset=dataset['id'],original_class=name,annotation_count=source_counts[(dataset['id'],cid)],reason=reason,suggested_action='Review images and confirm semantic meaning; quarantined' if not canonical else 'Review retained distinction or explicit alias'))
    kept,duplicates,leakage=deduplicate(records)
    for path in sorted(raw.rglob('*')):
        if path.is_file(): fingerprints[str(path.relative_to(backend))]=hashlib.sha256(path.read_bytes()).hexdigest()
    fingerprint=hashlib.sha256(json.dumps(fingerprints,sort_keys=True).encode()).hexdigest()
    return dict(datasets=datasets,ignored=ignored,records=kept,issues=issues,broken=broken,mapping=mapping,review=review,duplicates=duplicates,leakage=leakage,fingerprint=fingerprint,input_counts=input_counts,raw_manifest=fingerprints)
