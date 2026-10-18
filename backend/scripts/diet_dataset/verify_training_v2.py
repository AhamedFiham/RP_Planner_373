"""Verification only: audit V2 and write reports/visual copies, never train or repair.

From backend: python3 scripts/diet_dataset/verify_training_v2.py
"""
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collections import Counter,defaultdict
import argparse
import hashlib
import json
import math
import random
import re
import yaml
from PIL import Image,ImageDraw,ImageFont
from diet_dataset.validation import EXTENSIONS,inspect_image,validate_box
from diet_dataset.image_groups import group_images,read_csv
from diet_dataset.outputs import write_csv

BACKEND=Path(__file__).resolve().parents[2]
SPLITS=('train','valid','test')


class UniqueLoader(yaml.SafeLoader):
    """Reject YAML duplicate keys rather than silently overwriting class IDs."""


def unique_mapping(loader: yaml.SafeLoader,node: yaml.Node,deep: bool=False) -> dict:
    result={}
    for key_node,value_node in node.value:
        key=loader.construct_object(key_node,deep=deep)
        if key in result:raise ValueError(f'Duplicate YAML key: {key}')
        result[key]=loader.construct_object(value_node,deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)


def strict_row(line: str) -> tuple[int,list[float]]:
    fields=line.split()
    if len(fields)!=5:raise ValueError('Expected exactly five values')
    if not re.fullmatch(r'\d+',fields[0]):raise ValueError('class_id is not an integer token')
    cid=int(fields[0])
    if not 0<=cid<=45:raise ValueError('class_id outside 0–45')
    try:box=[float(value) for value in fields[1:]]
    except ValueError:raise ValueError('Nonnumeric coordinates') from None
    if not all(math.isfinite(v) for v in box):raise ValueError('NaN or infinite coordinate')
    if not validate_box(box):raise ValueError('Invalid normalized coordinates or out-of-bounds box')
    return cid,box


def coverage_status(count: int) -> str:
    return 'GOOD' if count>=5 else 'LIMITED' if count>=3 else 'CRITICAL' if count else 'MISSING'


def hashes(folder: Path,exclude_reports: bool=False) -> dict:
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file() and not (exclude_reports and (p.relative_to(folder).parts[0]=='reports' or p.name=='final_dataset_readiness.json'))}


