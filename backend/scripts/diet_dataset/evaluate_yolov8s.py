"""Evaluate YOLOv8s with the identical YOLOv8n evaluation implementation.

From backend: .venv/bin/python scripts/diet_dataset/evaluate_yolov8s.py --device cpu
CPU matches the saved YOLOv8n evaluation and benchmark device.
"""
from evaluate_yolov8n import main
from train_yolov8n import DIET_OUTPUT


if __name__ == '__main__':
    main(run=DIET_OUTPUT/'yolov8s_baseline', model_label='YOLOv8s')
