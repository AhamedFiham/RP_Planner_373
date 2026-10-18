"""Classification splits, duplicate detection, provenance groups, and balancing."""
import random
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import re
from .validation import inspect_image
from .validation import parse_row
import math


# Organize classification

def assign_splits(records: list[dict], seed: int = 42) -> None:
    groups = {}
    for record in records:
        if record['task']=='classification' and not record.get('preserve_split'): groups.setdefault(record['canonical'],[]).append(record)
    for name, group in sorted(groups.items()):
        group.sort(key=lambda r:str(r['path']))
        random.Random(f'{seed}:{name}').shuffle(group)
        n = len(group)
        train, valid = int(n*.7), int(n*.2)
        if n>=3: train, valid = max(1,min(train,n-2)),max(1,valid)
        for i, record in enumerate(group): record['split'] = 'train' if i<train else 'valid' if i<train+valid else 'test'


# Detect duplicates

def deduplicate(records: list[dict]) -> tuple[list[dict],list[dict],list[dict]]:
    duplicates, leakage, kept = [], [], []
    seen = {}
    priority = {'test':0,'valid':1,'train':2,'unsplit':3}
    # Retain evaluation images preferentially; deterministic tie-breaking.
    for row in sorted(records,key=lambda r:(priority[r['split']],r['dataset'],str(r['path']))):
        old = seen.get(row['pixel_hash'])
        if old:
            kind = 'sha256' if row['sha256']==old['sha256'] else 'decoded_pixels'
            duplicates.append(dict(original_path=str(row['path']),duplicate_of=str(old['path']),hash=row['sha256'],dataset=row['dataset'],action='exclude_exact_duplicate',match_type=kind))
            if row['split']!=old['split']:
                leakage.append(dict(original_path=str(row['path']),duplicate_of=str(old['path']),split=row['split'],retained_split=old['split'],reason=kind,action='excluded'))
        else:
            seen[row['pixel_hash']] = row
            kept.append(row)
    assign_splits(kept)
    final = []
    for row in sorted(kept,key=lambda r:(priority[r['split']],r['dataset'],str(r['path']))):
        near = None
        for old in final:
            # Hashes propose candidates, never assert that food labels are identical.
            if abs(row['width']/row['height']-old['width']/old['height'])>.1: continue
            if (row['dhash'] ^ old['dhash']).bit_count()<=2:
                duplicates.append(dict(original_path=str(row['path']),duplicate_of=str(old['path']),hash=f'{row["dhash"]:016x}',dataset=row['dataset'],action='quarantine_near_duplicate' if row['split']!=old['split'] else 'review_near_duplicate_same_split',match_type='dhash_distance_le_2'))
                if row['split']!=old['split']:
                    near=old
                    break
        if near:
            leakage.append(dict(original_path=str(row['path']),duplicate_of=str(near['path']),split=row['split'],retained_split=near['split'],reason='perceptual_candidate',action='quarantined_for_manual_review'))
        else: final.append(row)
    return final,duplicates,leakage


# Group related images

class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str,str] = {}
        self.reasons: dict[str,set[str]] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item]=item;self.reasons[item]=set()
        if self.parent[item]!=item: self.parent[item]=self.find(self.parent[item])
        return self.parent[item]

    def union(self, first: str, second: str, reason: str) -> None:
        a,b=self.find(first),self.find(second)
        if a!=b:
            a,b=sorted((a,b));self.parent[b]=a
            self.reasons[a].update(self.reasons[b])
        self.reasons[a].add(reason)

def filename_family(filename: str) -> str:
    """Remove Roboflow export hashes and encoded extensions, retaining photo IDs."""
    stem=Path(filename).stem
    stem=re.split(r'\.rf\.',stem,flags=re.I)[0]
    stem=re.sub(r'[_\-.](jpg|jpeg|png|webp)$','',stem,flags=re.I)
    return re.sub(r'[^a-z0-9]+','',stem.casefold())

