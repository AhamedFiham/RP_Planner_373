"""Train only the requested YOLOv8s baseline against immutable training_v3.

From backend: .venv/bin/python scripts/diet_dataset/train_yolov8s.py --check
              .venv/bin/python scripts/diet_dataset/train_yolov8s.py
Only use --resume after an interrupted run with a valid last.pt checkpoint.
"""
from pathlib import Path
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import inspect
import json
import logging
import os
import platform
import shutil
import sys
import time

BACKEND=Path(__file__).resolve().parents[2]
DIET_OUTPUT=BACKEND/'outputs/diet'
RUN=DIET_OUTPUT/'yolov8s_baseline'
REFERENCE=DIET_OUTPUT/'yolov8n_baseline/experiment_config.json'
DATASET=BACKEND/'datasets/diet/training_v3'


def snapshot(folder: Path) -> dict[str,str]:
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file()}


def select_device(torch) -> str:
    if torch.cuda.is_available():return 'cuda:0'
    if hasattr(torch.backends,'mps') and torch.backends.mps.is_available():return 'mps'
    return 'cpu'


def redirect_cache_writer(original,cache_dir: Path):
    """Redirect Ultralytics label caches into experiment outputs, not the dataset."""
    signature=inspect.signature(original)
    if 'path' not in signature.parameters:
        raise RuntimeError('Unsupported Ultralytics cache API; stop before dataset writes')
    def save(*args,**kwargs):
        bound=signature.bind(*args,**kwargs);path=Path(bound.arguments['path'])
        digest=hashlib.sha256(str(path).encode()).hexdigest()[:12]
        cache_dir.mkdir(parents=True,exist_ok=True)
        bound.arguments['path']=cache_dir/f'{path.stem}_{digest}.cache'
        return original(*bound.args,**bound.kwargs)
    return save


def metrics_dict(result) -> dict:
    values=getattr(result,'results_dict',{}) or {}
    return {str(key):float(value) for key,value in values.items()}


