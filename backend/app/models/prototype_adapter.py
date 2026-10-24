"""Bridge the clinic API to the matching, isolated PyTorch prototype runtime.

The numeric masks and label palette match the supplied training/inference code.
No wound measurements, tissue percentages, or healing outputs are calculated.
"""

import base64
import hashlib
import io
import json
from pathlib import Path
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from PIL import Image

from app.database.repositories import wound_repository as repository
from app.models.wound_model import SegmentationResult, TissueResult

MODEL_IDS = {"unet_resnet18", "deeplabv3plus_mobilenet_v2", "segformer_mit_b0"}
SUPPORTED_TISSUES = [0, 1, 2, 3, 5, 6, 7]
TISSUE_COLORS = {
    0: (0, 0, 0), 1: (255, 102, 204), 2: (255, 0, 0),
    3: (128, 128, 128), 4: (255, 255, 0), 5: (139, 69, 19),
    6: (0, 255, 255), 7: (0, 176, 80), 255: (128, 0, 255),
}
MAX_RESPONSE_BYTES = 96 * 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise HTTPError(request.full_url, code, "Inference redirects are not allowed", headers, response)


class PrototypeAdapter:
    def __init__(self, weights_path, model_version, parameters, stage):
        if set(parameters) - {"model_id", "service_url", "runtime_token", "timeout_seconds"}:
            raise ValueError("Unknown prototype adapter parameter")
        self.weights_path = Path(weights_path).resolve()
        self.model_id = parameters["model_id"]
        if self.model_id not in MODEL_IDS or self.weights_path.parent.name != self.model_id or self.weights_path.name != "final.pt":
            raise ValueError("Checkpoint does not match the selected trained model")
        self.weights_sha256 = hashlib.sha256(self.weights_path.read_bytes()).hexdigest()
        self.model_version = model_version
        self.stage = stage
        self.service_url = parameters.get("service_url", "http://127.0.0.1:8010").rstrip("/")
        url = urlsplit(self.service_url)
        if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"} or url.username or url.password or url.path or url.query or url.fragment:
            raise ValueError("The prototype inference service must be a loopback HTTP URL")
        self.runtime_token = parameters["runtime_token"]
        if not isinstance(self.runtime_token, str) or len(self.runtime_token) < 24:
            raise ValueError("A private runtime token is required")
        self.timeout = parameters.get("timeout_seconds", 180)
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)) or not 1 <= self.timeout <= 600:
            raise ValueError("Invalid model timeout")
        self._outputs = set()

    def predict(self, image_path, wound_mask=None):
        image_path = Path(image_path)
        if hashlib.sha256(self.weights_path.read_bytes()).hexdigest() != self.weights_sha256:
            raise RuntimeError("Checkpoint changed after adapter initialization; retry with the current model")
        with Image.open(image_path) as original:
            size = original.size
            content_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(original.format)
        if content_type is None:
            raise ValueError("Unsupported stored image")
        if self.stage == "tissue_segmentation":
            # These trained models have independent heads. Preserve the dependency
            # for provenance without clipping epithelialization to an open wound.
            with Image.open(wound_mask) as mask:
                if mask.size != size:
                    raise ValueError("The wound mask does not match the image")

        boundary = "wound-" + secrets.token_hex(16)
        fields = {"model_id": self.model_id, "checkpoint_sha256": self.weights_sha256}
        parts = []
        for key, value in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="visit-image"\r\nContent-Type: {content_type}\r\n\r\n'.encode())
        parts.extend([image_path.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()])
        request = Request(self.service_url + "/predict", data=b"".join(parts), method="POST", headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": "Bearer " + self.runtime_token,
        })
        try:
            with build_opener(NoRedirects()).open(request, timeout=self.timeout) as response:
                encoded = response.read(MAX_RESPONSE_BYTES + 1)
                if len(encoded) > MAX_RESPONSE_BYTES:
                    raise ValueError("Inference response exceeds the limit")
                result = json.loads(encoded)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError("The PyTorch model service is unavailable or rejected this inference request") from error
        if (result.get("source") != "model_prediction" or result.get("model_id") != self.model_id
                or result.get("checkpoint_sha256") != self.weights_sha256
                or (result.get("image_width"), result.get("image_height")) != size
                or result.get("supported_tissue_classes") != SUPPORTED_TISSUES
                or result.get("unsupported_tissue_classes") != [4]):
            raise ValueError("Model response does not match the requested checkpoint and training protocol")

        field = "wound_mask_data_url" if self.stage == "wound_segmentation" else "tissue_mask_data_url"
        data_url = result.get(field, "")
        if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
            raise ValueError("The model did not return a PNG segmentation mask")
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
        with Image.open(io.BytesIO(raw)) as mask:
            if mask.format != "PNG" or mask.mode != "L" or mask.size != size or getattr(mask, "n_frames", 1) != 1:
                raise ValueError("The model mask is not aligned numeric label data")
            mask.load()
            labels = mask.tobytes()
        allowed = {0, 1} if self.stage == "wound_segmentation" else set(SUPPORTED_TISSUES)
        if not set(labels).issubset(allowed):
            raise ValueError("The mask contains labels unsupported by this trained model")

        # Palette PNG preserves numeric class IDs while displaying the known labels.
        rendered = Image.frombytes("P", size, labels)
        colors = {0: (0, 0, 0), 1: (255, 255, 255)} if self.stage == "wound_segmentation" else TISSUE_COLORS
        palette = [0] * 768
        for class_id, color in colors.items():
            palette[class_id * 3:class_id * 3 + 3] = color
        rendered.putpalette(palette)
        directory = repository.data_directory() / "model_scratch"
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / (str(uuid4()) + ".png")
        try:
            rendered.save(output, format="PNG")
        except Exception:
            output.unlink(missing_ok=True)
            raise
        self._outputs.add(output)
        result_type = SegmentationResult if self.stage == "wound_segmentation" else TissueResult
        return result_type(mask_path=output, model_version=self.model_version)

    def release(self, result):
        path = Path(result.mask_path)
        if path in self._outputs:
            path.unlink(missing_ok=True)
            self._outputs.discard(path)


def build_wound_adapter(*, weights_path, model_version, parameters):
    return PrototypeAdapter(weights_path, model_version, parameters, "wound_segmentation")


def build_tissue_adapter(*, weights_path, model_version, parameters):
    return PrototypeAdapter(weights_path, model_version, parameters, "tissue_segmentation")
