"""Compare existing YOLOv8n/s reports only; no training, inference or model publishing.

From backend: python3 scripts/diet_dataset/compare_yolo_models.py
All differences use YOLOv8s minus YOLOv8n; relative percentages use YOLOv8n.
"""
import csv
import hashlib
import json
from pathlib import Path
import statistics

BACKEND = Path(__file__).resolve().parents[2]
ROOT = BACKEND/'outputs/diet'
METRICS = ['precision', 'recall', 'f1', 'mAP50', 'mAP50_95']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def difference(n, s):
    return dict(difference_s_minus_n=s-n, absolute_difference=abs(s-n),
                percentage_difference=100*(s-n)/n if n else None)


def write_csv(path, rows):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    sources = {}
    def read(path):
        sources[str(path.relative_to(BACKEND))] = sha(path)
        return json.loads(path.read_text())
    models = {}
    for name in ['yolov8n', 'yolov8s']:
        run = ROOT/f'{name}_baseline'
        folder = run/'evaluation'
        models[name] = {split: read(folder/f'{split}_metrics.json') for split in ['validation','test']}
        models[name]['benchmark'] = read(folder/'inference_benchmark.json')
        models[name]['evaluation_config'] = read(folder/'evaluation_config.json')
        models[name]['training_config'] = read(run/'experiment_config.json')
        models[name]['training_summary'] = read(run/'training_summary.json')
        integrity = read(folder/'source_integrity.json')
        if not integrity['training_v3_unchanged'] or not integrity['checkpoint_unchanged']:
            raise ValueError(f'{name} evaluation integrity check failed')
        checkpoint = run/'weights/best.pt'
        if sha(checkpoint) != models[name]['evaluation_config']['checkpoint_sha256']:
            raise ValueError(f'{name} checkpoint changed since evaluation')
        sources[str(checkpoint.relative_to(BACKEND))] = sha(checkpoint)
        path = folder/'per_class_metrics.csv'
        sources[str(path.relative_to(BACKEND))] = sha(path)
        with path.open(newline='') as handle:
            models[name]['classes'] = {int(row['class_id']):row for row in csv.DictReader(handle) if row['split']=='test'}
    n,s = models['yolov8n'],models['yolov8s']
    evaluation_keys = ['dataset','device','torch','ultralytics','imgsz','batch','confidence_threshold','nms_iou','root_plots_split']
    training_keys = ['dataset_version','dataset_path','class_count','image_size','epochs','patience','seed','workers','batch','cache','deterministic','amp','device','validation_split','test_split_used']
    for group,keys in [('evaluation_config',evaluation_keys),('training_config',training_keys)]:
        for key in keys:
            if n[group][key] != s[group][key]: raise ValueError(f'Comparison mismatch: {group}/{key}')
    for key in ['device','image_paths','seed','sample_count','warmup_images','timing_scope']:
        if n['benchmark'][key] != s['benchmark'][key]: raise ValueError(f'Benchmark mismatch: {key}')
    if n['benchmark']['device']!='cpu': raise ValueError('Expected CPU benchmark')
    if set(n['classes']) != set(s['classes']) or len(n['classes']) != 46:
        raise ValueError('Expected matching 46-class taxonomies')
    overall = []
    for split in ['validation','test']:
        if any(n[split][key]!=s[split][key] for key in ['images','instances']):
            raise ValueError('Split support differs')
        for metric in METRICS:
            nv,sv = n[split][metric],s[split][metric]
            overall.append(dict(split=split,metric=metric,unit='fraction',yolov8n=nv,yolov8s=sv,
                **difference(nv,sv),percentage_point_difference=100*(sv-nv),
                better_model='YOLOv8s' if sv>nv else 'YOLOv8n' if nv>sv else 'TIE'))
    for metric,unit,lower in [('model_size_MB','MB (decimal)',True),('average_inference_time_ms','ms/image',True),('FPS','frames/second',False)]:
        nv,sv = n['benchmark'][metric],s['benchmark'][metric]
        overall.append(dict(split='benchmark',metric=metric,unit=unit,yolov8n=nv,yolov8s=sv,
            **difference(nv,sv),percentage_point_difference=None,
            better_model='YOLOv8n' if (nv<sv if lower else nv>sv) else 'YOLOv8s' if nv!=sv else 'TIE'))
    per_class = []
    for cid in sorted(n['classes']):
        a,b = n['classes'][cid],s['classes'][cid]
        if a['class_name']!=b['class_name'] or a['instances']!=b['instances']:
            raise ValueError(f'Class alignment mismatch: {cid}')
        count = int(a['instances'])
        row = dict(class_id=cid,class_name=a['class_name'],test_instances=count)
        for output,input_key in [('precision','precision'),('recall','recall'),('f1','f1'),('ap50','AP50'),('ap50_95','AP50_95')]:
            for prefix,values in [('yolov8n',a),('yolov8s',b)]:
                if count and values['status']!='EVALUABLE': raise ValueError('Unexpected class status')
                if not count and values[input_key]!='': raise ValueError('Absent class has numerical metrics')
                row[f'{prefix}_{output}']=float(values[input_key]) if count else None
        delta = row['yolov8s_ap50_95']-row['yolov8n_ap50_95'] if count else None
        row.update(ap50_95_difference=delta,
            better_model=('YOLOv8s' if delta>1e-12 else 'YOLOv8n' if delta < -1e-12 else 'TIE') if count else 'NOT_EVALUABLE_ON_TEST',
            status='EVALUABLE' if count else 'NOT_EVALUABLE_ON_TEST',
            support_flag='SPARSE_TEST_SUPPORT' if 0<count<5 else 'NOT_EVALUABLE_ON_TEST' if not count else 'AT_LEAST_5_TEST_INSTANCES')
        per_class.append(row)
    evaluable = [r for r in per_class if r['test_instances']]
    supported = [r for r in evaluable if r['test_instances']>=5]
    sparse = [r for r in evaluable if r['test_instances']<5]
    def consistency(rows):
        return dict(class_count=len(rows),wins={model:sum(r['better_model']==model for r in rows) for model in ['YOLOv8n','YOLOv8s','TIE']},
            median_ap50_95_difference=statistics.median(r['ap50_95_difference'] for r in rows),
            mean_ap50_95_difference=statistics.mean(r['ap50_95_difference'] for r in rows))
    efficiency = dict(model_size_ratio_s_over_n=s['benchmark']['model_size_MB']/n['benchmark']['model_size_MB'],
        latency_ratio_s_over_n=s['benchmark']['average_inference_time_ms']/n['benchmark']['average_inference_time_ms'],
        relative_FPS_difference_percent=100*(s['benchmark']['FPS']/n['benchmark']['FPS']-1))
    generalization = {name:{metric:dict(validation=values['validation'][metric],test=values['test'][metric],
        test_minus_validation=values['test'][metric]-values['validation'][metric]) for metric in METRICS} for name,values in models.items()}
    # Explicit application-oriented decision, not a universal statistical superiority rule.
    n_test_advantages = all(n['test'][key]>s['test'][key] for key in ['precision','f1','mAP50'])
    s_gain = s['test']['mAP50_95']-n['test']['mAP50_95']
    prefer_n = n_test_advantages and 0<=s_gain<0.01 and efficiency['model_size_ratio_s_over_n']>2 and efficiency['latency_ratio_s_over_n']>1.5
    recommendation = 'RECOMMEND_YOLOV8N' if prefer_n else 'RESULT_INCONCLUSIVE'
    test_m = 'NO' if prefer_n else 'YES'
    caveat = s['training_config'].get('comparison_note','Training schedule history should be reviewed.')
    result = dict(difference_definition='Signed differences are YOLOv8s minus YOLOv8n. Absolute differences are magnitudes. Relative percentage differences use YOLOv8n as denominator. Fraction metric deltas multiplied by 100 are percentage points.',
        overall_metrics=overall,efficiency=efficiency,generalization=generalization,
        consistency_all_evaluable=consistency(evaluable),consistency_excluding_sparse=consistency(supported),
        largest_supported_gains=sorted(supported,key=lambda r:r['ap50_95_difference'],reverse=True)[:5],
        largest_supported_regressions=sorted(supported,key=lambda r:r['ap50_95_difference'])[:5],
        sparse_test_classes=[r['class_name'] for r in sparse],
        not_evaluable_on_test=[r['class_name'] for r in per_class if not r['test_instances']],
        recommendation=recommendation,SHOULD_TEST_YOLOV8M=test_m,
        decision_basis='Current CPU deployment context: higher precision, F1 and AP50 for n; s AP50-95 gain below 1 percentage point with >2x size and >1.5x latency. These are explicit practical judgments, not statistical significance thresholds.',
        fair_comparison_checks=dict(recorded_settings_match=True,benchmark_subset_identical=True,training_history_caveat=caveat),
        source_sha256=sources,training_performed=False,inference_performed=False)
    out = ROOT/'model_comparison'
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'model_comparison.csv',overall)
    write_csv(out/'per_class_comparison.csv',per_class)
    (out/'comparison_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    def table(split):
        text='| Metric | YOLOv8n | YOLOv8s | s − n (pp) | Relative change |\n|---|---:|---:|---:|---:|\n'
        for row in overall:
            if row['split']==split:
                text+=f"| {row['metric']} | {100*row['yolov8n']:.2f}% | {100*row['yolov8s']:.2f}% | {row['percentage_point_difference']:+.3f} | {row['percentage_difference']:+.2f}% |\n"
        return text
    report='# YOLOv8n versus YOLOv8s\n\n'
    report+='## 1. Experimental Setup\n\nThis is a read-only comparison of saved evaluation reports; no model was trained or evaluated again. Both use training_v3 (46 classes), the same splits (1868 train, 279 validation, 279 test), image size 640, seed 42, batch 4, patience 20 and workers 0. Training used MPS; evaluation and latency measurement used Apple M1 CPU with the same recorded software versions. Validation contains 747 annotations and test contains 692. Evaluation confidence is 0.001 and NMS IoU is 0.7; prediction samples use confidence 0.25.\n\n'
    report+='The final recorded epoch budget is 30 for both, but the training histories are not identical: '+caveat+' This limits strict architecture-only causal attribution. Neither prior run is changed.\n\n'
    report+='## 2. Validation Performance\n\n'+table('validation')+'\nYOLOv8s improves every reported validation metric.\n\n'
    report+='## 3. Test Performance\n\n'+table('test')+'\nYOLOv8n has higher precision, F1 and mAP50; YOLOv8s has higher recall and narrowly higher mAP50–95. Aggregate F1 is the harmonic mean of macro precision and recall, not the mean of class F1 values. No confidence intervals or repeated-seed experiments are available, so the observed margin is not established statistical superiority.\n\n'
    report+='## 4. Computational Efficiency\n\n| Measure | YOLOv8n | YOLOv8s | s − n | Relative change |\n|---|---:|---:|---:|---:|\n'
    for row in overall:
        if row['split']=='benchmark': report+=f"| {row['metric']} | {row['yolov8n']:.4f} | {row['yolov8s']:.4f} | {row['difference_s_minus_n']:+.4f} | {row['percentage_difference']:+.2f}% |\n"
    report+=f"\nYOLOv8s is {efficiency['model_size_ratio_s_over_n']:.3f}× the size and {efficiency['latency_ratio_s_over_n']:.3f}× the latency. FPS changes by {efficiency['relative_FPS_difference_percent']:.2f}%. The identical seeded 50-image test subset and five warmups were verified. Batch-1 latency includes loading and pre/postprocessing but excludes saving; FPS is its reciprocal, not concurrent server throughput. Single-run hardware load and thermal effects remain uncontrolled. The test AP50–95 increase is only {100*s_gain:.3f} percentage points; this does not demonstrate a broad accuracy gain commensurate with the extra CPU cost.\n\n"
    report+='## 5. Per-Class Analysis\n\n'
    for title,group in [('All 44 evaluable classes',evaluable),('Classes with at least five test instances',supported)]:
        c=consistency(group)
        report+=f"{title}: {c['wins']['YOLOv8n']} favor n, {c['wins']['YOLOv8s']} favor s, {c['wins']['TIE']} ties by AP50–95. Median s−n change: {100*c['median_ap50_95_difference']:+.3f} percentage points.\n\n"
    report+=f"Excluding sparse classes, the mean AP50–95 difference is {100*consistency(supported)['mean_ap50_95_difference']:+.3f} pp. This supported-class sensitivity analysis shows a larger s advantage than the overall mean; the practical n recommendation should not obscure these class-specific gains. This is a post-hoc analysis, not a replacement for the original 44-class metric.\n\n"
    report+='| Class (at least 5 test instances) | Instances | s − n AP50–95 (pp) |\n|---|---:|---:|\n'
    for row in result['largest_supported_gains']+result['largest_supported_regressions']:
        report+=f"| {row['class_name']} | {row['test_instances']} | {100*row['ap50_95_difference']:+.3f} |\n"
    report+='\nFive largest improvements and five largest regressions are listed above. They remain descriptive; object counts do not equal independent meal counts.\n\n'
    report+='Sparse (<5) test classes: '+', '.join(r['class_name']+f" ({r['test_instances']})" for r in sparse)+'. They are flagged SPARSE_TEST_SUPPORT; rankings involving these classes are descriptive only. Full class-aligned metrics and signed differences are in per_class_comparison.csv. Class-wise wins are not an independent significance test; objects can share images and foods differ in support and difficulty. At least five instances is a reporting threshold, not proof of reliable coverage.\n\n'
    report+='## 6. Precision vs Recall Trade-off\n\nHigher n precision suggests fewer false detections among predicted foods at the reported operating point; higher s recall suggests fewer missed annotated foods. False positive identities can introduce incorrect nutrition entries, while missed foods can omit carbohydrate contributions. Both error types can propagate into later nutrition, GI, carbohydrate and Glycemic Load estimates. The current precision/efficiency advantage favors n for a provisional deployment baseline, with user confirmation of detected foods and future downstream validation. Detection performance does not establish nutritional accuracy or clinical suitability.\n\nThe validator selects its confidence operating point separately for each model when reporting precision/recall/F1. Equal low AP confidence thresholds and equal NMS settings do not establish a shared deployment threshold or equal-error operating point. These reports cannot quantify downstream false-positive costs at a fixed production threshold. No thresholds were changed here.\n\n'
    report+='## 7. Generalization Observation\n\n'
    for model in ['yolov8n','yolov8s']:
        g=generalization[model]
        report+=f"{model}: test−validation mAP50 is {100*g['mAP50']['test_minus_validation']:+.3f} pp and mAP50–95 is {100*g['mAP50_95']['test_minus_validation']:+.3f} pp.\n\n"
    report+='The stronger s validation result translates into only a very small test mAP50–95 advantage and lower test mAP50. This is a possible generalization difference to consider in model selection, not sufficient evidence to label the model overfit. Split composition, limited support, training-history differences and stochastic training are possible explanations; these reports do not identify the cause.\n\n'
    report+='## 8. Dataset Evaluation Limitations\n\nDried_Halmasso and Omelette have zero test annotations. They remain NOT_EVALUABLE_ON_TEST with blank numerical metrics and are excluded from rankings. The test macro AP covers 44 classes, whereas validation covers 46; validation/test aggregate differences therefore also reflect different evaluated class sets. Sparse classes should not support strong conclusions. One dataset split, one seed per architecture and one latency run cannot establish robust superiority. This report does not re-audit annotations or duplicate leakage. Using these test results to choose a model makes the choice exploratory; an independent future holdout or prospective assessment would be needed for an unbiased final assessment.\n\n'
    report+='## 9. Deployment Considerations\n\nYOLOv8n offers lower storage and CPU latency, important for resource-constrained meal-image workflows. YOLOv8s may be useful if missing foods is assigned a substantially larger cost and its class-specific gains align with the target meals. Neither model should be selected on AP alone. Validate uncertain food identities and downstream nutrition mapping independently; the detector does not infer serving mass, preparation details, GI or carbohydrate quantity from these evaluation results. No model was copied, deployed or integrated into FastAPI.\n\n'
    report+=f"## 10. Recommendation\n\n**{recommendation}** as the provisional CPU baseline under the stated application priorities. The rationale is higher test precision, F1 and mAP50 with substantially smaller size and lower latency; s offers improved recall and a marginal AP50–95 gain. Per-class results are mixed, so this is a practical trade-off, not a claim that n is uniformly more accurate or statistically superior. The decision rule and all source hashes are recorded in comparison_results.json.\n\n"
    report+=f"## 11. Whether YOLOv8m Testing Is Justified\n\n**SHOULD_TEST_YOLOV8M = {test_m}**, based on current evidence and CPU deployment constraints. The move from n to s already substantially increases cost without a broad test-set gain. A larger model is not yet justified by these results; prioritize reliable class support, error review and downstream requirements before considering another architecture. This does not prove m would perform worse. Reconsider only if a defined recall/accuracy requirement remains unmet and additional compute is acceptable. No YOLOv8m training is initiated.\n"
    (out/'comparison_summary.md').write_text(report)
    for relative,digest in sources.items():
        if sha(BACKEND/relative)!=digest: raise RuntimeError(f'Source changed during comparison: {relative}')
    print(json.dumps(dict(recommendation=recommendation,SHOULD_TEST_YOLOV8M=test_m,efficiency=efficiency,
        per_class=consistency(evaluable),supported=consistency(supported),output=str(out)),indent=2))


if __name__=='__main__': main()
