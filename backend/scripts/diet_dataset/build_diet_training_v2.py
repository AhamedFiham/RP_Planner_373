"""Improve evaluation coverage by moving whole image families, never modifying V1.

From backend: python3 scripts/diet_dataset/build_diet_training_v2.py --execute
"""
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collections import Counter
import argparse
import hashlib
import json
import shutil
import yaml
from diet_dataset.image_groups import group_images, read_csv
from diet_dataset.image_groups import balance, preferred_target
from diet_dataset.outputs import write_csv
from diet_dataset.validation import parse_row

BACKEND=Path(__file__).resolve().parents[2]
SPLITS=('train','valid','test')


def snapshot(folder: Path) -> dict[str,str]:
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file()}


def status(value: int) -> str:
    return 'GOOD' if value>=5 else 'LIMITED' if value>=3 else 'CRITICAL' if value else 'MISSING'


def individually_feasible(group_counts: list[int], total: int, target: int = 3) -> bool:
    """Exact per-class feasibility; other classes may impose extra restrictions."""
    budget=total-max(15,total//2+1)
    # Retain minimum used budget for capped evaluation-coverage states.
    states={(0,0):0}
    for count in group_counts:
        updated=dict(states)
        for (v,t),used in states.items():
            if used+count>budget:continue
            for key in [(min(target,v+count),t),(v,min(target,t+count))]:
                updated[key]=min(updated.get(key,budget+1),used+count)
        states=updated
    return (target,target) in states


def build(backend: Path, execute: bool) -> dict:
    diet=backend/'datasets/diet';v1=diet/'training_v1';target=diet/'training_v2'
    before_v1=snapshot(v1);before_raw=snapshot(diet/'raw')
    groups,records,selected=group_images(backend)
    if len(selected)!=46 or [r['new_class_id'] for r in selected]!=list(range(46)):
        raise ValueError('Expected exactly the existing V1 class IDs 0–45')
    # Consume V1 warnings as an explicit input and validate their class references.
    warnings=read_csv(v1/'reports/evaluation_coverage_warnings.csv')
    selected_names={r['canonical_class_name'] for r in selected}
    if any(r['food_name'] not in selected_names for r in warnings):raise ValueError('Unknown class in V1 coverage warnings')
    assignment,optimization=balance(groups,seed=42)
    groups_by_id={g['id']:g for g in groups}
    for row in records:row['new_split']=assignment[row['group_id']]
    input_digest=hashlib.sha256(json.dumps(before_v1,sort_keys=True).encode())
    for p in [Path(__file__),Path(__file__).parent/'image_groups.py',diet/'normalized/reports/duplicates.csv',diet/'normalized/reports/image_manifest.csv']:
        input_digest.update(p.read_bytes())
    signature=input_digest.hexdigest()
    counts=optimization['counts'];total=len(records);moved=sum(r['new_split']!=r['old_split'] for r in records)
    summary=dict(images_total=total,annotations_total=sum(sum(r['counts']) for r in records),train_images=optimization['images']['train'],valid_images=optimization['images']['valid'],test_images=optimization['images']['test'],classes=46,classes_with_test_zero=sum(v==0 for v in counts[2]),classes_with_valid_zero=sum(v==0 for v in counts[1]),classes_with_test_lt3=sum(v<3 for v in counts[2]),classes_with_valid_lt3=sum(v<3 for v in counts[1]),images_moved=moved,image_groups=len(groups))
    if not execute:
        return summary
    if target.exists():
        metadata=target/'reports/build_metadata.json'
        if metadata.exists() and json.loads(metadata.read_text())['input_fingerprint']==signature:
            print('V2 is unchanged; existing output preserved.')
            return summary
        raise FileExistsError('training_v2 exists with different inputs. Preserve it before rebuilding.')
    stage=diet/'processed/reports/training_v2_staging'
    if stage.exists():raise FileExistsError('Previous V2 staging exists; preserve/review it before retrying.')
    stage.mkdir(parents=True)
    for split in SPLITS:
        for folder in ('images','labels'):(stage/split/folder).mkdir(parents=True)
    for row in records:
        split=row['new_split'];image=row['image'];label=row['label']
        dst=stage/split/'images'/image.name;dst_label=stage/split/'labels'/label.name
        if dst.exists() or dst_label.exists():raise ValueError('V2 filename collision')
        shutil.copy2(image,dst);shutil.copy2(label,dst_label)
    reports=stage/'reports';reports.mkdir()
    group_rows=[];changes=[]
    for row in records:
        group_rows.append(dict(group_id=row['group_id'],image=row['image'].name,source_dataset=row['source_dataset'],original_split=row['old_split'],new_split=row['new_split'],hash=row['sha256'],perceptual_hash=f'{row["dhash"]:016x}',group_reason=row['group_reason']))
        if row['new_split']!=row['old_split']:
            changes.append(dict(image=row['image'].name,source_dataset=row['source_dataset'],old_split=row['old_split'],new_split=row['new_split'],group_id=row['group_id'],reason='Improve per-class evaluation coverage and consolidate related image families; preserve training minimum/majority'))
    write_csv(reports/'image_groups.csv',group_rows,['group_id','image','source_dataset','original_split','new_split','hash','perceptual_hash','group_reason'])
    write_csv(reports/'split_changes.csv',changes,['image','source_dataset','old_split','new_split','group_id','reason'])
    distributions=[];coverage=[];comparison=[];limits=[]
    payload=json.loads((v1/'selected_classes.json').read_text());payload['version']=2;payload['split_policy']='seed 42; indivisible provenance/hash groups; constrained multilabel balancing'
    for c,row in enumerate(selected):
        name=row['canonical_class_name'];v,t=counts[1][c],counts[2][c];class_total=sum(counts[s][c] for s in range(3))
        d=dict(class_id=c,class_name=name,category=row['category'],**{s+'_annotations':counts[i][c] for i,s in enumerate(SPLITS)},total_annotations=class_total,**{s+'_images':sum(r['counts'][c]>0 and r['new_split']==s for r in records) for s in SPLITS})
        distributions.append(d)
        coverage.append(dict(class_id=c,class_name=name,total_annotations=class_total,valid_annotations=v,test_annotations=t,valid_status=status(v),test_status=status(t)))
        def coverage_score(a: int,b: int) -> tuple:
            target=preferred_target(class_total)
            return (min(3,a)+min(3,b),min(target,a)+min(target,b),min(a,b))
        comparison.append(dict(class_name=name,v1_train=row['train_annotations'],v1_valid=row['valid_annotations'],v1_test=row['test_annotations'],v2_train=counts[0][c],v2_valid=v,v2_test=t,coverage_improved=coverage_score(v,t)>coverage_score(row['valid_annotations'],row['test_annotations'])))
        group_counts=[g['counts'][c] for g in groups if g['counts'][c]]
        target_count=preferred_target(class_total)
        if min(v,t)<target_count:
            feasible=individually_feasible(group_counts,class_total)
            reason='Minimum 3/3 impossible with indivisible groups and training floor/majority' if not feasible else 'Preferred targets not achieved under coupled image groups and constrained heuristic; not proven impossible'
            limits.append(dict(class_name=name,preferred_per_eval_split=target_count,train_annotations=counts[0][c],valid_annotations=v,test_annotations=t,minimum_training=max(15,class_total//2+1),independent_groups=len(group_counts),group_annotation_sizes=';'.join(map(str,sorted(group_counts,reverse=True))),minimum_3_each_individually_feasible=feasible,reason=reason))
        payload['classes'][c].update(train_annotations=counts[0][c],valid_annotations=v,test_annotations=t,total_annotations=class_total)
    write_csv(reports/'class_distribution.csv',distributions,['class_id','class_name','category','train_annotations','valid_annotations','test_annotations','total_annotations','train_images','valid_images','test_images'])
    write_csv(reports/'evaluation_coverage.csv',coverage,['class_id','class_name','total_annotations','valid_annotations','test_annotations','valid_status','test_status'])
    write_csv(reports/'evaluation_coverage_warnings.csv',[r for r in coverage if r['valid_status']!='GOOD' or r['test_status']!='GOOD'],['class_id','class_name','total_annotations','valid_annotations','test_annotations','valid_status','test_status'])
    write_csv(reports/'v1_vs_v2_comparison.csv',comparison,['class_name','v1_train','v1_valid','v1_test','v2_train','v2_valid','v2_test','coverage_improved'])
    write_csv(reports/'coverage_limitations.csv',limits,['class_name','preferred_per_eval_split','train_annotations','valid_annotations','test_annotations','minimum_training','independent_groups','group_annotation_sizes','minimum_3_each_individually_feasible','reason'])
    write_csv(reports/'split_summary.csv',[dict(split=s,images=optimization['images'][s],annotations=sum(counts[i]),groups=sum(assignment[g['id']]==s for g in groups),image_percentage=round(100*optimization['images'][s]/total,3)) for i,s in enumerate(SPLITS)],['split','images','annotations','groups','image_percentage'])
    conf=yaml.safe_load((v1/'data.yaml').read_text());conf['path']=str(target.resolve());(stage/'data.yaml').write_text(yaml.safe_dump(conf,sort_keys=False))
    (stage/'selected_classes.json').write_text(json.dumps(payload,indent=2))
    # Independently validate the files that will be published.
    exact={};pixel={};group_splits={};sha_violations=0;near_violations=0;image_changes=0;geometry_changes=0;observed=Counter();leakage=[]
    for row in records:
        split=row['new_split'];dst=stage/split/'images'/row['image'].name;label=stage/split/'labels'/row['label'].name
        digest=hashlib.sha256(dst.read_bytes()).hexdigest()
        image_changes+=digest!=row['sha256'];geometry_changes+=label.read_bytes()!=row['label'].read_bytes()
        for lookup,value in [(exact,digest),(pixel,row['pixel_hash'])]:
            if value in lookup and lookup[value]!=split:sha_violations+=1
            lookup[value]=split
        group_splits.setdefault(row['group_id'],set()).add(split)
        for line in label.read_text().splitlines():
            if line.strip():cid,box,mode=parse_row(line,set(range(46)));observed[(cid,split)]+=1
    near_violations=sum(len(splits)>1 for splits in group_splits.values())
    if len(exact)!=len(records) or len(pixel)!=len(records):raise ValueError('V2 contains duplicate images')
    for c in range(46):
        for i,s in enumerate(SPLITS):
            if observed[(c,s)]!=counts[i][c]:raise ValueError('Exported counts disagree with plan')
        if counts[0][c]<15 or counts[0][c]<=sum(counts[s][c] for s in (1,2)):raise ValueError('Training majority/floor violated')
    for split in SPLITS:
        if {p.stem for p in (stage/split/'images').iterdir()}!={p.stem for p in (stage/split/'labels').iterdir()}:raise ValueError('Image-label pairing mismatch')
    # Directly check all detected near edges, independently from group assignment.
    for i,row in enumerate(records):
        for old in records[:i]:
            if row['new_split']!=old['new_split'] and abs(row['width']/row['height']-old['width']/old['height'])<=.1 and (row['dhash']^old['dhash']).bit_count()<=2:
                raise ValueError('Cross-split near duplicate remains')
    raw_after=snapshot(diet/'raw');v1_after=snapshot(v1)
    if raw_after!=before_raw or v1_after!=before_v1:raise RuntimeError('Immutable source changed during build')
    summary.update(exact_cross_split_duplicates=sha_violations,near_duplicate_cross_split_groups=near_violations,image_bytes_modified=image_changes,annotation_geometry_modified=geometry_changes,raw_untouched=True,v1_untouched=True,classes_with_valid_zero_names=[r['class_name'] for r in coverage if r['valid_annotations']==0],classes_with_test_zero_names=[r['class_name'] for r in coverage if r['test_annotations']==0],classes_with_valid_lt3_names=[r['class_name'] for r in coverage if r['valid_annotations']<3],classes_with_test_lt3_names=[r['class_name'] for r in coverage if r['test_annotations']<3],classes_with_improved_coverage=sum(r['coverage_improved'] for r in comparison),raw_files_verified=len(before_raw),v1_files_verified=len(before_v1))
    if any(summary[k] for k in ['exact_cross_split_duplicates','near_duplicate_cross_split_groups','image_bytes_modified','annotation_geometry_modified']):raise ValueError('Integrity validation failed')
    for check,violations in [('exact_cross_split_duplicates',sha_violations),('near_duplicate_cross_split_groups',near_violations),('image_bytes_modified',image_changes),('annotation_geometry_modified',geometry_changes),('raw_mutations',0),('v1_mutations',0)]:leakage.append(dict(check=check,violations=violations,status='PASS' if violations==0 else 'FAIL'))
    write_csv(reports/'leakage_check.csv',leakage,['check','violations','status'])
    (stage/'validation_results.json').write_text(json.dumps(summary,indent=2));(reports/'validation_results.json').write_text(json.dumps(summary,indent=2))
    (reports/'build_metadata.json').write_text(json.dumps(dict(input_fingerprint=signature,optimizer={k:v for k,v in optimization.items() if k not in {'counts','totals'}},grouping='Roboflow families scoped by source; raw duplicate-report transitive bridges; SHA256/RGB and dHash distance<=2 with aspect-ratio difference<=0.1',seed=42,training_performed=False),indent=2))
    (reports/'v1_integrity_manifest.json').write_text(json.dumps(before_v1,indent=2,sort_keys=True))
    (reports/'raw_integrity_manifest.json').write_text(json.dumps(before_raw,indent=2,sort_keys=True))
    (stage/'README.md').write_text('# Diet detection Version 2\n\nSame 46 classes, image bytes, labels, and 2,427 independent retained image files as V1. Only group-level split assignments changed. Class IDs remain 0–45. Families and conservative perceptual candidates, including transitive links through excluded raw images, stay in one split. 42 is the split seed. No training or augmentation was performed. The constrained splitter is heuristic, not globally optimal; see coverage_limitations.csv. Training remains a strict majority and at least 15 annotations for every class. Some minimum evaluation targets cannot be achieved with current indivisible image groups. This supports exploratory baseline training but not reliable evaluation of all 46 classes.\n')
    stage.rename(target)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--dry-run',action='store_true');mode.add_argument('--execute',action='store_true');args=parser.parse_args()
    print(json.dumps(build(BACKEND,args.execute),indent=2))