def read_csv(path: Path) -> list[dict]:
    with path.open(newline='') as f:return list(csv.DictReader(f))

def group_images(backend: Path) -> tuple[list[dict],list[dict],list[dict]]:
    diet=backend/'datasets/diet';v1=diet/'training_v1';normalized=diet/'normalized'
    selected=json.loads((v1/'selected_classes.json').read_text())['classes']
    manifest=read_csv(v1/'reports/image_manifest.csv')
    original={r['normalized_path']:r for r in read_csv(normalized/'reports/image_manifest.csv')}
    uf=UnionFind();families={}
    # Include original, even excluded, filenames so family/duplicate chains are transitive.
    raw_files=json.loads((normalized/'reports/raw_integrity_manifest.json').read_text())
    for relative in sorted(raw_files):
        p=Path(relative)
        if p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:continue
        parts=p.relative_to('datasets/diet/raw').parts
        node=str(p);uf.find(node)
        family=(parts[0],filename_family(p.name))
        if family in families:uf.union(node,families[family],'same_roboflow_original' if '.rf.' in p.name else 'filename_family')
        else:families[family]=node
    def node_from_report(value: str) -> str:
        # Old reports may contain a different workstation prefix.
        marker='datasets/diet/raw/'
        if marker not in value:raise ValueError('Duplicate provenance does not refer to raw data')
        return marker+value.split(marker,1)[1]
    duplicates=normalized/'reports/duplicates.csv'
    if duplicates.exists():
        for row in read_csv(duplicates):
            reason='exact_duplicate' if row['match_type'] in {'sha256','decoded_pixels'} else 'near_duplicate'
            uf.union(node_from_report(row['original_path']),node_from_report(row['duplicate_of']),reason)
    records=[];sha_seen={};pixel_seen={}
    for row in sorted(manifest,key=lambda r:r['image']):
        image=v1/row['split']/'images'/row['image']
        label=v1/row['split']/'labels'/(image.stem+'.txt')
        info=inspect_image(image)
        if info['sha256']!=row['sha256']:raise ValueError('V1 image no longer matches its manifest')
        source=str(Path(row['source']).relative_to('datasets/diet/normalized'))
        provenance=original[source];node=provenance['original_path'];uf.find(node)
        for key,lookup in [('sha256',sha_seen),('pixel_hash',pixel_seen)]:
            if info[key] in lookup:uf.union(node,lookup[info[key]],'exact_duplicate')
            else:lookup[info[key]]=node
        counts=[0]*len(selected)
        for line in label.read_text().splitlines():
            if line.strip():cid,_,mode=parse_row(line,set(range(len(selected))));counts[cid]+=1
        records.append(dict(image=image,label=label,node=node,source_dataset=row['source_dataset'],old_split=row['split'],counts=counts,**info))
    for i,row in enumerate(records):
        for old in records[:i]:
            if abs(row['width']/row['height']-old['width']/old['height'])<=.1 and (row['dhash']^old['dhash']).bit_count()<=2:
                uf.union(row['node'],old['node'],'near_duplicate')
    grouped=defaultdict(list)
    for record in records:grouped[uf.find(record['node'])].append(record)
    groups=[]
    for root,items in sorted(grouped.items()):
        gid='group_'+hashlib.sha256(root.encode()).hexdigest()[:16]
        counts=[sum(row['counts'][i] for row in items) for i in range(len(selected))]
        reason=';'.join(sorted(uf.reasons[uf.find(root)])) or 'independent'
        for row in items:row.update(group_id=gid,group_reason=reason)
        groups.append(dict(id=gid,records=items,counts=counts,size=len(items)))
    return groups,records,selected


# Balance group splits

SPLITS=('train','valid','test')

def preferred_target(total: int) -> int:
    return 15 if total>=200 else 10 if total>=100 else 5

