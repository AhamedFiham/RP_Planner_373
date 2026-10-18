"""Apply only the three explicitly approved, manually reviewed V2 corrections.

No relabeling, inferred geometry, split changes, or model training.
Run from backend: python3 scripts/diet_dataset/correct_training_v3.py
"""
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collections import Counter,defaultdict
import argparse
import hashlib
import json
import shutil
import yaml
from PIL import Image,ImageDraw,ImageFont
from diet_dataset.validation import inspect_image,EXTENSIONS
from diet_dataset.verify_training_v2 import strict_row,hashes
from diet_dataset.image_groups import read_csv
from diet_dataset.outputs import write_csv

BACKEND=Path(__file__).resolve().parents[2]
OMELETTE='sl_food_v2i_yolov8__91f0cbc6d7ae8aa17b2ec76200d69a8e_jpg.rf.7083ae55152f467aab4ba7c9873da442'
KOKIS='food_detetct2_v1i_yolov8__Kokis-35-_jpeg.rf.efb4dd91a77fd4edc43d0ed43d27cacf'
RICE='sri_lankan_food_detection_v2i_yolov8__46_jpg.rf.51285f53ebe82bd2d952b8a2a90b37b0'
APPROVED = {
 ('train',OMELETTE):dict(cid=30,name='Omelette',action='removed_invalid_annotation',old='30 0.6905998047 0.2980298838 0.4460949180 0.3641863301',reason='Manually confirmed sunny-side-up egg, not an omelette; no replacement class assigned'),
 ('train',KOKIS):dict(cid=25,name='Kokis',action='excluded_image',old='25 0.5000000000 0.5000000000 0.6446808511 0.9578125000',reason='Food identity uncertain and original box covers plate/background; exclude rather than guess identity or coordinates'),
 ('test',RICE):dict(cid=44,name='White_Rice',action='removed_invalid_annotation',old='44 0.4344362744 0.4253982842 0.1613562090 0.0554534316',reason='Remove the specifically user-approved extra small rice box; preserve the lower visible-rice box and all other annotations'),
}


def approved_lines(split: str,stem: str,text: str) -> tuple[str | None,dict | None]:
    """Exact-line whitelist; unapproved annotation bytes are never rewritten."""
    rule=APPROVED.get((split,stem))
    if rule is None:return text,None
    lines=text.splitlines(keepends=True)
    matches=[i for i,line in enumerate(lines) if line.rstrip('\r\n')==rule['old']]
    if len(matches)!=1:raise ValueError(f'Approved annotation no longer matches exactly: {stem}')
    if rule['action']=='excluded_image':
        if len([line for line in lines if line.strip()])!=1:raise ValueError('Kokis image has unrelated annotations; exclusion requires review')
        return None,rule
    del lines[matches[0]]
    if not any(line.strip() for line in lines):
        return None,dict(rule,action='excluded_image',reason=rule['reason']+'; no valid annotations remain')
    return ''.join(lines),rule


def render(image: Path,label_text: str,names: dict,heading: str,excluded: bool=False) -> Image.Image:
    with Image.open(image) as source:canvas=source.convert('RGB')
    draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('Arial.ttf',16)
    except OSError:font=ImageFont.load_default()
    for line in label_text.splitlines():
        if not line.strip():continue
        cid,(x,y,w,h)=strict_row(line);color=((cid*73+60)%200+55,(cid*131+90)%200+55,(cid*47+120)%200+55)
        left,top,right,bottom=(x-w/2)*canvas.width,(y-h/2)*canvas.height,(x+w/2)*canvas.width,(y+h/2)*canvas.height
        draw.rectangle((left,top,right,bottom),outline=color,width=3)
        text=f'{cid}: {names[cid]}';box=draw.textbbox((0,0),text,font=font);tw,th=box[2]-box[0],box[3]-box[1]
        tx=min(max(left,0),max(0,canvas.width-tw-4));ty=max(0,top-th-6)
        draw.rectangle((tx,ty,tx+tw+4,ty+th+6),fill='black');draw.text((tx+2,ty+1),text,fill=color,font=font)
    framed=Image.new('RGB',(canvas.width,canvas.height+54),'white');framed.paste(canvas,(0,54));d=ImageDraw.Draw(framed)
    d.text((8,8),heading,fill='red' if excluded else 'black',font=font)
    return framed


