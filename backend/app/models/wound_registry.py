"""Lazy, explicitly configured inference adapters; no guessed PyTorch loader."""

import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import re
from threading import RLock

STAGES = ("wound_segmentation", "tissue_segmentation")
logger = logging.getLogger(__name__)


class ModelUnavailable(Exception):
    """A safe public availability error, without configuration paths."""


class InvalidModelSelection(Exception):
    pass


class WoundModelRegistry:
    def __init__(self):
        self._locks = {stage: RLock() for stage in STAGES}
        self._loaded = {}
        self._errors = set()

    def lock(self, stage):
        return self._locks[stage]

    def _document(self):
        location = os.getenv("WOUND_MODEL_CONFIG", "").strip()
        if not location:
            return "not_configured", None, {}, None
        try:
            path = Path(location).expanduser().resolve()
            document = json.loads(path.read_bytes())
            if not isinstance(document, dict):
                raise ValueError("Invalid model configuration")
            if "profiles" in document:
                if set(document) - {"profiles", "default_model_id"}:
                    raise ValueError("Invalid profile configuration")
                profiles = document["profiles"]
                if not isinstance(profiles, dict) or not 1 <= len(profiles) <= 20:
                    raise ValueError("Invalid profiles")
                for key, profile in profiles.items():
                    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", key) is None or not isinstance(profile, dict):
                        raise ValueError("Invalid model profile")
                    if set(profile) - {"label", *STAGES} or not isinstance(profile.get("label", key), str):
                        raise ValueError("Invalid model profile fields")
                default_id = document.get("default_model_id", next(iter(profiles)))
                if default_id not in profiles:
                    raise ValueError("Invalid default model")
            else:
                if set(document) - set(STAGES):
                    raise ValueError("Invalid model configuration")
                profiles, default_id = {"default": document}, "default"
            return "configured", path, profiles, default_id
        except (OSError, ValueError, TypeError, RuntimeError):
            return "error", None, {}, None

    def selection(self, model_id=None):
        _, _, profiles, default_id = self._document()
        if profiles and model_id is not None and model_id not in profiles:
            raise InvalidModelSelection("Choose an available model.")
        selected = (model_id or default_id) if profiles else None
        return {"default_model_id": default_id, "selected_model_id": selected,
                "models": [{"id": key, "label": value.get("label", key)} for key, value in profiles.items()]}

    def _configuration(self, stage, model_id=None):
        state, path, profiles, default_id = self._document()
        if state != "configured":
            return state, None, None, None
        selected = model_id or default_id
        if selected not in profiles:
            raise InvalidModelSelection("Choose an available model.")
        try:
            entry = profiles[selected].get(stage)
            if entry is None:
                return "not_configured", None, None, selected
            if not isinstance(entry, dict) or set(entry) - {"adapter", "weights_path", "model_version", "parameters"}:
                raise ValueError("Invalid model entry")
            if not isinstance(entry.get("adapter"), str) or re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", entry["adapter"]) is None:
                raise ValueError("Invalid adapter factory")
            version = entry.get("model_version")
            if not isinstance(version, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,99}", version) is None:
                raise ValueError("Invalid model version")
            if not isinstance(entry.get("weights_path"), str) or not entry["weights_path"].strip():
                raise ValueError("Missing weights path")
            if not isinstance(entry.get("parameters", {}), dict):
                raise ValueError("Invalid adapter parameters")
            entry_digest = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
            weights = Path(entry["weights_path"]).expanduser()
            if not weights.is_absolute():
                weights = path.parent / weights
            entry = {**entry, "weights_path": weights.resolve()}
            stat = entry["weights_path"].stat() if entry["weights_path"].is_file() else None
            signature = (selected, stage, entry_digest, (stat.st_mtime_ns, stat.st_size) if stat else None)
            return ("configured" if stat else "weights_missing"), entry, signature, selected
        except (OSError, ValueError, TypeError, RuntimeError):
            return "error", None, None, selected

    def status(self, stage, model_id=None):
        # Availability checks must not wait on inference while holding a DB lock.
        status, entry, signature, _ = self._configuration(stage, model_id)
        if status == "configured":
            if signature in self._errors:
                status = "error"
            elif stage in self._loaded and self._loaded[stage][0] == signature:
                status = "ready"
        return {"status": status, "model_version": entry["model_version"] if entry else None}

    def statuses(self, model_id=None):
        return {**{stage: self.status(stage, model_id) for stage in STAGES},
                "healing_analysis": {"status": "awaiting_method", "model_version": None},
                **self.selection(model_id)}

    def _fingerprint(self, entry):
        digest = hashlib.sha256()
        with entry["weights_path"].open("rb") as weights:
            for block in iter(lambda: weights.read(1024 * 1024), b""):
                digest.update(block)
        weights_digest = digest.hexdigest()
        identity = json.dumps({"adapter": entry["adapter"], "model_version": entry["model_version"],
                               "parameters": entry.get("parameters", {}), "weights_sha256": weights_digest},
                              sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(identity.encode("utf-8")).hexdigest(), weights_digest

    def identity(self, stage, model_id=None):
        """Resolve current output identity without loading an inference adapter."""
        status, entry, _, selected = self._configuration(stage, model_id)
        if status != "configured":
            raise ModelUnavailable("This model is not available. Ask the server administrator to configure it.")
        try:
            return self._fingerprint(entry)[0], selected
        except OSError:
            raise ModelUnavailable("The model weights are unavailable. Ask the server administrator to check them.") from None

    def adapter(self, stage, model_id=None):
        """Factory executes only for a server configuration, under the stage lock."""
        with self.lock(stage):
            status, entry, signature, selected = self._configuration(stage, model_id)
            if status != "configured" or signature in self._errors:
                raise ModelUnavailable("This model is not available. Ask the server administrator to configure it.")
            try:
                fingerprint, weights_digest = self._fingerprint(entry)
            except OSError:
                raise ModelUnavailable("The model weights are unavailable. Ask the server administrator to check them.") from None
            loaded = self._loaded.get(stage)
            # Moving identical weights must update the adapter's file path while
            # retaining the content identity used by saved analysis results.
            if loaded is None or loaded[0] != signature or loaded[1] != fingerprint:
                try:
                    module_name, factory_name = entry["adapter"].split(":")
                    factory = getattr(importlib.import_module(module_name), factory_name)
                    adapter = factory(weights_path=entry["weights_path"], model_version=entry["model_version"], parameters=entry.get("parameters", {}))
                    if not callable(getattr(adapter, "predict", None)):
                        raise TypeError("Adapter must provide predict")
                    if getattr(adapter, "weights_sha256", weights_digest) != weights_digest:
                        raise ValueError("Checkpoint changed during adapter initialization")
                    # Retain only the current adapter per stage, bounding GPU copies.
                    self._loaded[stage] = (signature, fingerprint, adapter)
                    self._errors = {key for key in self._errors if key[1] != stage}
                except Exception:
                    self._errors.add(signature)
                    logger.exception("Could not initialize wound model adapter for %s", stage)
                    raise ModelUnavailable("This model could not be initialized. Ask the server administrator to check its configuration.") from None
            else:
                self._loaded[stage] = (signature, fingerprint, loaded[2])
            return self._loaded[stage][2], entry["model_version"], fingerprint, selected


registry = WoundModelRegistry()
