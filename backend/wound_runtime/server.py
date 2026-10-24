"""Loopback-only, authenticated inference for the trained dual-head DFU models.

Run this package with its own Python 3.12 environment. Importing this module
does not load model weights or download any model assets.
"""
from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import secrets
import threading
from typing import Annotated, Literal
import warnings

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
import numpy as np
from PIL import Image, UnidentifiedImageError
import torch
import torch.nn.functional as F


logger = logging.getLogger(__name__)
ModelId = Literal["unet_resnet18", "deeplabv3plus_mobilenet_v2", "segformer_mit_b0"]
MODEL_SPECS = {
    "unet_resnet18": {
        "name": "U-Net / ResNet-18", "encoder": "resnet18", "architecture": "Unet",
    },
    "deeplabv3plus_mobilenet_v2": {
        "name": "DeepLabV3+ / MobileNetV2", "encoder": "mobilenet_v2", "architecture": "DeepLabV3Plus",
    },
    "segformer_mit_b0": {
        "name": "SegFormer / MiT-B0", "encoder": "mit_b0", "architecture": "Segformer",
    },
}
DEFAULT_MODEL_ID = "unet_resnet18"
SUPPORTED_TISSUE_CLASSES = [0, 1, 2, 3, 5, 6, 7]
UNSUPPORTED_TISSUE_CLASSES = [4]
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000


class PipelineError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RuntimeSettings:
    checkpoint_root: Path
    token: str
    device: str

    @classmethod
    def from_environment(cls) -> "RuntimeSettings":
        config_path = os.environ.get("WOUND_RUNTIME_CONFIG")
        if not config_path:
            raise RuntimeError("WOUND_RUNTIME_CONFIG must identify a local runtime configuration file.")
        try:
            with Path(config_path).open(encoding="utf-8-sig") as stream:
                config = json.load(stream)
        except (OSError, ValueError) as exc:
            raise RuntimeError("The wound runtime configuration could not be read.") from exc
        if not isinstance(config, dict):
            raise RuntimeError("The wound runtime configuration must be a JSON object.")
        root = config.get("checkpoint_root")
        token = config.get("token")
        device = config.get("device", "auto")
        if not isinstance(root, str) or not root.strip():
            raise RuntimeError("The runtime configuration requires checkpoint_root.")
        if not isinstance(token, str) or not token.strip():
            raise RuntimeError("The runtime configuration requires a nonempty token.")
        if device not in {"auto", "cpu", "cuda"}:
            raise RuntimeError("The runtime device must be auto, cpu, or cuda.")
        return cls(Path(root).expanduser().resolve(), token, device)