def create(backend: Path) -> dict:
    diet=backend/'datasets/diet';source=diet/'training_v2';target=diet/'training_v3'
    before={name:hashes(diet/name) for name in ('raw','training_v1','training_v2')}
    signature=hashlib.sha256((json.dumps(before['training_v2'],sort_keys=True)+Path(__file__).read_text()).encode()).hexdigest()
    if target.exists():
        marker=target/'reports/correction_metadata.json'
        if marker.exists() and json.loads(marker.read_text())['input_fingerprint']==signature:
            print('V3 already matches these approved corrections; output preserved.')
            return json.loads((target/'final_dataset_readiness.json').read_text())
        raise FileExistsError('V3 exists with different inputs or code; preserve it before rebuilding')
    selected=json.loads((source/'selected_classes.json').read_text());names={r['new_class_id']:r['canonical_class_name'] for r in selected['classes']}
    conf=yaml.safe_load((source/'data.yaml').read_text())
    if set(names)!=set(range(46)) or conf['names']!=names or conf['nc']!=46:raise ValueError('V2 class registry mismatch')
    for (split,stem),rule in APPROVED.items():
        approved_lines(split,stem,(source/split/'labels'/f'{stem}.txt').read_text())
    stage=diet/'processed/reports/training_v3_staging'
    if stage.exists():raise FileExistsError('Existing V3 staging requires review')
    stage.mkdir(parents=True)
    reports=stage/'reports';reports.mkdir();audit=[];excluded=[];changed=set();counts=Counter();image_counts=Counter()
    for split in ('train','valid','test'):
        (stage/split/'images').mkdir(parents=True);(stage/split/'labels').mkdir()
        for image in sorted((source/split/'images').iterdir()):
            if not image.is_file():continue
            label=source/split/'labels'/f'{image.stem}.txt';text=label.read_text();new,rule=approved_lines(split,image.stem,text)
            if rule:
                audit.append(dict(split=split,image=image.name,class_id=rule['cid'],class_name=rule['name'],action=rule['action'],old_annotation=rule['old'],new_annotation='',reason=rule['reason'],manual_review_status='reviewed; pending final visual comparison'))
                changed.add((split,image.stem))
            if new is None:excluded.append((split,image.name));continue
            shutil.copy2(image,stage/split/'images'/image.name)
            if rule:(stage/split/'labels'/label.name).write_text(new)
            else:shutil.copy2(label,stage/split/'labels'/label.name)
            image_counts[split]+=1
            for line in new.splitlines():
                if line.strip():cid,_=strict_row(line);counts[(cid,split)]+=1
    if changed!=set(APPROVED):raise ValueError('Not all approved cases were processed')
    conf['path']=str(target.resolve());(stage/'data.yaml').write_text(yaml.safe_dump(conf,sort_keys=False))
    selected['version']=3;selected['correction_policy']='Only three explicitly approved V2 cases; no rebalance, relabel, or inferred geometry'
    for row in selected['classes']:
        cid=row['new_class_id']
        row.update({s+'_annotations':counts[(cid,s)] for s in ('train','valid','test')});row['total_annotations']=sum(counts[(cid,s)] for s in ('train','valid','test'))
    (stage/'selected_classes.json').write_text(json.dumps(selected,indent=2))
    write_csv(reports/'annotation_corrections.csv',audit,['split','image','class_id','class_name','action','old_annotation','new_annotation','reason','manual_review_status'])
    visual=reports/'visual_checks/corrections';visual.mkdir(parents=True);review=[]
    for index,((split,stem),rule) in enumerate(APPROVED.items(),1):
        image=next((source/split/'images').glob(stem+'.*'));old=(source/split/'labels'/f'{stem}.txt').read_text();new,_=approved_lines(split,stem,old)
        first=render(image,old,names,'V2 BEFORE - '+rule['name'])
        second=render(image,new or '',names,'V3 EXCLUDED - identity uncertain' if new is None else 'V3 AFTER - approved annotation removed',new is None)
        first.save(visual/f'issue_{index}_before.jpg',quality=95);second.save(visual/f'issue_{index}_after.jpg',quality=95)
        def tile(im):
            im.thumbnail((760,810));return im
        first,second=tile(first),tile(second)
        sheet=Image.new('RGB',(1520,max(first.height,second.height)),'#eeeeee');sheet.paste(first,(0,0));sheet.paste(second,(760,0));sheet.save(visual/f'issue_{index}_comparison.jpg',quality=96)
        review.append(dict(image=image.name,issue=rule['name'],correction=rule['reason'],status='pending_final_visual_recheck'))
    write_csv(reports/'final_visual_review.csv',review,['image','issue','correction','status'])
    # Independently verify all exported files, not just the correction plan.
    issues=[];records=[];broken=[];pairs=0;actual=Counter();geometry_differences=[];label_differences=[]
    for split in ('train','valid','test'):
        images={p.stem:p for p in (stage/split/'images').iterdir()};labels={p.stem:p for p in (stage/split/'labels').glob('*.txt')}
        pairs+=len(set(images)^set(labels))
        for stem,image in sorted(images.items()):
            src=source/split/'images'/image.name
            if image.read_bytes()!=src.read_bytes():raise ValueError('Image bytes changed')
            try:info=inspect_image(image)
            except (OSError,ValueError,Image.DecompressionBombError) as exc:broken.append(str(image)+': '+str(exc));continue
            label=labels[stem];old_label=source/split/'labels'/label.name
            if label.read_bytes()!=old_label.read_bytes():label_differences.append((split,stem))
            expected,_=approved_lines(split,stem,old_label.read_text())
            if label.read_text()!=expected:raise ValueError('Undocumented annotation difference')
            for line_no,line in enumerate(label.read_text().splitlines(),1):
                try:cid,box=strict_row(line);actual[(cid,split)]+=1
                except ValueError as exc:issues.append(dict(split=split,image=image.name,label_file=label.name,line_number=line_no,issue_type='invalid_row',details=str(exc)))
            records.append(dict(split=split,image=image.name,**info))
    if set(label_differences)!={('train',OMELETTE),('test',RICE)}:raise ValueError('Unexpected changed label files')
    if counts!=actual or pairs or broken or issues:raise ValueError('V3 automated validation failed')
    for split in ('train','valid','test'):
        original={p.name for p in (source/split/'images').iterdir()}
        output={p.name for p in (stage/split/'images').iterdir()}
        expected=original-{name for s,name in excluded if s==split}
        if output!=expected:raise ValueError('Split assignment or image inventory changed unexpectedly')
    leakage=[];groups={r['image']:r for r in read_csv(source/'reports/image_groups.csv')};observed_groups=defaultdict(set)
    for i,row in enumerate(records):
        observed_groups[groups[row['image']]['group_id']].add(row['split'])
        for old in records[:i]:
            if old['split']==row['split']:continue
            kind=None
            if row['sha256']==old['sha256'] or row['pixel_hash']==old['pixel_hash']:kind='exact_duplicate'
            elif abs(row['width']/row['height']-old['width']/old['height'])<=.1 and (row['dhash']^old['dhash']).bit_count()<=2:kind='near_duplicate'
            if kind:leakage.append(dict(issue_type=kind,split_a=old['split'],image_a=old['image'],split_b=row['split'],image_b=row['image'],details='Fresh SHA/RGB/dHash comparison',status='FAIL'))
    family_leaks=sum(len(splits)>1 for splits in observed_groups.values())
    if leakage or family_leaks:raise ValueError('V3 leakage detected')
    write_csv(reports/'final_annotation_validation.csv',issues,['split','image','label_file','line_number','issue_type','details'])
    write_csv(reports/'final_leakage_check.csv',leakage,['issue_type','split_a','image_a','split_b','image_b','details','status'])
    distributions=[]
    for cid,name in names.items():distributions.append(dict(class_id=cid,class_name=name,**{s+'_annotations':counts[(cid,s)] for s in ('train','valid','test')},total_annotations=sum(counts[(cid,s)] for s in ('train','valid','test'))))
    write_csv(reports/'final_class_distribution.csv',distributions,['class_id','class_name','train_annotations','valid_annotations','test_annotations','total_annotations'])
    v2_counts=Counter()
    for row in read_csv(source/'reports/final_class_distribution.csv'):v2_counts[row['class_name']]=int(row['total_annotations'])
    old_images={s:len(list((source/s/'images').iterdir())) for s in ('train','valid','test')}
    metrics={'total_images':(sum(old_images.values()),sum(image_counts.values())),'train_images':(old_images['train'],image_counts['train']),'valid_images':(old_images['valid'],image_counts['valid']),'test_images':(old_images['test'],image_counts['test']),'total_annotations':(sum(v2_counts.values()),sum(counts.values()))}
    for cid,name in [(30,'Omelette'),(25,'Kokis'),(44,'White_Rice')]:metrics[name+'_annotations']=(v2_counts[name],sum(counts[(cid,s)] for s in ('train','valid','test')))
    comparison=[dict(metric=key,v2=a,v3=b,difference=b-a) for key,(a,b) in metrics.items()]
    comparison.extend(dict(metric=key,v2=False,v3=False,difference=False) for key in ('class_count_changed','class_ids_changed','split_assignments_changed'))
    write_csv(reports/'v2_vs_v3_comparison.csv',comparison,['metric','v2','v3','difference'])
    immutable={name:hashes(diet/name)==before[name] for name in before}
    if not all(immutable.values()):raise RuntimeError('Protected source files changed')
    readiness=dict(dataset='training_v3',class_count=46,train_images=image_counts['train'],valid_images=image_counts['valid'],test_images=image_counts['test'],total_images=sum(image_counts.values()),total_annotations=sum(counts.values()),broken_images=0,invalid_annotations=0,missing_image_label_pairs=0,invalid_class_ids=0,exact_cross_split_duplicates=0,near_duplicate_cross_split_groups=0,visual_review_blockers=3,visual_issues_resolved=0,classes_with_zero_validation=[names[c] for c in names if counts[(c,'valid')]==0],classes_with_zero_test=[names[c] for c in names if counts[(c,'test')]==0],ready_for_training=False,automated_checks_passed=True,annotations_removed=sum(v2_counts.values())-sum(counts.values()),bounding_boxes_corrected=0,images_excluded=len(excluded),annotation_geometry_modified=0,class_count_changed=False,class_ids_changed=False,split_assignments_changed=False,immutable_sources=immutable,training_performed=False,review_note='Automated checks pass; inspect new before/after visual copies before marking the three approved cases resolved')
    (stage/'final_dataset_readiness.json').write_text(json.dumps(readiness,indent=2))
    (reports/'correction_metadata.json').write_text(json.dumps(dict(input_fingerprint=signature,approved_cases=3,changed_label_files=[list(k) for k in label_differences],excluded_images=[list(k) for k in excluded],source_files_verified={k:len(v) for k,v in before.items()}),indent=2))
    (reports/'protected_source_hashes.json').write_text(json.dumps(before,indent=2,sort_keys=True))
    stage.rename(target)
    return readiness


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(create(BACKEND),indent=2))
