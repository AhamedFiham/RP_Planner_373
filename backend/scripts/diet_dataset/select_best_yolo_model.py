"""Document a final selection using saved reports only; no ML runtime is imported.

From backend: python3 scripts/diet_dataset/select_best_yolo_model.py
Refuses to publish a selection if source reports disagree or the evidence no
longer supports the recorded application-specific recommendation.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
DIET = BACKEND/'outputs/diet'
COMPARISON = DIET/'model_comparison'
METRICS = ['precision','recall','f1','mAP50','mAP50_95']
# These are rounded reference observations supplied in the selection request,
# not replacement metrics. Output numbers always come from verified reports.
RECORDED = {
    'yolov8n': [0.787244,0.634311,0.702551,0.712754,0.561226],
    'yolov8s': [0.678450,0.687337,0.682865,0.698531,0.563352],
}


def require(condition, message):
    if not condition: raise ValueError('Selection verification failed: '+message)


def close(a,b,tolerance=1e-12):
    return math.isfinite(float(a)) and math.isfinite(float(b)) and math.isclose(float(a),float(b),rel_tol=0,abs_tol=tolerance)


def verify_and_select():
    """Read reports and return selection evidence without writing any outputs."""
    source_hashes = {}
    def read(path, csv_file=False):
        source_hashes[str(path.relative_to(BACKEND))] = hashlib.sha256(path.read_bytes()).hexdigest()
        if csv_file:
            with path.open(newline='') as handle: return list(csv.DictReader(handle))
        return json.loads(path.read_text())
    comparison = read(COMPARISON/'comparison_results.json')
    overall_csv = read(COMPARISON/'model_comparison.csv',True)
    classes = read(COMPARISON/'per_class_comparison.csv',True)
    overall = {(r['split'],r['metric']):r for r in comparison['overall_metrics']}
    require(len(overall)==len(overall_csv)==13,'expected 13 overall comparisons')
    for row in overall_csv:
        other = overall[(row['split'],row['metric'])]
        for key in ['yolov8n','yolov8s','difference_s_minus_n','absolute_difference','percentage_difference']:
            require(close(row[key],other[key]),f'comparison CSV/JSON disagree: {key}')
    models = {}
    for name in RECORDED:
        folder = DIET/f'{name}_baseline/evaluation'
        model = {split:read(folder/f'{split}_metrics.json') for split in ['validation','test']}
        model['benchmark'] = read(folder/'inference_benchmark.json')
        model['config'] = read(folder/'evaluation_config.json')
        model['per_class'] = {int(r['class_id']):r for r in read(folder/'per_class_metrics.csv',True) if r['split']=='test'}
        model['integrity'] = read(folder/'source_integrity.json')
        require(model['integrity']['training_v3_unchanged'] and model['integrity']['checkpoint_unchanged'],f'{name} evaluation integrity')
        for metric,expected in zip(METRICS,RECORDED[name]):
            require(close(model['test'][metric],expected,5e-7),f'{name} recorded test {metric}')
        for split in ['validation','test']:
            for metric in METRICS:
                row = overall[(split,metric)]
                require(close(model[split][metric],row[name]),f'{name} {split} {metric} differs from comparison')
        for metric in ['model_size_MB','average_inference_time_ms','FPS']:
            require(close(model['benchmark'][metric],overall[('benchmark',metric)][name]),f'{name} benchmark {metric}')
        require(close(model['benchmark']['FPS'],1000/model['benchmark']['average_inference_time_ms']),f'{name} reciprocal FPS')
        require(len(model['per_class'])==46,f'{name} class count')
        require(Path(model['config']['dataset']).name=='training_v3',f'{name} dataset version')
        models[name] = model
    # Verify the reports consumed by the comparison still have their original hashes.
    # Checkpoints are never opened; their provenance is the saved evaluation config.
    for relative,digest in comparison['source_sha256'].items():
        if relative in source_hashes:
            require(source_hashes[relative]==digest,f'comparison input changed: {relative}')
    n,s = models['yolov8n'],models['yolov8s']
    for key in ['dataset','device','torch','ultralytics','imgsz','batch','confidence_threshold','nms_iou']:
        require(n['config'][key]==s['config'][key],f'evaluation setting {key}')
    for key in ['image_paths','device','sample_count','seed','warmup_images','timing_scope']:
        require(n['benchmark'][key]==s['benchmark'][key],f'benchmark setting {key}')
    expected_efficiency = {'yolov8n':(6.52977,59.2000,16.8919),'yolov8s':(22.55281,121.4420,8.23438)}
    for name,expected in expected_efficiency.items():
        for key,value,tolerance in zip(['model_size_MB','average_inference_time_ms','FPS'],expected,[5e-8,5e-5,5e-5]):
            require(close(models[name]['benchmark'][key],value,tolerance),f'{name} recorded efficiency {key}')
    require(len(classes)==46 and len({int(r['class_id']) for r in classes})==46,'unique comparison classes')
    absent,sparse,wins = [],[],{'YOLOv8n':0,'YOLOv8s':0,'TIE':0}
    for row in classes:
        cid = int(row['class_id'])
        count = int(row['test_instances'])
        for model in models:
            original = models[model]['per_class'][cid]
            require(row['class_name']==original['class_name'] and count==int(original['instances']),'class identity/support')
            for output,key in [('precision','precision'),('recall','recall'),('f1','f1'),('ap50','AP50'),('ap50_95','AP50_95')]:
                value = row[f'{model}_{output}']
                require(close(value,original[key]) if count else value==original[key]=='','per-class metrics disagree')
        if not count:
            require(row['status']==row['better_model']=='NOT_EVALUABLE_ON_TEST' and row['ap50_95_difference']=='','zero-instance ranking')
            absent.append(row['class_name'])
            continue
        delta = float(row['yolov8s_ap50_95'])-float(row['yolov8n_ap50_95'])
        require(close(delta,row['ap50_95_difference']),'per-class difference')
        winner = 'YOLOv8s' if delta>1e-12 else 'YOLOv8n' if delta < -1e-12 else 'TIE'
        require(row['better_model']==winner,'per-class winner')
        wins[winner]+=1
        if count<5:
            require(row['support_flag']=='SPARSE_TEST_SUPPORT','sparse support flag')
            sparse.append(row['class_name'])
    require(set(absent)=={'Dried_Halmasso','Omelette'},'zero-test class list')
    require(wins==comparison['consistency_all_evaluable']['wins'],'per-class consistency totals')
    for name,model in models.items():
        for metric in METRICS:
            saved = comparison['generalization'][name][metric]
            require(close(saved['validation'],model['validation'][metric]) and close(saved['test'],model['test'][metric]),'generalization source values')
            require(close(saved['test_minus_validation'],model['test'][metric]-model['validation'][metric]),'generalization delta')
    size_ratio = s['benchmark']['model_size_MB']/n['benchmark']['model_size_MB']
    latency_ratio = s['benchmark']['average_inference_time_ms']/n['benchmark']['average_inference_time_ms']
    gain = s['test']['mAP50_95']-n['test']['mAP50_95']
    require(comparison['recommendation']=='RECOMMEND_YOLOV8N','source recommendation is not n')
    require(comparison['SHOULD_TEST_YOLOV8M']=='NO','source YOLOv8m conclusion changed')
    require(all(n['test'][k]>s['test'][k] for k in ['precision','f1','mAP50']),'n precision/F1/AP50 advantage')
    require(s['test']['recall']>n['test']['recall'] and 0<=gain<.01,'recorded recall/AP trade-off')
    require(size_ratio>2 and latency_ratio>1.5,'recorded efficiency advantage')
    checkpoint = 'backend/outputs/diet/yolov8n_baseline/weights/best.pt'
    require(Path(n['config']['checkpoint']).resolve()==(BACKEND/'outputs/diet/yolov8n_baseline/weights/best.pt').resolve(),'source checkpoint provenance')
    require(n['benchmark']['device']=='cpu','CPU deployment evidence')
    require(not any((DIET/'yolov8m_baseline'/name).exists() for name in ['training_summary.json','results.csv','weights/best.pt']),'unexpected YOLOv8m training artifacts; review before stating untested')
    reasons = [
        'Verified saved comparison recommendation and original evaluation metrics agree.',
        'Higher test precision, F1 and mAP50 favor food identity reliability for the stated downstream workflow.',
        f'YOLOv8s is {size_ratio:.3f} times the size and {latency_ratio:.3f} times the CPU latency, for only {gain*100:.3f} percentage points more overall test mAP50-95.',
        'Smaller size and lower CPU latency support practical future FastAPI deployment; no FastAPI throughput or concurrency test was performed.',
        'The validation advantage of YOLOv8s did not translate into a broad overall test advantage; generalization behavior is considered without diagnosing overfitting.',
    ]
    tradeoffs = [
        'YOLOv8s has higher test recall and slightly higher overall test mAP50-95; YOLOv8n may miss more annotated foods at the reported operating point.',
        f"Per-class AP50-95 favors YOLOv8s for {wins['YOLOv8s']} and YOLOv8n for {wins['YOLOv8n']} of 44 evaluable classes; YOLOv8n is not uniformly superior.",
        'YOLOv8s also leads validation metrics and has meaningful gains on some supported classes; selection reflects precision and CPU deployment priorities.',
    ]
    limitations = [
        'Dried_Halmasso has zero test annotations: NOT_EVALUABLE_ON_TEST.',
        'Omelette has zero test annotations: NOT_EVALUABLE_ON_TEST.',
        'Sparse test classes have uncertain per-class estimates: '+', '.join(sparse)+'.',
        'Only one seed per architecture and no confidence intervals; statistical superiority has not been demonstrated.',
        comparison['fair_comparison_checks']['training_history_caveat'],
        'Detector performance does not establish nutrition or clinical accuracy; portion mass and carbohydrate/GI mappings require separate validation.',
        'Validation evaluates 46 classes and test evaluates 44; aggregate generalization gaps also reflect class-support differences.',
        'Precision/recall/F1 operating points were chosen separately by the validator; these are not calibrated fixed production-threshold comparisons.',
        'Single CPU latency run per model, with uncontrolled thermal/load effects; reciprocal FPS is not measured FastAPI server throughput.',
        'Selection uses the observed test results and is therefore post-hoc; an independent future assessment is needed for an unbiased final performance estimate.',
    ]
    selection = dict(selected_model='YOLOv8n',selection_status='FINAL_SELECTED_FROM_VERIFIED_REPORTS',
        source_checkpoint=checkpoint,dataset_version='training_v3',class_count=46,
        test_metrics={key:n['test'][key] for key in METRICS},
        efficiency=dict(model_size_MB=n['benchmark']['model_size_MB'],average_inference_ms=n['benchmark']['average_inference_time_ms'],FPS=n['benchmark']['FPS'],device='cpu'),
        selection_reasons=reasons,tradeoffs=tradeoffs,known_limitations=limitations,
        yolov8m_tested=False,yolov8m_reason_not_tested='The verified comparison concluded SHOULD_TEST_YOLOV8M = NO. YOLOv8s already substantially increased CPU cost without a broad overall test gain; current evidence does not justify testing a larger model.',
        selection_scope='Final documented choice among the two completed candidates for this research project; deployment and downstream clinical/nutrition suitability remain unvalidated.',
        verification=dict(recorded_metrics_confirmed=True,comparison_csv_json_consistent=True,per_class_metrics_confirmed=True,
            zero_test_classes=absent,sparse_test_classes=sparse,per_class_wins=wins,
            checkpoint_sha256_from_evaluation=n['config']['checkpoint_sha256'],checkpoint_read_or_copied=False,
            training_performed=False,inference_performed=False,source_report_sha256=source_hashes))
    return selection, models, comparison


def main():
    selection,models,comparison = verify_and_select()
    report = '# Final YOLO model selection\n\n'
    report += '## 1. Candidate Models\n\nYOLOv8n and YOLOv8s are the two completed candidates, using training_v3 and 46 classes. This step verifies existing comparison/evaluation reports only. It does not train, run inference, modify datasets/checkpoints, copy a model or integrate FastAPI. YOLOv8m was intentionally not trained.\n\n'
    report += '## 2. Test Performance\n\n| Metric | YOLOv8n | YOLOv8s |\n|---|---:|---:|\n'
    for metric in METRICS:
        report+=f"| {metric} | {100*models['yolov8n']['test'][metric]:.3f}% | {100*models['yolov8s']['test'][metric]:.3f}% |\n"
    report += '\nAll numbers are read from the original reports and cross-checked against comparison JSON/CSV and the rounded observations supplied for this selection. F1 is the harmonic mean of macro precision and recall.\n\n'
    report += '## 3. Efficiency Comparison\n\n| Measure | YOLOv8n | YOLOv8s |\n|---|---:|---:|\n'
    for key,label in [('model_size_MB','Size (decimal MB)'),('average_inference_time_ms','CPU latency (ms/image)'),('FPS','FPS')]:
        report+=f"| {label} | {models['yolov8n']['benchmark'][key]:.3f} | {models['yolov8s']['benchmark'][key]:.3f} |\n"
    report += '\nThe benchmark used identical 50-image subsets and five warmups. Batch-1 wall latency includes loading and pre/postprocessing; it excludes saving. FPS is reciprocal latency.\n\n'
    report += '## 4. Precision vs Recall Trade-off\n\nYOLOv8n has higher test precision and F1; YOLOv8s has higher recall and narrowly higher test mAP50–95. False food identities can insert incorrect nutrition entries; missed foods can omit carbohydrate contributions. Both matter. Precision and CPU efficiency are prioritized here, while the recall disadvantage is retained explicitly. Operating points were selected separately by the validator; no threshold was changed in this documentation step.\n\n'
    report += '## 5. Generalization Considerations\n\n'
    for name,values in models.items():
        report+=f"{name}: validation mAP50–95 {100*values['validation']['mAP50_95']:.3f}%, test {100*values['test']['mAP50_95']:.3f}%.\n\n"
    report += 'YOLOv8s leads all validation metrics but shows only a small overall test AP50–95 gain and lower test AP50. This is a possible generalization difference, not sufficient evidence of overfitting. Training histories and evaluated class sets also differ.\n\n'
    report += '## 6. Application-Specific Considerations\n\nThe planned workflow is meal image → detection → nutrition mapping → carbohydrate estimation → GI/GL calculation → personalized recommendation. Incorrect identities and omissions may propagate through this chain. Lower CPU latency and storage requirements make YOLOv8n a practical candidate for future FastAPI use, but server performance, production confidence thresholds and downstream nutritional validity have not been established. No model is deployed by this step.\n\n'
    report += '\n'.join('- '+reason for reason in selection['tradeoffs'])+'\n\n'
    report += '## 7. Dataset Limitations\n\n'+'\n'.join('- '+item for item in selection['known_limitations'])+'\n\n'
    report += '## 8. Final Selection\n\n**FINAL_SELECTED_MODEL = '+selection['selected_model']+'**\n\nStatus: `'+selection['selection_status']+'`.\n\n'+'\n'.join('- '+reason for reason in selection['selection_reasons'])+'\n\nThis is the final documented model choice for the stated project priorities, not a claim of universal or statistically proven superiority. It authorizes no checkpoint publication or integration.\n\n'
    report += '## 9. Why YOLOv8m Was Not Tested\n\n**yolov8m_tested = false**\n\n'+selection['yolov8m_reason_not_tested']+' This does not prove a larger model would perform worse.\n\n'
    report += '## 10. Source Checkpoint\n\n`'+selection['source_checkpoint']+'`\n\nThe path and recorded checkpoint hash are taken from the saved evaluation provenance. This selection script neither opens nor copies the checkpoint. Source report SHA256 hashes and verification outcomes are stored in final_model_selection.json.\n'
    # Verify all inputs are unchanged before publishing documentation.
    for relative,digest in selection['verification']['source_report_sha256'].items():
        require(hashlib.sha256((BACKEND/relative).read_bytes()).hexdigest()==digest,'input report changed during selection')
    (COMPARISON/'final_model_selection.json').write_text(json.dumps(selection,indent=2,allow_nan=False)+'\n')
    (COMPARISON/'final_model_selection.md').write_text(report)
    print(json.dumps({k:selection[k] for k in ['selected_model','selection_status','source_checkpoint','yolov8m_tested']},indent=2))


if __name__=='__main__': main()