def balance(groups: list[dict], seed: int = 42, restarts: int = 10) -> tuple[dict,dict]:
    classes=len(groups[0]['counts'])
    totals=[sum(g['counts'][c] for g in groups) for c in range(classes)]
    floors=[max(15,t//2+1) for t in totals]
    if any(t<f for t,f in zip(totals,floors)):raise ValueError('Training floor is infeasible even before splitting')
    sparse=[[(c,v) for c,v in enumerate(g['counts']) if v] for g in groups]
    sizes=[g['size'] for g in groups];n=sum(sizes)
    def class_cost(c: int, train: int, valid: int, test: int) -> float:
        if train<floors[c]:return float('inf')
        p=preferred_target(totals[c])
        return sum(600*(max(0,3-v)/3)**2+60*(max(0,p-v)/p)**2 for v in (valid,test))
    def ratio_cost(counts: list[int]) -> float:
        return 5000*sum((counts[i]/n-target)**2 for i,target in enumerate((.77,.115,.115)))
    best=None
    for restart in range(restarts):
        rng=random.Random(seed+restart)
        assignment=[0]*len(groups);counts=[totals.copy(),[0]*classes,[0]*classes];images=[n,0,0]
        cost=sum(class_cost(c,counts[0][c],0,0) for c in range(classes))+ratio_cost(images)
        def change(changes: list[tuple[int,int]]) -> tuple[float,dict,list[int]]:
            deltas={};image_delta=[0,0,0]
            for index,new in changes:
                old=assignment[index]
                if old==new:continue
                image_delta[old]-=sizes[index];image_delta[new]+=sizes[index]
                for c,value in sparse[index]:
                    d=deltas.setdefault(c,[0,0,0]);d[old]-=value;d[new]+=value
            delta=ratio_cost([images[s]+image_delta[s] for s in range(3)])-ratio_cost(images)
            for c,d in deltas.items():
                before=[counts[s][c] for s in range(3)];after=[before[s]+d[s] for s in range(3)]
                delta+=class_cost(c,*after)-class_cost(c,*before)
            return delta,deltas,image_delta
        def commit(changes: list[tuple[int,int]],proposal: tuple) -> None:
            nonlocal cost
            delta,deltas,image_delta=proposal
            for c,d in deltas.items():
                for s in range(3):counts[s][c]+=d[s]
            for s in range(3):images[s]+=image_delta[s]
            for index,new in changes:assignment[index]=new
            cost+=delta
        for sweep in range(12):
            improved=False;order=list(range(len(groups)));rng.shuffle(order)
            for index in order:
                destinations=list(range(3));rng.shuffle(destinations)
                choices=[]
                for new in destinations:
                    if new!=assignment[index]:choices.append((change([(index,new)]),new))
                proposal,new=min(choices,key=lambda item:item[0][0])
                if proposal[0]<-1e-9:commit([(index,new)],proposal);improved=True
            # Swaps permit escaping constraints that block one-group moves.
            for _ in range(2500):
                a,b=rng.sample(range(len(groups)),2)
                if assignment[a]==assignment[b]:continue
                changes=[(a,assignment[b]),(b,assignment[a])];proposal=change(changes)
                if proposal[0]<-1e-9:commit(changes,proposal);improved=True
            if not improved:break
        actual=sum(class_cost(c,counts[0][c],counts[1][c],counts[2][c]) for c in range(classes))+ratio_cost(images)
        if best is None or actual<best[0]-1e-9:best=(actual,assignment.copy(),[x.copy() for x in counts],images.copy())
    _,assignment,counts,images=best
    return {g['id']:SPLITS[assignment[i]] for i,g in enumerate(groups)},dict(seed=seed,restarts=restarts,objective=best[0],images=dict(zip(SPLITS,images)),counts=counts,totals=totals,minimum_training=floors,optimizer='Seeded multilabel coordinate descent with group swaps; heuristic, not a proof of optimality')
