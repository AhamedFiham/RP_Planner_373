"""Run with the compatible PyTorch Python environment, separately from the API."""

import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "wound-runtime.local.json")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    if not args.config.is_file():
        parser.error("Run scripts.configure_wound_models before starting the model runtime.")
    if not 1 <= args.port <= 65535:
        parser.error("Choose a valid TCP port.")
    os.environ["WOUND_RUNTIME_CONFIG"] = str(args.config.resolve())
    import uvicorn
    uvicorn.run("wound_runtime.server:app", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