def make_visuals(records: list[dict],names: dict,reports: Path) -> tuple[int,int]:
    rng=random.Random(42);covered=set();created=[]
    for split,limit in [('train',20),('valid',10),('test',10)]:
        candidates=[r for r in records if r['split']==split and r.get('info') and r['annotations']]
        rng.shuffle(candidates);chosen=[]
        # Random tie-breaking with a coverage-aware preference for unseen classes.
        while candidates and len(chosen)<limit:
            candidate=max(candidates,key=lambda r:len({c for c,b in r['annotations']}-covered))
            candidates.remove(candidate);chosen.append(candidate);covered.update(c for c,b in candidate['annotations'])
        out=reports/'visual_checks'/split;out.mkdir(parents=True,exist_ok=True)
        samples=[]
        for index,row in enumerate(chosen,1):
            with Image.open(row['path']) as source:canvas=source.convert('RGB')
            draw=ImageDraw.Draw(canvas)
            try:font=ImageFont.truetype('Arial.ttf',14)
            except OSError:font=ImageFont.load_default()
            for cid,(x,y,w,h) in row['annotations']:
                color=((cid*73+60)%200+55,(cid*131+90)%200+55,(cid*47+120)%200+55)
                left,top,right,bottom=(x-w/2)*canvas.width,(y-h/2)*canvas.height,(x+w/2)*canvas.width,(y+h/2)*canvas.height
                draw.rectangle([left,top,right,bottom],outline=color,width=3)
                text=f'{cid}: {names[cid]}';bounds=draw.textbbox((0,0),text,font=font);tw,th=bounds[2]-bounds[0],bounds[3]-bounds[1]
                tx=min(max(0,left),max(0,canvas.width-tw-4));ty=max(0,top-th-7)
                draw.rectangle((tx,ty,tx+tw+4,ty+th+6),fill='black');draw.text((tx+2,ty+1),text,fill=color,font=font)
            path=out/f'{index:02d}__{row["path"].stem}.jpg';canvas.save(path,quality=94)
            samples.append((path,row));created.append(dict(split=split,source_image=row['path'].name,visual_image=str(path.relative_to(reports)),class_ids=';'.join(map(str,sorted({c for c,b in row['annotations']})))))
        # Five samples per sheet keep the drawn labels legible during inspection.
        for start in range(0,len(samples),5):
            chunk=samples[start:start+5];sheet=Image.new('RGB',(1440,860),'#eeeeee');draw=ImageDraw.Draw(sheet)
            for index,(path,row) in enumerate(chunk):
                with Image.open(path) as image:
                    image.thumbnail((472,390));x=(index%3)*480;y=(index//3)*430
                    sheet.paste(image,(x+(472-image.width)//2,y+30));draw.text((x+5,y+5),f'{split} {start+index+1:02d}',fill='black')
            sheet.save(reports/'visual_checks'/f'{split}_sheet_{start//5+1}.jpg',quality=95)
    write_csv(reports/'visual_checks/sample_manifest.csv',created,['split','source_image','visual_image','class_ids'])
    return len(created),len(covered)


def verify(backend: Path) -> dict:
    diet=backend/'datasets/diet';root=diet/'training_v2';reports=root/'reports'
    raw_before=hashes(diet/'raw');v1_before=hashes(diet/'training_v1');v2_before=hashes(root,True)
    reports.mkdir(parents=True,exist_ok=True)
    yaml_checks=[]
    def check(name: str,passed: bool,details: str) -> None:yaml_checks.append(dict(check=name,status='PASS' if passed else 'FAIL',details=details))
    required=['data.yaml','selected_classes.json','validation_results.json','reports']+[f'{s}/{p}' for s in SPLITS for p in ('images','labels')]
    for item in required:check('structure_'+item,(root/item).exists(),item)
    try:
        config=yaml.load((root/'data.yaml').read_text(),Loader=UniqueLoader)
        check('yaml_valid',True,'Parsed with duplicate-key rejection')
    except (ValueError,yaml.YAMLError,OSError) as exc:
        config={};check('yaml_valid',False,str(exc))
    selected=json.loads((root/'selected_classes.json').read_text())['classes']
    names=config.get('names',{})
    if isinstance(names,list):names=dict(enumerate(names))
    check('class_count_46',len(names)==46 and config.get('nc')==46,f'nc={config.get("nc")}; names={len(names)}')
    check('class_ids_sequential',set(names)==set(range(46)),'Expected IDs 0–45')
    check('class_names_unique',len(set(names.values()))==len(names),'No duplicate canonical names')
    json_names={r['new_class_id']:r['canonical_class_name'] for r in selected}
    check('registry_match',names==json_names and len(selected)==46,'data.yaml compared with selected_classes.json')
    base=Path(config.get('path',root))
    if not base.is_absolute():base=(backend/base).resolve()
    check('dataset_root_correct',base.resolve()==root.resolve(),str(base))
    for split,key in [('train','train'),('valid','val'),('test','test')]:
        value=config.get(key,config.get('valid') if split=='valid' else None)
        path=(base/value).resolve() if isinstance(value,str) else Path('/__missing_dataset_path__')
        check(split+'_path_exists',path.is_dir() and path==(root/split/'images').resolve(),str(path))
    registry=[]
    for cid in range(46):registry.append(dict(class_id=cid,class_name_yaml=names.get(cid,''),class_name_json=json_names.get(cid,''),match=names.get(cid)==json_names.get(cid),status='PASS' if names.get(cid) and names.get(cid)==json_names.get(cid) else 'FAIL'))
    pairs=[];split_rows=[];image_rows=[];issues=[];boxes=[];records=[];counts=Counter();invalid_ids=0
    for split in SPLITS:
        folder=root/split;image_paths=sorted(p for p in (folder/'images').glob('*') if p.is_file())
        label_paths=sorted((folder/'labels').glob('*.txt'))
        image_groups=defaultdict(list)
        for path in image_paths:image_groups[path.stem].append(path)
        labels={p.stem:p for p in label_paths};empty=0
        for stem in sorted(set(image_groups)|set(labels)):
            image_found=len(image_groups.get(stem,[]))==1;label_found=stem in labels;is_empty=label_found and not labels[stem].read_text().strip()
            pairs.append(dict(split=split,stem=stem,image_found=image_found,label_found=label_found,label_empty=is_empty,status='PASS' if image_found and label_found else 'FAIL'))
        for path in image_paths:
            record=dict(path=path,split=split,annotations=[])
            try:
                if path.suffix.lower() not in EXTENSIONS:raise ValueError('Unsupported image format')
                info=inspect_image(path);record['info']=info
                with Image.open(path) as image:fmt=image.format
                image_rows.append(dict(split=split,image=path.name,width=info['width'],height=info['height'],format=fmt,status='PASS',issue=''))
            except (OSError,ValueError,Image.DecompressionBombError) as exc:
                image_rows.append(dict(split=split,image=path.name,width='',height='',format='',status='FAIL',issue=str(exc)))
            label=labels.get(path.stem)
            if label:
                text=label.read_text()
                if not text.strip():empty+=1
                for number,line in enumerate(text.splitlines(),1):
                    if not text.strip():break
                    try:cid,box=strict_row(line)
                    except ValueError as exc:
                        problem=str(exc);invalid_ids+='class_id' in problem
                        issues.append(dict(split=split,image=path.name,label_file=label.name,line_number=number,issue_type='invalid_class_id' if 'class_id' in problem else 'invalid_row',details=problem));continue
                    record['annotations'].append((cid,box));counts[(cid,split)]+=1
                    x,y,w,h=box;area=w*h;status='WARNING' if area<.0005 else 'PASS';issue='Tiny box (<0.0005 normalized area); manual review' if status=='WARNING' else ''
                    if 'info' in record:
                        width,height=record['info']['width'],record['info']['height'];left,right=(x-w/2)*width,(x+w/2)*width;top,bottom=(y-h/2)*height,(y+h/2)*height
                        if not (left<right and top<bottom and left>=-1e-4 and top>=-1e-4 and right<=width+1e-4 and bottom<=height+1e-4):status='FAIL';issue='Invalid pixel-space box'
                    boxes.append(dict(split=split,image=path.name,class_id=cid,class_name=names.get(cid,'UNKNOWN'),normalized_area=area,issue=issue,status=status))
            records.append(record)
        split_rows.append(dict(split=split,image_count=len(image_paths),label_count=len(label_paths),matched_pairs=sum(p['split']==split and p['status']=='PASS' for p in pairs),images_without_label=sum(stem not in labels for stem in image_groups),labels_without_image=sum(stem not in image_groups for stem in labels),empty_label_files=empty,status='PASS' if all(p['status']=='PASS' for p in pairs if p['split']==split) else 'FAIL'))
    leakage=[];exact=0;near_groups=set();all_paths=set();groups_for_image={}
    try:
        groups,source_records,source_classes=group_images(backend)
        groups_for_image={r['image'].name:r['group_id'] for r in source_records}
        check('provenance_available',True,f'Rebuilt {len(groups)} image groups independently from V1/raw provenance')
    except (OSError,ValueError,KeyError) as exc:check('provenance_available',False,str(exc))
    observed_groups=defaultdict(list)
    for i,row in enumerate(records):
        path=row['path'];split=row['split'];info=row.get('info')
        if str(path.resolve()) in all_paths:leakage.append(dict(issue_type='repeated_path',split_a=split,image_a=path.name,split_b=split,image_b=path.name,details='Image path repeated',status='FAIL'))
        all_paths.add(str(path.resolve()))
        group=groups_for_image.get(path.name)
        if group:observed_groups[group].append(row)
        else:check('provenance_'+path.name,False,'Image missing from V1 group provenance')
        if not info:continue
        for old in records[:i]:
            if old['split']==split or not old.get('info'):continue
            match=None
            if info['sha256']==old['info']['sha256'] or info['pixel_hash']==old['info']['pixel_hash']:
                match='exact_duplicate';exact+=1
            elif abs(info['width']/info['height']-old['info']['width']/old['info']['height'])<=.1 and (info['dhash']^old['info']['dhash']).bit_count()<=2:
                match='near_duplicate';near_groups.add(tuple(sorted([groups_for_image.get(path.name,path.name),groups_for_image.get(old['path'].name,old['path'].name)])))
            if match:leakage.append(dict(issue_type=match,split_a=old['split'],image_a=old['path'].name,split_b=split,image_b=path.name,details='Fresh SHA256/RGB/dHash comparison',status='FAIL'))
    for group,items in observed_groups.items():
        if len({r['split'] for r in items})>1:
            near_groups.add((group,group));leakage.append(dict(issue_type='family_group_leakage',split_a=items[0]['split'],image_a=items[0]['path'].name,split_b='multiple',image_b='',details=group,status='FAIL'))
    distribution=[];warnings=[]
    for cid in range(46):
        distribution.append(dict(class_id=cid,class_name=names.get(cid,''),**{s+'_annotations':counts[(cid,s)] for s in SPLITS},total_annotations=sum(counts[(cid,s)] for s in SPLITS)))
        for split in SPLITS:
            value=counts[(cid,split)];s=coverage_status(value)
            if s!='GOOD':warnings.append(dict(class_id=cid,class_name=names.get(cid,''),split=split,annotations=value,status=s))
    outputs=[
      ('data_yaml_validation',yaml_checks,['check','status','details']),
      ('split_integrity',split_rows,['split','image_count','label_count','matched_pairs','images_without_label','labels_without_image','empty_label_files','status']),
      ('class_registry_check',registry,['class_id','class_name_yaml','class_name_json','match','status']),
      ('final_annotation_validation',issues,['split','image','label_file','line_number','issue_type','details']),
      ('final_image_validation',image_rows,['split','image','width','height','format','status','issue']),
      ('image_label_pair_check',pairs,['split','stem','image_found','label_found','label_empty','status']),
      ('final_class_distribution',distribution,['class_id','class_name','train_annotations','valid_annotations','test_annotations','total_annotations']),
      ('final_class_coverage_warnings',warnings,['class_id','class_name','split','annotations','status']),
      ('final_leakage_check',leakage,['issue_type','split_a','image_a','split_b','image_b','details','status']),
      ('bounding_box_sanity',boxes,['split','image','class_id','class_name','normalized_area','issue','status'])]
    for filename,rows,fields in outputs:write_csv(reports/(filename+'.csv'),rows,fields)
    visual_count,visual_classes=make_visuals(records,names,reports)
    immutable=raw_before==hashes(diet/'raw') and v1_before==hashes(diet/'training_v1') and v2_before==hashes(root,True)
    broken=sum(r['status']=='FAIL' for r in image_rows);missing=sum(r['status']=='FAIL' for r in pairs);yaml_valid=all(r['status']=='PASS' for r in yaml_checks);box_errors=sum(r['status']=='FAIL' for r in boxes)
    readiness=dict(dataset='training_v2',class_count=len(names),**{s+'_images':sum(r['split']==s for r in records) for s in SPLITS},total_images=len(records),total_annotations=sum(counts.values()),invalid_annotations=len(issues),broken_images=broken,missing_image_label_pairs=missing,invalid_class_ids=invalid_ids,exact_cross_split_duplicates=exact,near_duplicate_cross_split_groups=len(near_groups),visual_samples_created=visual_count,visual_classes_covered=visual_classes,classes_with_zero_validation=[names[c] for c in range(46) if counts[(c,'valid')]==0],classes_with_zero_test=[names[c] for c in range(46) if counts[(c,'test')]==0],coverage_warning_rows=len(warnings),tiny_box_warnings=sum(r['status']=='WARNING' for r in boxes),data_yaml_valid=yaml_valid,class_registry_matches=names==json_names,immutable_inputs_unchanged=immutable,visual_review_status='pending manual inspection of generated samples',ready_for_training=yaml_valid and not issues and not broken and not missing and not invalid_ids and not exact and not near_groups and not leakage and not box_errors and immutable,scope='Automated readiness for exploratory baseline; sparse classes remain evaluation limitations',training_performed=False)
    readiness['automated_checks_passed']=readiness['ready_for_training']
    review_path=reports/'manual_visual_review.json'
    if review_path.exists():
        review=json.loads(review_path.read_text())
        fingerprint=hashlib.sha256(json.dumps(v2_before,sort_keys=True).encode()).hexdigest()
        current_review=review.get('dataset_fingerprint')==fingerprint
        readiness['visual_review_status']=review.get('status') if current_review else 'stale visual review; dataset changed'
        readiness['visual_review_findings']=review.get('findings',[]) if current_review else []
        readiness['visual_review_blockers']=review.get('blocking_findings',0) if current_review else 1
        readiness['ready_for_training']=readiness['automated_checks_passed'] and current_review and not readiness['visual_review_blockers']
    else:
        readiness['visual_review_blockers']=0
    (root/'final_dataset_readiness.json').write_text(json.dumps(readiness,indent=2))
    print('FINAL DIET DATASET CHECK\n'+json.dumps(readiness,indent=2))
    print('STATUS: '+('READY FOR YOLO BASELINE TRAINING' if readiness['ready_for_training'] else 'NOT READY FOR TRAINING'))
    return readiness


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    verify(BACKEND)
