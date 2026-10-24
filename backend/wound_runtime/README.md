# Local PyTorch wound runtime

This service runs separately from the clinic API because the trained models use
PyTorch 2.6 and Python 3.12. Keep the main backend's environment unchanged. The
clinic API calls this runtime over loopback; browsers do not call it directly.

The three supported architectures are **alternative dual-head segmenters**:
`unet_resnet18`, `deeplabv3plus_mobilenet_v2`, and `segformer_mit_b0`. Each produces
an independent open-wound mask and an eight-channel tissue prediction. These
are not three separate wound, tissue, and healing stages. No healing assessment,
physical size, depth, tissue percentages, or graphs are computed here.

## Configure and run

Use a Python 3.12 virtual environment with the versions in `requirements.txt`.
For a fresh environment, run from the repository root:

```powershell
py -3.12 -m venv backend\.venv-wound-runtime
& .\backend\.venv-wound-runtime\Scripts\python.exe -m pip install -r .\backend\wound_runtime\requirements.txt
```

For GPU use, install the official PyTorch 2.6.0 / torchvision 0.21.0 CUDA wheel
pair appropriate for the machine in that isolated environment. The pins also
accept matching CPU/CUDA local version builds. The service never downloads
weights or pretrained encoders.

Create a local JSON configuration outside tracked source (for example,
`backend/wound-runtime.local.json`, which is Git-ignored):

```json
{
  "checkpoint_root": "C:/Projects/RP_Planner_373/backend/trained_models/wound",
  "token": "replace-with-a-long-random-local-secret",
  "device": "auto"
}
```

`checkpoint_root` contains the three model-ID subdirectories, each containing
`final.pt`. Use `cpu` or `cuda` to require a device; `auto` selects CUDA when
available and otherwise CPU. Configure the clinic API with the same secret.

Start from the repository root, setting the configuration file's actual path:

```powershell
$env:WOUND_RUNTIME_CONFIG = (Resolve-Path .\backend\wound-runtime.local.json).Path
& .\backend\.venv-wound-runtime\Scripts\python.exe -m uvicorn wound_runtime.server:app --app-dir backend --host 127.0.0.1 --port 8010
```

An existing compatible Python 3.12 environment can replace the executable in the
command. Keep the host bound to `127.0.0.1`; there is no browser CORS configuration.
Model loading is lazy and happens only on an authenticated prediction request.

## HTTP contract

- `GET /health`: public minimal `{status, device, model_count}` readiness data.
- `GET /models`: Bearer authentication; returns `default_model_id` and a `models`
  list with `model_id`, `model_name`, and `available` for each allowlisted model.
- `POST /predict`: Bearer authentication and multipart fields `image`, `model_id`,
  and `checkpoint_sha256` (the expected 64-character SHA-256 of `final.pt`).

The runtime reads the selected checkpoint once per request, hashes those bytes,
and loads exactly those bytes with `torch.load(..., weights_only=True)`. A hash
mismatch returns HTTP 409. Loaded models are cached by model ID and hash; only
one model is retained in accelerator memory. Missing/incompatible checkpoints or
inference failures return HTTP 503. Invalid image uploads return HTTP 400 and
invalid form fields return HTTP 422. Error responses omit local paths and secrets.

Predictions contain only:

```text
model_id, checkpoint_sha256, image_width, image_height,
source = "model_prediction",
supported_tissue_classes = [0, 1, 2, 3, 5, 6, 7],
unsupported_tissue_classes = [4],
wound_mask_data_url, tissue_mask_data_url
```

Both masks are lossless, single-channel numeric PNGs at the photograph's stored
dimensions, with exact class IDs rather than coloured previews. Open wound is
0/1. Tissue IDs are 0 background, 1 epithelialization, 2 granulation, 3 slough,
4 fibrin (disabled because there were no training examples), 5 necrosis,
6 bone/tendon/muscle, and 7 other. No ignored pixels are invented by inference.

## Exact training preprocessing

Decode a single-frame JPEG/PNG/WebP into RGB, retaining stored geometry without
applying EXIF rotation. Uploads are limited to 10 MiB and 20 megapixels. Resize
with bilinear interpolation into a black, aspect-preserving square letterbox
using the checkpoint's `config.image_size` (512 for the supplied checkpoints).
Convert to float32 CHW, divide by 255, then apply ImageNet mean
`[0.485, 0.456, 0.406]` and standard deviation `[0.229, 0.224, 0.225]`.

The architecture has 10 output channels: eight tissue channels plus two
independent open-wound channels. Restore logits through letterbox cropping and
bilinear interpolation to the original dimensions before argmax. Suppress tissue
class 4 before argmax, matching the original inference protocol. Checkpoint model
ID, input dimensions, supported-class protocol, and all state-dict tensors are
validated before prediction.
