"""Evaluate best.pt without training. Run this script from backend using Python 3."""
import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import time
from train_yolov8n import DATASET, DIET_OUTPUT, RUN, snapshot, select_device, redirect_cache_writer


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def class_rows(metrics, names, counts, split):
    # box.maps must not be used: it fills absent classes with the global mean.
    indices = {int(cid): i for i, cid in enumerate(metrics.box.ap_class_index)}
    rows = []
    for cid, name in names.items():
        count = counts[cid]
        row = dict(split=split, class_id=cid, class_name=name, precision=None, recall=None,
                   f1=None, AP50=None, AP50_95=None, instances=count,
                   status='EVALUABLE' if count else 'NOT_EVALUABLE_ON_'+split.upper())
        if count:
            index = indices.get(cid)
            for key, array in [('precision',metrics.box.p), ('recall',metrics.box.r),
                               ('f1',metrics.box.f1), ('AP50',metrics.box.ap50), ('AP50_95',metrics.box.ap)]:
                row[key] = float(array[index]) if index is not None else 0.0
        rows.append(row)
    return rows


def main(run=RUN, model_label='YOLOv8n'):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device')
    args = parser.parse_args()
    out = run/'evaluation'
    out.mkdir(parents=True, exist_ok=True)
    for variable, path in [('YOLO_CONFIG_DIR',DIET_OUTPUT/'.ultralytics'), ('MPLCONFIGDIR',DIET_OUTPUT/'.matplotlib'), ('TORCH_HOME',DIET_OUTPUT/'.torch')]:
        os.environ.setdefault(variable,str(path))
        path.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK','1')
    import torch
    import ultralytics
    import yaml
    from ultralytics import YOLO
    from ultralytics.data import dataset as yolo_dataset
    from ultralytics.utils import SETTINGS
    SETTINGS.update({k:False for k in ('sync','wandb','comet','clearml','mlflow','neptune','raytune','hub') if k in SETTINGS})
    weights = run/'weights/best.pt'
    before = snapshot(DATASET)
    weight_hash = hashlib.sha256(weights.read_bytes()).hexdigest()
    names = {int(k):v for k,v in yaml.safe_load((DATASET/'data.yaml').read_text())['names'].items()}
    device = args.device or select_device(torch)
    model = YOLO(str(weights))
    if model.names != names or model.task != 'detect':
        raise ValueError('Checkpoint class names must match the dataset')
    dump(out/'evaluation_config.json',dict(checkpoint=str(weights),checkpoint_sha256=weight_hash,
        dataset=str(DATASET),device=device,torch=torch.__version__,ultralytics=ultralytics.__version__,
        imgsz=640,batch=4,confidence_threshold=0.001,nms_iou=0.7,root_plots_split='test',training_performed=False))
    original = yolo_dataset.save_dataset_cache_file
    yolo_dataset.save_dataset_cache_file = redirect_cache_writer(original,out/'dataset_cache')
    rows, aggregates = [], {}
    try:
        for split,folder,key in [('validation','valid','val'),('test','test','test')]:
            counts = dict.fromkeys(names,0)
            for label in sorted((DATASET/folder/'labels').glob('*.txt')):
                for line in label.read_text().splitlines():
                    if line.strip(): counts[int(line.split()[0])] += 1
            result = model.val(data=str(DATASET/'data.yaml'),split=key,imgsz=640,batch=4,
                device=device,workers=0,cache=False,plots=True,project=str(out),name=split,
                exist_ok=True,conf=0.001,iou=0.7,half=False,augment=False,seed=42,verbose=True)
            split_rows = class_rows(result,names,counts,split)
            rows.extend(split_rows)
            p,r,ap50,ap = map(float,result.box.mean_results())
            aggregates[split] = dict(split=split,precision=p,recall=r,f1=2*p*r/(p+r) if p+r else 0,
                mAP50=ap50,mAP50_95=ap,instances=sum(counts.values()),
                images=len(list((DATASET/folder/'images').iterdir())),
                not_evaluable=[row['class_name'] for row in split_rows if not row['instances']],
                speed_ms_per_image={k:float(v) for k,v in result.speed.items()})
            dump(out/f'{split}_metrics.json',aggregates[split])
        with (out/'per_class_metrics.csv').open('w',newline='') as handle:
            writer = csv.DictWriter(handle,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        for name in ['confusion_matrix.png','confusion_matrix_normalized.png','PR_curve.png','F1_curve.png']:
            source = next((out/'test'/prefix for prefix in [name,'Box'+name,'Box_'+name] if (out/'test'/prefix).is_file()),None)
            if source is None: raise FileNotFoundError(name)
            shutil.copy2(source,out/name)
        images = sorted(p for p in (DATASET/'test/images').iterdir() if p.is_file())
        random.Random(42).shuffle(images)
        images = images[:50]
        def synchronize():
            if device.startswith('cuda'): torch.cuda.synchronize()
            elif device == 'mps': torch.mps.synchronize()
        options = dict(imgsz=640,device=device,conf=0.25,iou=0.7,verbose=False,save=False,half=False)
        for image in images[:5]: model.predict(str(image),**options)
        timings,forwards,predictions = [],[],[]
        for image in images:
            synchronize()
            started = time.perf_counter()
            prediction = model.predict(str(image),**options)[0]
            synchronize()
            timings.append((time.perf_counter()-started)*1000)
            forwards.append(float(prediction.speed['inference']))
            predictions.append(prediction)
        average = sum(timings)/len(timings)
        benchmark = dict(device=device,model_size_MB=weights.stat().st_size/1_000_000,
            sample_count=len(images),warmup_images=5,seed=42,average_inference_time_ms=average,
            FPS=1000/average,average_model_forward_ms=sum(forwards)/len(forwards),
            timing_scope='Synchronized batch=1 wall time including image loading and pre/postprocessing, excluding saving',
            image_paths=[str(p.relative_to(DATASET)) for p in images])
        dump(out/'inference_benchmark.json',benchmark)
        samples = out/'prediction_samples'
        samples.mkdir(exist_ok=True)
        for i,prediction in enumerate(predictions[:20]):
            prediction.save(filename=str(samples/f'{i+1:02d}_{images[i].name}'),labels=True,conf=True)
        ranked = sorted([row for row in rows if row['split']=='test' and row['instances']],key=lambda row:(-row['AP50_95'],row['class_name']))
        rankings = dict(ranking_metric='test AP50_95',strongest=ranked[:5],weakest=list(reversed(ranked[-5:])))
        dump(out/'class_rankings.json',rankings)
        report = f'# {model_label} evaluation\n\nNo training performed. Root plots describe test; split-specific plots are retained in validation/ and test/.\n\n'
        report += '| Split | Precision | Recall | F1 | mAP50 | mAP50-95 |\n|---|---:|---:|---:|---:|---:|\n'
        for split,values in aggregates.items():
            report += '| '+split+' | '+' | '.join(f'{values[k]:.6f}' for k in ['precision','recall','f1','mAP50','mAP50_95'])+' |\n'
        report += '\nAggregate F1 is the harmonic mean of macro precision and recall. Per-class F1 uses the validator operating point. AP confidence threshold: 0.001; NMS IoU: 0.7.\n\n'
        report += 'NOT_EVALUABLE_ON_TEST: '+', '.join(aggregates['test']['not_evaluable'])+'. No ground truth means null/blank metrics, excluded from rankings. Sparse classes have uncertain estimates; consult instance counts.\n\n'
        report += 'Benchmark (decimal MB; milliseconds/image; FPS reciprocal of synchronized wall latency):\n\n```json\n'+json.dumps({k:v for k,v in benchmark.items() if k!='image_paths'},indent=2)+'\n```\n\n'
        for title,group in [('Strongest',rankings['strongest']),('Weakest evaluable',rankings['weakest'])]:
            report += f'## {title} five by test AP50-95\n\n'+'\n'.join(f"- {row['class_name']}: {row['AP50_95']:.4f}, {row['instances']} instances" for row in group)+'\n\n'
        report += 'Twenty test prediction images retain source pixels and add predicted boxes, food names and confidence (threshold 0.25) in prediction_samples/. Original files are unchanged.\n'
        (out/'evaluation_summary.md').write_text(report)
    finally:
        yolo_dataset.save_dataset_cache_file = original
        integrity = dict(training_v3_unchanged=snapshot(DATASET)==before,
            checkpoint_unchanged=hashlib.sha256(weights.read_bytes()).hexdigest()==weight_hash,training_performed=False)
        dump(out/'source_integrity.json',integrity)
        if not integrity['training_v3_unchanged'] or not integrity['checkpoint_unchanged']:
            raise RuntimeError('Source integrity check failed')
    print(json.dumps(dict(metrics=aggregates,benchmark=benchmark,rankings=rankings),indent=2),flush=True)


if __name__ == '__main__': main()
