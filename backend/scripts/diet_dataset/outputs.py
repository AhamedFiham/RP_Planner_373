"""Dataset reports and safe publication of prepared output trees."""
from pathlib import Path
import csv
from collections import Counter, defaultdict
import json
from .dataset_sources import PRIORITY, category
from collections import Counter
import hashlib
import logging
import shutil
from datetime import datetime, timezone
import yaml
from .dataset_sources import category


# Generate reports

def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n',extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def imbalance(count: int) -> str:
    for maximum,status in [(20,'Critical'),(50,'Very_Low'),(100,'Low'),(200,'Acceptable'),(500,'Good')]:
        if count<maximum: return status
    return 'Strong'

def report(audit_data: dict, folder: Path) -> tuple[dict,list[str]]:
    records=audit_data['records']
    names=sorted({r['canonical_class_name'] for r in audit_data['mapping'] if r['include']} | set(PRIORITY))
    ids={name:i for i,name in enumerate(names)}
    ann_counts=Counter();class_counts=Counter();sources=defaultdict(set);split_counts=Counter();by_dataset=defaultdict(Counter)
    for row in records:
        by_dataset[row['dataset']][row['split']]+=1
        split_counts[(row['task'],row['split'])]+=1
        for name,box in row['annotations']:
            class_counts[(row['task'],name)]+=1
            if row['task']=='detection': ann_counts[(name,row['split'])]+=1
            sources[name].add(row['dataset'])
    fields=['class_id','food_name','category','train_annotations','valid_annotations','test_annotations','total_annotations','source_datasets']
    distribution=[];imbalances=[];missing=[]
    for name in names:
        counts={s:ann_counts[(name,s)] for s in ('train','valid','test')}
        total=sum(counts.values())
        distribution.append(dict(class_id=ids[name],food_name=name,category=category(name),**{s+'_annotations':v for s,v in counts.items()},total_annotations=total,source_datasets=';'.join(sorted(sources[name]))))
        classification=class_counts[('classification',name)]
        imbalances.append(dict(class_id=ids[name],food_name=name,detection_annotations=total,classification_images=classification,status=imbalance(total),classification_status=imbalance(classification),note='Development heuristic; classification images are not detection annotations'))
        if name in PRIORITY and total+classification==0: missing.append(dict(food_name=name,status='data_needed',reason='No usable images or annotations'))
    configs={name:dict(id=ids[name],category=category(name),status='available' if sources[name] else 'data_needed',detection_annotations=class_counts[('detection',name)],classification_images=class_counts[('classification',name)]) for name in names}
    folder.mkdir(parents=True,exist_ok=True)
    write_csv(folder/'class_distribution.csv',distribution,fields)
    write_csv(folder/'class_imbalance.csv',imbalances,['class_id','food_name','detection_annotations','classification_images','status','classification_status','note'])
    write_csv(folder/'missing_priority_classes.csv',missing,['food_name','status','reason'])
    for file,rows,columns in [
      ('classes_needing_manual_review',audit_data['review'],['dataset','original_class','annotation_count','reason','suggested_action']),
      ('duplicates',audit_data['duplicates'],['original_path','duplicate_of','hash','dataset','action','match_type']),
      ('data_leakage',audit_data['leakage'],['original_path','duplicate_of','split','retained_split','reason','action']),
      ('broken_images',audit_data['broken'],['dataset','path','reason']),
      ('annotation_issues',audit_data['issues'],['dataset','path','issue']),
      ('ignored_inputs',audit_data['ignored'],['path','reason']),
      ('diet_class_mapping',audit_data['mapping'],['source_dataset','source_class_id','source_class_name','canonical_class_name','include','reason'])]:
        write_csv(folder/(file+'.csv'),rows,columns)
    summaries=[];conversions=[]
    for dataset in audit_data['datasets']:
        subset=[r for r in records if r['dataset']==dataset['id']];counts=by_dataset[dataset['id']]
        summaries.append(dict(dataset=dataset['id'],format=dataset['format'],**{s+'_images':counts[s] for s in ('train','valid','test')},total_images=len(subset),annotation_count=sum(len(r['annotations']) for r in subset) if dataset['format']!='classification' else 0,class_count=len({n for r in subset for n,b in r['annotations']})))
        if dataset['format']!='classification': conversions.append(dict(dataset=dataset['id'],source_format=';'.join(sorted({r.get('conversion','yolo') for r in subset})),output_format='YOLO_detection',images_processed=len(subset),annotations_processed=sum(len(r['annotations']) for r in subset),errors=sum(i['dataset']==dataset['id'] for i in audit_data['issues']),warnings='Polygon extents use existing annotated points' if any('polygon' in r.get('conversion','') for r in subset) else 'Only supplied geometry used'))
    write_csv(folder/'dataset_summary.csv',summaries,['dataset','format','train_images','valid_images','test_images','total_images','annotation_count','class_count'])
    write_csv(folder/'conversion_report.csv',conversions,['dataset','source_format','output_format','images_processed','annotations_processed','errors','warnings'])
    classification=[]
    for dataset in audit_data['datasets']:
        if dataset['format']=='classification':
            counts=Counter(r['canonical'] for r in records if r['dataset']==dataset['id'])
            classification.extend(dict(dataset=dataset['id'],category=category(name),class_name=name,image_count=count) for name,count in sorted(counts.items()))
    write_csv(folder/'classification_counts.csv',classification,['dataset','category','class_name','image_count'])
    food=[]
    for dataset in audit_data['datasets']:
        counts=Counter(n for r in records if r['dataset']==dataset['id'] for n,b in r['annotations'])
        food.extend(dict(dataset=dataset['id'],class_id=ids[name],food_name=name,annotation_count=count) for name,count in sorted(counts.items()))
    write_csv(folder/'food_names.csv',food,['dataset','class_id','food_name','annotation_count'])
    summary=dict(datasets_discovered=len(audit_data['datasets']),raw_images=sum(audit_data['input_counts'].values()),detection_images=sum(v for (task,s),v in split_counts.items() if task=='detection'),classification_images=sum(v for (task,s),v in split_counts.items() if task=='classification'),global_classes=len(names),available_classes=sum(v['status']=='available' for v in configs.values()),exact_duplicate_images=sum(r['action']=='exclude_exact_duplicate' for r in audit_data['duplicates']),near_duplicate_quarantines=sum('near_duplicate' in r['action'] and 'quarantine' in r['action'] for r in audit_data['duplicates']),broken_images=len(audit_data['broken']),splits={task:{s:split_counts[(task,s)] for s in ('train','valid','test')} for task in ('detection','classification')},missing_priority=[r['food_name'] for r in missing],critical_detection=[r['food_name'] for r in imbalances if r['detection_annotations']<20],raw_fingerprint=audit_data['fingerprint'])
    (folder/'summary.json').write_text(json.dumps(summary,indent=2))
    (folder/'proposed_diet_classes.json').write_text(json.dumps(configs,indent=2))
    (folder/'raw_integrity_manifest.json').write_text(json.dumps(audit_data['raw_manifest'],indent=2,sort_keys=True))
    return summary,names