def decode_image(data: bytes) -> Image.Image:
    """Match the training pipeline's stored pixel geometry, including EXIF handling."""
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise PipelineError(400, "Upload must contain an image of at most 10 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise PipelineError(400, "Only decoded JPEG, PNG, and WebP images are supported.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise PipelineError(400, "Image exceeds the 20 megapixel limit.")
                if getattr(source, "n_frames", 1) != 1:
                    raise PipelineError(400, "Animated or multi-frame images are not supported.")
                source.load()
                # Do not apply EXIF rotation: training image/mask pairs use the
                # stored geometry, and the numeric output must align with it.
                return source.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise PipelineError(400, "The upload is not a supported, readable image.") from exc


def letterbox(image: Image.Image, image_size: int) -> tuple[torch.Tensor, tuple[int, int, int, int]]:
    """Black RGB letterbox and ImageNet normalization used during training."""
    image = image.convert("RGB")
    width, height = image.size
    scale = image_size / max(width, height)
    resized = (max(1, round(width * scale)), max(1, round(height * scale)))
    left, top = ((image_size - resized[0]) // 2, (image_size - resized[1]) // 2)
    canvas = Image.new("RGB", (image_size, image_size), (0, 0, 0))
    canvas.paste(image.resize(resized, Image.Resampling.BILINEAR), (left, top))
    tensor = torch.from_numpy(np.array(canvas)).permute(2, 0, 1).float().div_(255)
    mean = torch.tensor(IMAGENET_MEAN, dtype=torch.float32)[:, None, None]
    std = torch.tensor(IMAGENET_STD, dtype=torch.float32)[:, None, None]
    return ((tensor - mean) / std).unsqueeze(0).contiguous(), (left, top, *resized)


def restore_logits(logits: torch.Tensor, box: tuple[int, int, int, int],
                   image_size: int, original_size: tuple[int, int]) -> torch.Tensor:
    """Crop letterbox padding and restore logits before selecting class IDs."""
    if logits.ndim != 4 or logits.shape[0] != 1:
        raise ValueError("Expected a single BCHW prediction.")
    if logits.shape[-2:] != (image_size, image_size):
        logits = F.interpolate(logits.float(), size=(image_size, image_size),
                               mode="bilinear", align_corners=False)
    left, top, width, height = box
    cropped = logits[:, :, top:top + height, left:left + width]
    return F.interpolate(cropped.float(), size=(original_size[1], original_size[0]),
                         mode="bilinear", align_corners=False)


def build_model(model_id: str):
    import segmentation_models_pytorch as smp

    spec = MODEL_SPECS[model_id]
    options = dict(encoder_name=spec["encoder"], encoder_weights=None,
                   in_channels=3, classes=10, activation=None)
    if model_id == "deeplabv3plus_mobilenet_v2":
        options.update(encoder_output_stride=16, decoder_channels=128)
    elif model_id == "segformer_mit_b0":
        options.update(decoder_segmentation_channels=256)
    # All encoder tensors come from the supplied checkpoint, never downloads.
    return getattr(smp, spec["architecture"])(**options)


def numeric_png_data_url(mask: np.ndarray) -> str:
    buffer = BytesIO()
    Image.fromarray(mask.astype(np.uint8)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


class RuntimeEngine:
    """Serialize requests and retain only one model in accelerator memory."""

    def __init__(self, settings: RuntimeSettings):
        self.settings = settings
        requested = settings.device
        selected = ("cuda" if torch.cuda.is_available() else "cpu") if requested == "auto" else requested
        if selected == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("The configured CUDA device is unavailable.")
        self.device = torch.device(selected)
        self._lock = threading.Lock()
        self._loaded_key: tuple[str, str] | None = None
        self._model = None
        self._image_size: int | None = None

    def _checkpoint_path(self, model_id: str) -> Path:
        if model_id not in MODEL_SPECS:
            raise PipelineError(422, "Unknown model ID.")
        path = (self.settings.checkpoint_root / model_id / "final.pt").resolve()
        if not path.is_relative_to(self.settings.checkpoint_root):
            raise PipelineError(503, "Selected model checkpoint is unavailable.")
        return path

    def models(self) -> dict:
        rows = []
        for model_id, spec in MODEL_SPECS.items():
            try:
                available = self._checkpoint_path(model_id).is_file()
            except (OSError, PipelineError):
                available = False
            rows.append({"model_id": model_id, "model_name": spec["name"], "available": available})
        return {"default_model_id": DEFAULT_MODEL_ID, "models": rows}

    def _load(self, model_id: str, checkpoint_bytes: bytes, checkpoint_sha256: str) -> None:
        key = (model_id, checkpoint_sha256)
        if self._loaded_key == key and self._model is not None:
            return
        self._model = None
        self._loaded_key = None
        self._image_size = None
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        checkpoint = torch.load(BytesIO(checkpoint_bytes), map_location="cpu", weights_only=True)
        if not isinstance(checkpoint, dict) or checkpoint.get("model_id") != model_id:
            raise ValueError("Checkpoint model ID does not match the selected model.")
        config = checkpoint.get("config")
        if not isinstance(config, dict):
            raise ValueError("Checkpoint is missing its training configuration.")
        image_size = config.get("image_size")
        if type(image_size) is not int or not 32 <= image_size <= 2048:
            raise ValueError("Checkpoint image_size is invalid.")
        if checkpoint.get("supported_tissue_classes") != SUPPORTED_TISSUE_CLASSES:
            raise ValueError("Checkpoint supported tissue classes differ from the training protocol.")
        if checkpoint.get("unsupported_tissue_classes") != UNSUPPORTED_TISSUE_CLASSES:
            raise ValueError("Checkpoint unsupported tissue classes differ from the training protocol.")
        model = build_model(model_id)
        model.load_state_dict(checkpoint["state_dict"], strict=True)
        self._model = model.to(self.device).eval()
        self._loaded_key = key
        self._image_size = image_size

    def predict(self, data: bytes, model_id: str, expected_sha256: str) -> dict:
        with self._lock:
            image = decode_image(data)
            try:
                # Read once, hash those bytes, and load those exact same bytes.
                # This also detects replacements when a model is already cached.
                checkpoint_bytes = self._checkpoint_path(model_id).read_bytes()
            except OSError as exc:
                raise PipelineError(503, "Selected model checkpoint is unavailable.") from exc
            digest = hashlib.sha256(checkpoint_bytes).hexdigest()
            if not secrets.compare_digest(digest, expected_sha256.lower()):
                raise PipelineError(409, "The checkpoint changed. Refresh the model configuration and retry.")
            self._load(model_id, checkpoint_bytes, digest)
            tensor, box = letterbox(image, self._image_size)
            with torch.inference_mode():
                logits = self._model(tensor.to(self.device))
                if logits.ndim != 4 or logits.shape[1] != 10:
                    raise ValueError("Expected eight tissue and two open-wound output channels.")
                if not torch.isfinite(logits).all():
                    raise ValueError("Model produced non-finite logits.")
                tissue_logits = restore_logits(logits[:, :8], box, self._image_size, image.size)
                wound_logits = restore_logits(logits[:, 8:10], box, self._image_size, image.size)
                # No positive fibrin training labels exist in this fixed protocol.
                tissue_logits[:, UNSUPPORTED_TISSUE_CLASSES, :, :] = -1e4
                tissue = tissue_logits.argmax(1)[0].cpu().numpy().astype(np.uint8)
                wound = wound_logits.argmax(1)[0].cpu().numpy().astype(np.uint8)
            return {
                "model_id": model_id,
                "checkpoint_sha256": digest,
                "image_width": image.width,
                "image_height": image.height,
                "source": "model_prediction",
                "supported_tissue_classes": list(SUPPORTED_TISSUE_CLASSES),
                "unsupported_tissue_classes": list(UNSUPPORTED_TISSUE_CLASSES),
                "wound_mask_data_url": numeric_png_data_url(wound),
                "tissue_mask_data_url": numeric_png_data_url(tissue),
            }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = RuntimeSettings.from_environment()
    app.state.engine = RuntimeEngine(settings)
    yield


app = FastAPI(title="Local wound model runtime", version="1.0.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


def require_token(request: Request, authorization: Annotated[str | None, Header()] = None) -> None:
    expected = "Bearer " + request.app.state.engine.settings.token
    if authorization is None or not secrets.compare_digest(authorization.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Runtime authentication required.",
                            headers={"WWW-Authenticate": "Bearer"})


@app.get("/health")
def health(request: Request) -> dict:
    engine = request.app.state.engine
    return {"status": "ok", "device": engine.device.type,
            "model_count": sum(row["available"] for row in engine.models()["models"])}


@app.get("/models", dependencies=[Depends(require_token)])
def models(request: Request) -> dict:
    return request.app.state.engine.models()


@app.post("/predict", dependencies=[Depends(require_token)])
async def predict(
    request: Request,
    image: Annotated[UploadFile, File()],
    model_id: Annotated[ModelId, Form()],
    checkpoint_sha256: Annotated[str, Form(pattern=r"^[a-fA-F0-9]{64}$")],
) -> dict:
    try:
        data = await image.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await image.close()
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Upload must contain an image of at most 10 MiB.")
    try:
        return await run_in_threadpool(request.app.state.engine.predict, data, model_id, checkpoint_sha256)
    except PipelineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Wound model inference failed; no prediction was generated.")
        raise HTTPException(status_code=503, detail="Model inference failed; no prediction was generated.") from exc
