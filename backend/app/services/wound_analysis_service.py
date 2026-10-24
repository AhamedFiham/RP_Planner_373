"""Run configured adapters and persist private, versioned segmentation masks."""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4
import warnings

from fastapi import HTTPException
from PIL import Image

from app.database.repositories import wound_repository as repository
from app.models.wound_registry import InvalidModelSelection, ModelUnavailable, registry
from app.services.wound_analysis_lock import RunLock
from app.services.wound_service import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS

logger = logging.getLogger(__name__)
MAX_MASK_BYTES = 32 * 1024 * 1024
ANALYSIS_FAILURE = "Analysis failed. No result was saved. Ask the server administrator to check the model and retry."
INTERRUPTED_FAILURE = "Analysis was interrupted before completion. Run the analysis again."


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def stored_path(directory, storage_name):
    directory = directory.resolve()
    path = (directory / storage_name).resolve()
    if not path.is_relative_to(directory) or not path.is_file():
        raise FileNotFoundError("Stored image or mask is unavailable")
    return path


def recover_interrupted(image_id, owner):
    """A released OS lock proves a running record has no live inference worker."""
    with repository.connection() as database:
        repository.require_image(database, image_id, owner)
        running = database.execute("SELECT id FROM wound_analyses WHERE image_id = ? AND status = 'running'", (image_id,)).fetchall()
    for row in running:
        lease = RunLock(row["id"])
        if not lease.acquired:
            continue
        try:
            with repository.connection() as database:
                database.execute(
                    "UPDATE wound_analyses SET status = 'failed', completed_at = ?, error = ? WHERE id = ? AND status = 'running'",
                    (timestamp(), INTERRUPTED_FAILURE, row["id"]),
                )
        finally:
            lease.close()


def _save_mask(source, image_path, target):
    """Preserve adapter labels/palette; require original pixel coordinates."""
    source = Path(source)
    if not source.is_file() or source.stat().st_size > MAX_MASK_BYTES:
        raise ValueError("Invalid model mask file")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(image_path) as original:
            expected_size = original.size
        with Image.open(source) as mask:
            width, height = mask.size
            if (mask.size != expected_size or width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION
                    or width * height > MAX_IMAGE_PIXELS or getattr(mask, "n_frames", 1) != 1
                    or mask.mode not in ("1", "L", "P", "I", "I;16", "RGB", "RGBA")):
                raise ValueError("Model must return a non-animated mask aligned to the original image")
            mask.load()
            if mask.mode == "I":
                minimum, maximum = mask.getextrema()
                if minimum < 0 or maximum > 65535:
                    raise ValueError("Integer mask labels must fit lossless 16-bit PNG")
                mask = mask.convert("I;16")
            clean = Image.new(mask.mode, mask.size)
            clean.paste(mask)
            if mask.mode == "P":
                clean.putpalette(mask.getpalette())
            if "transparency" in mask.info:
                clean.info["transparency"] = mask.info["transparency"]
            clean.save(target, format="PNG")
    if target.stat().st_size > MAX_MASK_BYTES:
        raise ValueError("Generated mask exceeds storage limits")


def analyze_image(image_id, stage, owner, model_id=None):
    # Authorize before exposing model availability or initializing an adapter.
    recover_interrupted(image_id, owner)
    with registry.lock(stage):
        try:
            adapter, version, fingerprint, selected = registry.adapter(stage, model_id)
            wound_fingerprint = registry.identity("wound_segmentation", selected)[0] if stage == "tissue_segmentation" else None
        except InvalidModelSelection as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        except ModelUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from None
        run_id = str(uuid4())
        # Held before inserting "running"; OS release allows safe crash recovery.
        with RunLock(run_id):
            return _run_analysis(image_id, stage, owner, adapter, version, fingerprint, selected, run_id, wound_fingerprint)