def resume_trainer_for_epochs(base_trainer, epochs: int):
    """Apply a new total-epoch limit after Ultralytics restores checkpoint args.

Ultralytics 8.4.182 ignores epochs in ordinary resume overrides. This changes
only the in-memory trainer args; original checkpoint files are not rewritten.
    """
    class EpochLimitedResumeTrainer(base_trainer):
        def check_resume(self, overrides):
            super().check_resume(overrides)
            if self.resume:
                self.args.epochs = epochs
    return EpochLimitedResumeTrainer


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Validate setup and report selected device without training')
    parser.add_argument('--resume',action='store_true',help='Resume this same baseline from its last.pt')
    parser.add_argument('--epochs',type=int,default=30,help='Total epochs including completed checkpoint epochs (default: 30)')
    args=parser.parse_args()
    if args.epochs<1:parser.error('--epochs must be positive')
    for variable,path in [('YOLO_CONFIG_DIR',DIET_OUTPUT/'.ultralytics'),('MPLCONFIGDIR',DIET_OUTPUT/'.matplotlib'),('TORCH_HOME',DIET_OUTPUT/'.torch')]:
        os.environ.setdefault(variable,str(path));path.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK','1')
    os.environ.setdefault('WANDB_DISABLED','true')
    import torch
    import ultralytics
    import yaml
    from ultralytics import YOLO
    from ultralytics.utils import SETTINGS,LOGGER
    from ultralytics.data import dataset as yolo_dataset
    # Prevent optional third-party logging or automatic extra-model checks.
    SETTINGS.update({key:False for key in ('sync','wandb','comet','clearml','mlflow','neptune','raytune','hub') if key in SETTINGS})
    readiness=json.loads((DATASET/'final_dataset_readiness.json').read_text())
    if not readiness.get('ready_for_training') or readiness.get('class_count')!=46:
        raise RuntimeError('V3 readiness must pass for exactly 46 classes')
    data=yaml.safe_load((DATASET/'data.yaml').read_text())
    if set(data['names'])!=set(range(46)) or data.get('nc')!=46:raise ValueError('V3 class IDs must remain 0–45')
    for split,key in [('train','train'),('valid','val'),('test','test')]:
        if (Path(data['path'])/data[key]).resolve()!=(DATASET/split/'images').resolve():raise ValueError('Dataset split path mismatch')
    reference=json.loads(REFERENCE.read_text())
    expected=dict(image_size=640,epochs=30,patience=20,seed=42,workers=0,
                  batch=4,cache=False,deterministic=True,amp=False,
                  dataset_version='training_v3',validation_split='valid',test_split_used=False)
    mismatches={key:(reference.get(key),value) for key,value in expected.items() if reference.get(key)!=value}
    if mismatches:raise ValueError(f'YOLOv8n reference settings changed: {mismatches}')
    if args.epochs!=reference['epochs']:raise ValueError('Epoch count must match the YOLOv8n baseline: 30')
    if torch.__version__!=reference['pytorch_version'] or ultralytics.__version__!=reference['ultralytics_version']:
        raise RuntimeError('Use the same PyTorch and Ultralytics versions as the YOLOv8n baseline')
    device=select_device(torch)
    if device!=reference['device'] and not args.check:
        raise RuntimeError(f"Reference device is {reference['device']}; available device is {device}. Run in a terminal with the reference device available.")
    # Conservative fixed batches avoid AutoBatch assumptions on MPS/CPU.
    batch=8 if device.startswith('cuda') else 4
    workers=0
    # Verify the cache API before downloading weights or starting training.
    original_cache_saver=yolo_dataset.save_dataset_cache_file
    cache_saver=redirect_cache_writer(original_cache_saver,RUN/'dataset_cache')
    configuration=dict(model_name='yolov8s.pt',dataset_version='training_v3',dataset_path=str(DATASET/'data.yaml'),class_count=46,image_size=640,epochs=args.epochs,batch=batch,patience=20,seed=42,device=device,workers=workers,python_version=platform.python_version(),pytorch_version=torch.__version__,ultralytics_version=ultralytics.__version__,cache=False,deterministic=True,amp=False,validation_split='valid',test_split_used=False,source_dataset_cache_policy='redirect generated label caches to experiment outputs',online_augmentation='Ultralytics training-time defaults; source files untouched')
    configuration['comparison_reference']=str(REFERENCE)
    configuration['comparison_note']='YOLOv8n was initially scheduled for 100 epochs and resumed after epoch 2 with a 30-epoch limit. This run matches the final recorded 30-epoch settings; the initial learning-rate schedule and resume history are not identical.'
    configuration['reference_device']=reference['device']
    configuration['reference_settings_match']=True
    configuration['device_matches_reference']=device==reference['device']
    if args.check:
        print(json.dumps(configuration,indent=2));return
    if args.resume:
        if not (RUN/'weights/last.pt').exists():raise FileNotFoundError('No baseline last.pt checkpoint exists to resume')
        previous=json.loads((RUN/'experiment_config.json').read_text())
        configuration['previous_epochs']=previous.get('epochs')
        configuration['initial_training_started_at']=previous.get('initial_training_started_at',previous.get('training_started_at'))
        if previous['model_name']!='yolov8s.pt' or previous['dataset_version']!='training_v3':raise ValueError('Checkpoint configuration is not this baseline')
    elif RUN.exists() and any(RUN.iterdir()):
        summary_path=RUN/'training_summary.json'
        previous=json.loads(summary_path.read_text()) if summary_path.exists() else {}
        retry_setup_failure=previous.get('status')=='failed' and not (RUN/'weights/last.pt').exists() and not (RUN/'results.csv').exists()
        if not retry_setup_failure:
            raise FileExistsError('Baseline output already exists. Preserve it, or use --resume for this same interrupted experiment.')
    RUN.mkdir(parents=True,exist_ok=True)
    handler=logging.FileHandler(RUN/'training.log');handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));LOGGER.addHandler(handler)
    configuration['training_started_at']=datetime.now(timezone.utc).isoformat()
    configuration['resume']=args.resume
    (RUN/'experiment_config.json').write_text(json.dumps(configuration,indent=2))
    protected={'raw':BACKEND/'datasets/diet/raw','training_v3':DATASET}
    before={name:snapshot(path) for name,path in protected.items()}
    (RUN/'source_integrity_before.json').write_text(json.dumps(before,indent=2,sort_keys=True))
    summary=dict(status='running',training_completed_successfully=False,model_name='yolov8s.pt',device=device,epochs_requested=args.epochs,epochs_completed=0,best_epoch=None,early_stopping=False,training_started_at=configuration['training_started_at'],precision=None,recall=None,mAP50=None,mAP50_95=None)
    if args.resume and (RUN/'training_summary.json').exists():
        prior=json.loads((RUN/'training_summary.json').read_text());summary.update({k:v for k,v in prior.items() if k in {'best_epoch','epochs_completed'}})
    started=time.monotonic()
    yolo_dataset.save_dataset_cache_file=cache_saver
    # No fallback to a different model architecture is permitted.
    weights=RUN/'weights/last.pt' if args.resume else DIET_OUTPUT/'pretrained/yolov8s.pt'
    weights.parent.mkdir(parents=True,exist_ok=True)
    def persist(trainer=None):
        if trainer is not None:
            summary['epochs_completed']=trainer.epoch+1
            current=getattr(trainer,'fitness',None);best=getattr(trainer,'best_fitness',None)
            if current is not None and best is not None and current>=best:summary['best_epoch']=trainer.epoch+1
            summary['latest_validation_metrics']={str(k):float(v) for k,v in (getattr(trainer,'metrics',{}) or {}).items()}
        summary['elapsed_seconds']=round(time.monotonic()-started,3)
        (RUN/'training_summary.json').write_text(json.dumps(summary,indent=2))
        if trainer is not None:print('BASELINE_PROGRESS '+json.dumps({k:summary[k] for k in ['epochs_completed','best_epoch','elapsed_seconds']}),flush=True)
    persist()
    model=None
    try:
        model=YOLO(str(weights))
        if model.task!='detect':raise ValueError('Expected detection checkpoint')
        model.add_callback('on_fit_epoch_end',persist)
        if args.resume:
            from ultralytics.models.yolo.detect import DetectionTrainer
            completed=int(model.ckpt.get('epoch',-1))+1
            if completed>=args.epochs:
                raise ValueError(f'Checkpoint already completed {completed} epochs; requested total is {args.epochs}')
            trainer_class=resume_trainer_for_epochs(DetectionTrainer,args.epochs)
            result=model.train(trainer=trainer_class,resume=True,device=device,workers=workers,cache=False)
        else:
            result=model.train(data=str(DATASET/'data.yaml'),imgsz=640,epochs=args.epochs,patience=20,seed=42,workers=workers,batch=batch,device=device,project=str(DIET_OUTPUT),name='yolov8s_baseline',exist_ok=True,cache=False,deterministic=True,amp=False,plots=True,save=True,save_period=-1,val=True,verbose=True)
        values=metrics_dict(result)
        summary.update(status='completed',training_completed_successfully=True,epochs_completed=model.trainer.epoch+1,early_stopping=model.trainer.epoch+1<args.epochs,precision=values.get('metrics/precision(B)'),recall=values.get('metrics/recall(B)'),mAP50=values.get('metrics/mAP50(B)'),mAP50_95=values.get('metrics/mAP50-95(B)'),best_weights=str(RUN/'weights/best.pt'),last_weights=str(RUN/'weights/last.pt'),metrics=values)
        # Preserve native curve names and add the requested conventional names.
        for path in RUN.glob('*.png'):
            for prefix in ('Box_','Box'):
                if path.name.startswith(prefix):
                    destination=RUN/path.name[len(prefix):]
                    if not destination.exists():shutil.copy2(path,destination)
                    break
        if not (RUN/'weights/best.pt').is_file():raise RuntimeError('Training returned without best.pt')
        # Read actual completed epochs and best validation fitness from persisted results.
        with (RUN/'results.csv').open(newline='') as handle:
            epoch_rows=[{key.strip():value for key,value in row.items()} for row in csv.DictReader(handle)]
        best_row=max(epoch_rows,key=lambda row:float(row['metrics/mAP50-95(B)']))
        summary['best_epoch']=int(float(best_row['epoch']))
        summary['epochs_completed']=max(int(float(row['epoch'])) for row in epoch_rows)
        summary['early_stopping']=summary['epochs_completed']<args.epochs
        summary['model_size_MB']=(RUN/'weights/best.pt').stat().st_size/1_000_000
        summary['training_duration_scope']='Wall time for this invocation; resumed invocations have separate timing'

    except BaseException as exc:
        summary.update(status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',error_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        yolo_dataset.save_dataset_cache_file=original_cache_saver
        summary['immutable_sources']={name:snapshot(path)==before[name] for name,path in protected.items()}
        summary['training_finished_at']=datetime.now(timezone.utc).isoformat();persist()
        if not all(summary['immutable_sources'].values()):
            summary.update(status='source_integrity_failed',training_completed_successfully=False);persist()
            raise RuntimeError('Protected dataset changed; review source integrity report')
        print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
