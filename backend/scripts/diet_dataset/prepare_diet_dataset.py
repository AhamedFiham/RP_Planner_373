"""Read-only dry run or reproducible preparation of diet image datasets.

Run from backend: python scripts/diet_dataset/prepare_diet_dataset.py --dry-run
"""
from pathlib import Path
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime,timezone

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diet_dataset.dataset_sources import audit
from diet_dataset.dataset_sources import decision, category, PRIORITY, SUSPICIOUS, key
from diet_dataset.validation import inspect_image, EXTENSIONS
from diet_dataset.validation import parse_row
from diet_dataset.validation import convert_bbox
from diet_dataset.image_groups import deduplicate
from diet_dataset.outputs import report

BACKEND=Path(__file__).resolve().parents[2]
SPLITS={'train':'train','training':'train','valid':'valid','val':'valid','validation':'valid','test':'test'}



def execute(data: dict, reports: Path, names: list[str], backend: Path, force: bool) -> None:
    from diet_dataset.outputs import write_outputs
    write_outputs(data,reports,names,backend,force)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--dry-run',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--force',action='store_true',help='Archive and rebuild only generated pipeline output folders')
    args=parser.parse_args()
    if args.force and not args.execute: parser.error('--force requires --execute')
    reports=BACKEND/'datasets/diet/processed/reports/dry_run'
    reports.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s',handlers=[logging.StreamHandler(),logging.FileHandler(reports/'diet_dataset_preparation.log')])
    data=audit(BACKEND/'datasets/diet/raw')
    summary,names=report(data,reports)
    logging.info('%s: %s','EXECUTE PLAN' if args.execute else 'DRY RUN', json.dumps({k:v for k,v in summary.items() if k!='critical_detection'},indent=2))
    if args.execute: execute(data,reports,names,BACKEND,args.force)


if __name__=='__main__': main()