def _run_analysis(image_id, stage, owner, adapter, version, fingerprint, model_id, run_id, wound_fingerprint):
    input_analysis_id = None
    try:
        with repository.connection() as database:
            database.execute("BEGIN IMMEDIATE")
            image = repository.require_image(database, image_id, owner)
            try:
                image_path = stored_path(repository.image_directory(), image["storage_name"])
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Image not found.") from None
            dependency_path = None
            if stage == "tissue_segmentation":
                # Pin the latest completed wound mask for THIS image and model.
                dependency = database.execute(
                    """SELECT a.id, f.storage_name FROM wound_analyses a
                       JOIN wound_analysis_artifacts f ON f.analysis_id = a.id AND f.kind = 'mask'
                       WHERE a.image_id = ? AND a.model_id = ? AND a.model_fingerprint = ?
                         AND a.stage = 'wound_segmentation' AND a.status = 'completed'
                       ORDER BY a.created_at DESC, a.rowid DESC LIMIT 1""", (image_id, model_id, wound_fingerprint),
                ).fetchone()
                if dependency is None:
                    raise HTTPException(status_code=409, detail="Run wound segmentation for this image with the current model before tissue segmentation.")
                try:
                    dependency_path = stored_path(repository.artifact_directory(), dependency["storage_name"])
                except FileNotFoundError:
                    raise HTTPException(status_code=409, detail="The saved wound mask is unavailable. Run wound segmentation again.") from None
                input_analysis_id = dependency["id"]

            cached = database.execute(
                """SELECT * FROM wound_analyses WHERE image_id = ? AND stage = ? AND model_id = ?
                   AND model_fingerprint = ? AND input_analysis_id IS ? AND status = 'completed'
                   ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                (image_id, stage, model_id, fingerprint, input_analysis_id),
            ).fetchone()
            if cached:
                artifacts = database.execute("SELECT storage_name FROM wound_analysis_artifacts WHERE analysis_id = ?", (cached["id"],)).fetchall()
                try:
                    if artifacts:
                        for artifact in artifacts:
                            stored_path(repository.artifact_directory(), artifact["storage_name"])
                        return repository.analysis_record(database, cached)
                except FileNotFoundError:
                    pass
            database.execute(
                """INSERT INTO wound_analyses (id, image_id, model_id, stage, status, model_version, model_fingerprint, created_at, input_analysis_id)
                   VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?)""",
                (run_id, image_id, model_id, stage, version, fingerprint, timestamp(), input_analysis_id),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Analysis is already running for this image and model stage.") from None

    artifact_id = str(uuid4())
    directory = repository.artifact_directory()
    target = directory / (artifact_id + ".png")
    temporary = None
    result = None
    try:
        result = adapter.predict(image_path) if stage == "wound_segmentation" else adapter.predict(image_path, dependency_path)
        if result.model_version != version:
            raise ValueError("Adapter result model version does not match configuration")
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="mask-", suffix=".tmp", dir=directory, delete=False) as file:
            temporary = Path(file.name)
        _save_mask(result.mask_path, image_path, temporary)
        os.replace(temporary, target)
        temporary = None
        with repository.connection() as database:
            database.execute("INSERT INTO wound_analysis_artifacts VALUES (?, ?, 'mask', 'image/png', ?)", (artifact_id, run_id, target.name))
            database.execute("UPDATE wound_analyses SET status = 'completed', completed_at = ? WHERE id = ?", (timestamp(), run_id))
            return repository.analysis_record(database, database.execute("SELECT * FROM wound_analyses WHERE id = ?", (run_id,)).fetchone())
    except Exception:
        logger.exception("Wound analysis failed for run %s", run_id)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        with repository.connection() as database:
            database.execute("UPDATE wound_analyses SET status = 'failed', completed_at = ?, error = ? WHERE id = ?", (timestamp(), ANALYSIS_FAILURE, run_id))
            return repository.analysis_record(database, database.execute("SELECT * FROM wound_analyses WHERE id = ?", (run_id,)).fetchone())
    finally:
        release = getattr(adapter, "release", None)
        if result is not None and callable(release):
            try:
                release(result)
            except Exception:
                logger.exception("Could not release temporary adapter output for run %s", run_id)
