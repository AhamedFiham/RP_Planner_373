"""Configure the supplied three-model checkpoints without copying their weights."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets

BACKEND = Path(__file__).resolve().parents[1]
MODELS = {
    "unet_resnet18": "U-Net / ResNet18",
    "deeplabv3plus_mobilenet_v2": "DeepLabV3+ / MobileNetV2",
    "segformer_mit_b0": "SegFormer / MiT-B0",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-root", type=Path, default=BACKEND / "trained_models" / "wound",
                        help="Folder containing the three model directories (default: backend/trained_models/wound).")
    parser.add_argument("--service-url", default="http://127.0.0.1:8010")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    root = args.checkpoint_root.expanduser().resolve()
    if (root / "runs").is_dir():
        root = root / "runs"
    checkpoints = {key: root / key / "final.pt" for key in MODELS}
    if any(not path.is_file() for path in checkpoints.values()):
        parser.error("The checkpoint root must contain all three model folders with final.pt files.")
    runtime_path = BACKEND / "wound-runtime.local.json"
    model_path = BACKEND / "wound-models.local.json"
    previous = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path.is_file() else {}
    token = previous.get("token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(48)
    profiles = {}
    for model_id, label in MODELS.items():
        digest = hashlib.sha256(checkpoints[model_id].read_bytes()).hexdigest()
        profile = {"label": label}
        for stage, factory in [("wound_segmentation", "build_wound_adapter"), ("tissue_segmentation", "build_tissue_adapter")]:
            profile[stage] = {
                "adapter": f"app.models.prototype_adapter:{factory}",
                "weights_path": checkpoints[model_id].relative_to(BACKEND).as_posix() if checkpoints[model_id].is_relative_to(BACKEND) else str(checkpoints[model_id]),
                "model_version": "checkpoint-" + digest[:12],
                "parameters": {"model_id": model_id, "service_url": args.service_url,
                               "runtime_token": token, "timeout_seconds": 180},
            }
        profiles[model_id] = profile
    runtime_path.write_text(json.dumps({"checkpoint_root": str(root), "token": token, "device": args.device}, indent=2) + "\n", encoding="utf-8")
    model_path.write_text(json.dumps({"default_model_id": "unet_resnet18", "profiles": profiles}, indent=2) + "\n", encoding="utf-8")
    env_path = BACKEND / ".env"
    text = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
    setting = "WOUND_MODEL_CONFIG=" + model_path.as_posix()
    if re.search(r"^WOUND_MODEL_CONFIG=.*$", text, flags=re.MULTILINE):
        text = re.sub(r"^WOUND_MODEL_CONFIG=.*$", lambda _: setting, text, flags=re.MULTILINE)
    else:
        text = text.rstrip("\n") + ("\n" if text else "") + setting + "\n"
    env_path.write_text(text, encoding="utf-8")
    print("Configured 3 model profiles. Model weights were not copied or modified.")
    print("Restart the clinic backend and model runtime after changing this configuration.")
    print("The local configuration files and runtime token are excluded from Git.")


if __name__ == "__main__":
    main()
