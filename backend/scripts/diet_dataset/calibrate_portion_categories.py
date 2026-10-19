"""Calibrate visual categories from TRAIN box distributions only; no model runtime.

Run from backend: .venv/bin/python scripts/diet_dataset/calibrate_portion_categories.py
Percentiles use linear interpolation at (n-1)*p (p=.33/.67). Labels are never written.
"""
from pathlib import Path
import argparse
import copy
import csv
import hashlib
import json
import math
import yaml

BACKEND=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, probability):
    ordered=sorted(values)
    if not ordered:raise ValueError('Cannot calculate an empty percentile')
    rank=(len(ordered)-1)*probability
    lo,hi=math.floor(rank),math.ceil(rank)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(rank-lo)


def calibrate(dataset, reference, minimum=10):
    """Pure read/derive step. Deliberately never discovers valid/ or test/ paths."""
    if minimum<10:raise ValueError('Minimum support must be at least 10 annotations')
    data_path=dataset/'data.yaml'
    mapping=yaml.safe_load(data_path.read_text())
    names={int(k):v for k,v in mapping['names'].items()}
    if mapping['nc']!=46 or set(names)!=set(range(46)):raise ValueError('Expected V3 IDs 0–45')
    config=copy.deepcopy(reference)
    if set(config['foods'])!=set(names.values()):raise ValueError('Reference names differ from V3 taxonomy')
    label_dir=dataset/'train/labels'
    paths=sorted(label_dir.glob('*.txt'))
    if not paths:raise ValueError('No training labels found')
    fingerprints={str(p.relative_to(dataset)):sha(p) for p in [data_path,*paths]}
    areas={cid:[] for cid in names}
    for path in paths:
        for line_no,line in enumerate(path.read_text().splitlines(),1):
            if not line.strip():continue
            try:
                parts=line.split()
                if len(parts)!=5:raise ValueError('Expected a detection box')
                raw_id,cx,cy,w,h=map(float,parts)
                if not all(math.isfinite(v) for v in [raw_id,cx,cy,w,h]):raise ValueError('Non-finite row')
                cid=int(raw_id)
                if raw_id!=cid or cid not in names or not (0<w<=1 and 0<h<=1):raise ValueError('Invalid ID/size')
                if not (0<=cx<=1 and 0<=cy<=1 and cx-w/2>=-1e-6 and cx+w/2<=1+1e-6 and cy-h/2>=-1e-6 and cy+h/2<=1+1e-6):raise ValueError('Box exceeds normalized image')
                areas[cid].append(w*h)
            except ValueError as exc:raise ValueError(f'Invalid train annotation {path.name}:{line_no}') from exc
    rows=[]
    for cid,name in sorted(names.items()):
        entry=config['foods'][name]
        method=entry['method'];values=areas[cid];q33=q67=None
        entry.update(portion_rules=None,serving_weights=None,validated=False,validated_physical_portion=False,
                     training_samples=len(values),calibration_type='visual_research_baseline')
        if method=='area_based':
            status='insufficient_training_support'
            if len(values)>=minimum:
                q33,q67=percentile(values,.33),percentile(values,.67)
                status='calibrated' if 0<q33<q67<=1 else 'degenerate_training_distribution'
                if status=='calibrated':
                    entry['portion_rules']={'small_max_relative_area':q33,'medium_max_relative_area':q67}
            entry.update(calibration_method='training_v3_train_quantiles_33_67',threshold_source='research_baseline_provisional')
        elif method=='count_based':
            status='provisional_count_rule'
            entry.update(portion_rules={'small_max_count':1,'medium_max_count':2},
                         calibration_method='research_baseline_count_rule',threshold_source='research_baseline_provisional')
        elif method=='reference_based':
            status='reference_required'
            entry.update(calibration_method='none_reference_required',threshold_source='not_established')
        else:raise ValueError('Unsupported portion method')
        entry['calibration_status']=status
        rows.append(dict(class_id=cid,food_name=name,method=method,training_samples=len(values),
                         q33_relative_area=q33,q67_relative_area=q67,calibration_status=status))
    config['research_baseline_thresholds']={
        'status':'train_quantiles_and_provisional_count_rules','validated':False,
        'calibration_type':'visual_research_baseline','minimum_training_annotations':minimum,
        'area_calibration_split':'train','area_percentiles':[33,67],
        'quantile_interpolation':'linear at (n-1)*p',
        'description':'Research-baseline visual portion categories, not validated physical serving weights. Count categories are an explicit provisional policy, not fitted weight estimates.'}
    summary=dict(dataset_version='training_v3',class_count=46,calibration_split='train',
        validation_used=False,test_used=False,minimum_training_annotations=minimum,
        normalized_edge_serialization_tolerance=1e-6,train_label_files=len(paths),train_annotations=sum(map(len,areas.values())),
        area_classes_calibrated=sum(r['method']=='area_based' and r['calibration_status']=='calibrated' for r in rows),
        insufficient_support=[r['food_name'] for r in rows if r['calibration_status']=='insufficient_training_support'],
        degenerate_distributions=[r['food_name'] for r in rows if r['calibration_status']=='degenerate_training_distribution'],
        count_based_foods=[r['food_name'] for r in rows if r['method']=='count_based'],
        reference_based_foods=[r['food_name'] for r in rows if r['method']=='reference_based'],
        dataset_inputs_sha256=fingerprints,validated_physical_portion=False,estimated_grams=False,
        training_performed=False,evaluation_performed=False)
    if any(sha(dataset/name)!=digest for name,digest in fingerprints.items()):raise RuntimeError('Input changed during calibration')
    summary['source_annotations_unchanged']=True
    return config,rows,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minimum-support',type=int,default=10)
    args=parser.parse_args()
    dataset=BACKEND/'datasets/diet/training_v3'
    path=BACKEND/'config/portion_reference.json'
    config,rows,summary=calibrate(dataset,json.loads(path.read_text()),args.minimum_support)
    out=BACKEND/'outputs/diet/portion_calibration';out.mkdir(parents=True,exist_ok=True)
    report='# Visual Portion Calibration\n\nResearch-baseline visual portion categories, not validated physical serving weights.\n\n'
    report+=f"Train only: {summary['train_label_files']} label files, {summary['train_annotations']} annotations. {summary['area_classes_calibrated']} area classes calibrated. Minimum support: {args.minimum_support}. Validation/test labels and images were not accessed.\n\n"
    report+='Each normalized YOLO box contributes width × height to its own class distribution. Q33 and Q67 use linear interpolation at (n−1)p; Small ≤ Q33, Medium ≤ Q67, Large > Q67. Insufficient support or equal quantiles yield Unknown, without fabricated thresholds.\n\n'
    report+='Count policy (not a fitted distribution): 1 → Small, 2 → Medium, 3+ → Large. Overlapping same-food detections withhold counts. Reference foods remain Unknown. No images, detector weights or dataset labels are modified.\n\n'
    report+='Insufficient support: '+(', '.join(summary['insufficient_support']) or 'None')+'.\n\nDegenerate distributions: '+(', '.join(summary['degenerate_distributions']) or 'None')+'.\n\n'
    report+='At runtime, grouped same-food areas use a rectangle union. Calibration samples are individual training boxes, so a grouped multi-box category is an extrapolation beyond that sampling unit. Background, framing, angle, depth and density affect the proxy; detector boxes may differ from annotation distributions. Quantile bins express relative image size, not clinical or nutritional portion standards. Measured food-specific serving data and independent validation are needed for physical serving interpretation.\n'
    with (out/'portion_thresholds.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    path.write_text(json.dumps(config,indent=2,allow_nan=False)+'\n')
    summary['portion_reference_sha256']=sha(path)
    (out/'portion_calibration_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'portion_calibration_report.md').write_text(report)
    print(json.dumps({k:v for k,v in summary.items() if k!='dataset_inputs_sha256'},indent=2))


if __name__=='__main__':main()