# Merge detection datasets

def write_outputs(data: dict, reports: Path, names: list[str], backend: Path, force: bool) -> None:
    diet=backend/'datasets/diet';normalized=diet/'normalized';processed=diet/'processed'
    marker=normalized/'reports/pipeline_metadata.json'
    code_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
    signature=dict(raw_fingerprint=data['fingerprint'],pipeline_hash=code_hash)
    if marker.exists() and not force:
        if json.loads(marker.read_text())==signature:
            logging.info('No changes: prepared outputs already match raw files and pipeline version.')
            return
        raise FileExistsError('Prepared data differs from current inputs/code. Use --force to archive and rebuild generated outputs.')
    destinations=[normalized/'detection',normalized/'classification',normalized/'reports',processed/'yolo_detection',processed/'coco_converted',processed/'classification']
    if not force and any(p.exists() for p in destinations):
        raise FileExistsError('Generated target exists without matching completion marker. Use --force to archive it.')
    # Audit and execution must use exactly the same original bytes.
    for relative,digest in data['raw_manifest'].items():
        if hashlib.sha256((backend/relative).read_bytes()).hexdigest()!=digest:
            raise RuntimeError(f'Raw input changed during preparation: {relative}')
    stage=processed/'reports/pipeline_staging'
    if stage.exists(): raise FileExistsError('Unfinished staging folder exists; preserve/review it before retrying.')
    stage.mkdir()
    for directory in ('detection','classification','reports','yolo_detection','coco_converted','classification_processed'):
        (stage/directory).mkdir()
    shutil.copytree(reports,stage/'reports',dirs_exist_ok=True)
    ids={name:i for i,name in enumerate(names)};manifest=[];used=set()
    dataset_formats={d['id']:d['format'] for d in data['datasets']}
    for split in ('train','valid','test'):
        for directory in ('images','labels'): (stage/'detection'/split/directory).mkdir(parents=True)
    for row in data['records']:
        source=row['path'];split=row['split'];dataset=row['dataset']
        filename=dataset+'__'+source.name
        identifier=(row['task'],split,Path(filename).stem)
        if identifier in used:
            suffix=hashlib.sha256(str(source.relative_to(backend)).encode()).hexdigest()[:12]
            filename=dataset+'__'+source.stem+'__'+suffix+source.suffix
            identifier=(row['task'],split,Path(filename).stem)
        if identifier in used: raise ValueError('Generated filename collision')
        used.add(identifier)
        if row['task']=='detection':
            relative=Path('detection')/split/'images'/filename
            target=stage/relative;shutil.copy2(source,target)
            label=target.parent.parent/'labels'/(target.stem+'.txt')
            lines=[str(ids[name])+' '+' '.join(f'{value:.10f}' for value in box) for name,box in row['annotations']]
            label.write_text('\n'.join(lines)+ ('\n' if lines else ''))
            group='coco_converted' if dataset_formats[dataset]=='coco' else 'yolo_detection'
            intermediate=stage/group/dataset/split
            (intermediate/'images').mkdir(parents=True,exist_ok=True);(intermediate/'labels').mkdir(exist_ok=True)
            shutil.copy2(target,intermediate/'images'/filename);shutil.copy2(label,intermediate/'labels'/label.name)
        else:
            # Preserve class directories while adding explicit source and split provenance.
            group='fruits' if category(row['canonical'])=='Fruits' else 'drinks' if category(row['canonical'])=='Drinks' else dataset
            relative=Path('classification')/group/split/row['canonical']/filename
            target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            intermediate=stage/'classification_processed'/group/split/row['canonical']/filename
            intermediate.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,intermediate)
        manifest.append(dict(dataset=dataset,task=row['task'],split=split,original_path=str(source.relative_to(backend)),normalized_path=str(relative),sha256=row['sha256'],pixel_hash=row['pixel_hash'],dhash=f'{row["dhash"]:016x}',food_name=row.get('canonical',''),annotation_count=len(row['annotations'])))
    config=dict(path=str((normalized/'detection').resolve()),train='train/images',val='valid/images',test='test/images',names=dict(enumerate(names)),nc=len(names))
    (stage/'detection/data.yaml').write_text(yaml.safe_dump(config,sort_keys=False))
    for group in ('coco_converted','yolo_detection'):
        for dataset in (stage/group).iterdir():
            for split in ('train','valid','test'):
                for folder in ('images','labels'): (dataset/split/folder).mkdir(parents=True,exist_ok=True)
            conf=dict(config,path=str((processed/group/dataset.name).resolve()))
            (dataset/'data.yaml').write_text(yaml.safe_dump(conf,sort_keys=False))
    fields=['dataset','task','split','original_path','normalized_path','sha256','pixel_hash','dhash','food_name','annotation_count']
    write_csv(stage/'reports/image_manifest.csv',manifest,fields)
    (stage/'reports/pipeline_metadata.json').write_text(json.dumps(signature,indent=2))
    # Preserve old configuration and generated outputs on every explicit rebuild.
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    archive=processed/'reports/pipeline_backups'/stamp
    archive.mkdir(parents=True)
    for name in ('diet_classes.json','diet_class_mapping.csv'):
        p=backend/'config'/name
        if p.exists(): shutil.copy2(p,archive/name)
    pairs=[(stage/'detection',normalized/'detection'),(stage/'classification',normalized/'classification'),(stage/'reports',normalized/'reports'),(stage/'yolo_detection',processed/'yolo_detection'),(stage/'coco_converted',processed/'coco_converted'),(stage/'classification_processed',processed/'classification')]
    for src,dst in pairs:
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            backup=archive/('normalized' if dst.parent==normalized else 'processed')/dst.name
            backup.parent.mkdir(parents=True,exist_ok=True);dst.rename(backup)
        src.rename(dst)
    stage.rmdir()
    shutil.copy2(normalized/'reports/proposed_diet_classes.json',backend/'config/diet_classes.json')
    shutil.copy2(normalized/'reports/diet_class_mapping.csv',backend/'config/diet_class_mapping.csv')
    shutil.copy2(normalized/'reports/food_names.csv',processed/'food_names.csv')
    logging.info('Published dataset trees. Prior configurations archived in %s',archive)
