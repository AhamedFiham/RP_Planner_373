"""Lazy singleton food detector. No nutrition or recommendation processing."""
from pathlib import Path
from threading import Lock
import hashlib
import json
import math
import os
from dotenv import load_dotenv
from PIL import Image
from app.models.diet_model import DietDetector
from app.schemas.diet_schema import BoundingBox, DietModelInfo, FoodDetection, FoodDetectionResponse

BACKEND = Path(__file__).resolve().parents[2]
PACKAGE = BACKEND / 'trained_models/diet'
DEFAULT_CONFIDENCE = 0.25
load_dotenv(BACKEND / '.env')
_load_lock = Lock()
_predict_lock = Lock()
_detector: DietDetector | None = None


class DietDetectionError(RuntimeError):
    """A model configuration, loading or inference failure."""


def confidence_threshold() -> float:
    try:
        value = float(os.getenv('DIET_DETECTION_CONFIDENCE', str(DEFAULT_CONFIDENCE)))
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Out of range')
        return value
    except ValueError as exc:
        raise DietDetectionError('DIET_DETECTION_CONFIDENCE must be a finite number between 0 and 1.') from exc


def get_detector() -> DietDetector:
    """Only one successful load per worker process, including concurrent first calls."""
    global _detector
    with _load_lock:
        if _detector is None:
            try:
                metadata = json.loads((PACKAGE / 'model_metadata.json').read_text())
                names = {int(k): v for k, v in json.loads((PACKAGE / 'class_names.json').read_text()).items()}
                if len(names) != 46 or set(names) != set(range(46)) or metadata['class_count'] != 46:
                    raise ValueError('Diet class mapping must contain exactly IDs 0–45.')
                checkpoint = PACKAGE / 'best.pt'
                if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != metadata['checkpoint_sha256']:
                    raise ValueError('Diet checkpoint integrity mismatch.')
                # Import only when diet is requested; no network or pretrained download.
                os.environ.setdefault('YOLO_CONFIG_DIR', str(BACKEND / 'outputs/diet/.ultralytics'))
                os.environ.setdefault('MPLCONFIGDIR', str(BACKEND / 'outputs/diet/.matplotlib'))
                from ultralytics import YOLO
                model = YOLO(str(checkpoint))
                if model.task != 'detect' or {int(k): v for k, v in model.names.items()} != names:
                    raise ValueError('Diet model names do not match class_names.json.')
                if metadata['selected_model'] != 'YOLOv8n' or metadata['input_image_size'] != 640:
                    raise ValueError('Unexpected diet deployment model configuration.')
                _detector = DietDetector(model=model, class_names=names, metadata=metadata)
            except Exception as exc:
                raise DietDetectionError('Diet model package could not be loaded; check checkpoint and class mapping.') from exc
        return _detector


def detect_food(image: Image.Image) -> FoodDetectionResponse:
    threshold = confidence_threshold()
    detector = get_detector()
    width, height = image.size
    try:
        # Ultralytics' predictor is mutable; serialize shared-process prediction.
        with _predict_lock:
            result = detector.model.predict(source=image, imgsz=detector.metadata['input_image_size'],
                                            conf=threshold, iou=0.7, device='cpu',
                                            save=False, save_txt=False, save_crop=False, verbose=False)[0]
            boxes = result.boxes
            rows = [] if boxes is None else boxes.data.detach().cpu().tolist()
        detections = []
        for row in rows:
            if len(row) != 6:
                raise ValueError('Unexpected detection tensor format')
            x1, y1, x2, y2, confidence, raw_id = row
            if not all(math.isfinite(v) for v in row) or raw_id != int(raw_id):
                raise ValueError('Invalid detection values')
            cid = int(raw_id)
            if cid not in detector.class_names or not 0 <= confidence <= 1:
                raise ValueError('Invalid detection class or confidence')
            if confidence < threshold:
                continue
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError('Detection box exceeds input image bounds')
            detections.append(FoodDetection(class_id=cid, food_name=detector.class_names[cid],
                confidence=confidence, bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)))
        detections.sort(key=lambda d: (-d.confidence, d.class_id, d.bounding_box.x1, d.bounding_box.y1))
        return FoodDetectionResponse(detection_count=len(detections), detections=detections,
            image_width=width, image_height=height, model_name=detector.metadata['selected_model'],
            confidence_threshold=threshold)
    except Exception as exc:
        raise DietDetectionError('Food detection failed.') from exc


def model_info() -> DietModelInfo:
    threshold = confidence_threshold()
    metadata = get_detector().metadata
    return DietModelInfo(**{key: metadata[key] for key in ['selected_model','dataset_version','class_count','input_image_size']},
                         confidence_threshold=threshold)
