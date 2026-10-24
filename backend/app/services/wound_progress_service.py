"""Tissue composition within paired wound masks, without a healing score.

One explicitly selected image represents each visit. Mask labels and checkpoint
identity must be known; missing or incompatible data remains a gap in the series.
"""

import warnings

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from app.database.repositories import wound_repository as repository
from app.models.wound_registry import InvalidModelSelection, ModelUnavailable, registry
from app.models.prototype_adapter import MODEL_IDS
from app.services.wound_analysis_service import MAX_MASK_BYTES, stored_path
from app.services.wound_service import MAX_IMAGE_DIMENSION, MAX_IMAGE_PIXELS

TISSUES = [
    {"id": 1, "key": "epithelialization", "label": "Epithelialization", "color": "#ff66cc"},
    {"id": 2, "key": "granulation", "label": "Granulation", "color": "#ff0000"},
    {"id": 3, "key": "slough", "label": "Slough", "color": "#808080"},
    {"id": 5, "key": "necrosis", "label": "Necrosis", "color": "#8b4513"},
    {"id": 6, "key": "bone_tendon_muscle", "label": "Bone / tendon / muscle", "color": "#00ffff"},
    {"id": 7, "key": "other", "label": "Other", "color": "#00b050"},
    {"id": 0, "key": "unclassified", "label": "Unclassified", "color": "#64748b"},
]
_TISSUE_IDS = {item["id"] for item in TISSUES}


def select_progress_image(visit_id, image_id, owner):
    with repository.connection() as database:
        database.execute("BEGIN IMMEDIATE")
        visit = database.execute(
            """SELECT v.id FROM wound_visits v JOIN clinic_wounds w ON w.id = v.wound_id
               JOIN wound_patients p ON p.id = w.patient_id WHERE v.id = ? AND p.owner = ?""",
            (visit_id, owner),
        ).fetchone()
        if visit is None:
            raise HTTPException(status_code=404, detail="Visit not found.")
        image = database.execute("SELECT id FROM wound_images WHERE id = ? AND visit_id = ?", (image_id, visit_id)).fetchone()
        if image is None:
            raise HTTPException(status_code=404, detail="Image not found in this visit.")
        database.execute("UPDATE wound_visits SET progress_image_id = ? WHERE id = ?", (image_id, visit_id))
    return {"visit_id": visit_id, "image_id": image_id}


def _context(model_id):
    """Inspect server configuration and hashes only; never load a model/runtime."""
    selection = registry.selection(model_id)
    selected = selection["selected_model_id"]
    entries = {}
    for stage, factory in (("wound_segmentation", "build_wound_adapter"), ("tissue_segmentation", "build_tissue_adapter")):
        state, entry, _, _ = registry._configuration(stage, selected)
        if state != "configured":
            return selected, None, "The selected model is unavailable. Configure its checkpoints to compare visits."
        if (entry["adapter"] != "app.models.prototype_adapter:" + factory
                or entry.get("parameters", {}).get("model_id") not in MODEL_IDS):
            return selected, None, "Tissue trends are unavailable because this model's numeric tissue labels are not defined."
        entries[stage] = entry
    if entries["wound_segmentation"]["parameters"]["model_id"] != entries["tissue_segmentation"]["parameters"]["model_id"]:
        return selected, None, "The wound and tissue models do not use the same label definition."
    try:
        fingerprints = {stage: registry.identity(stage, selected)[0] for stage in entries}
    except ModelUnavailable:
        return selected, None, "The selected model checkpoints are unavailable."
    return selected, fingerprints, None


def _numeric_mask(path, allowed):
    if path.stat().st_size > MAX_MASK_BYTES:
        raise ValueError("Mask exceeds the limit")
    with Image.open(path) as mask:
        width, height = mask.size
        if (mask.format != "PNG" or mask.mode not in ("L", "P") or getattr(mask, "n_frames", 1) != 1
                or width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION or width * height > MAX_IMAGE_PIXELS):
            raise ValueError("Unsupported numeric mask")
        mask.load()
        labels = mask.getcolors(maxcolors=256)
        if labels is None or any(label not in allowed for _, label in labels):
            raise ValueError("Unknown mask labels")
        # P-mode convert('L') maps palette colours; preserve label bytes instead.
        return Image.frombytes("L", mask.size, mask.tobytes())


def mask_percentages(wound_path, tissue_path):
    """All foreground wound pixels form the denominator, including tissue ID 0."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with _numeric_mask(wound_path, {0, 1}) as wound, _numeric_mask(tissue_path, _TISSUE_IDS) as tissue:
            if wound.size != tissue.size:
                raise ValueError("Masks are not aligned")
            denominator = wound.histogram()[1]
            if denominator == 0:
                return None
            with wound.point(lambda value: 255 if value == 1 else 0) as foreground:
                counts = tissue.histogram(mask=foreground)
            return {item["key"]: 100 * counts[item["id"]] / denominator for item in TISSUES}


def _latest(database, image_id, stage, model_id, fingerprint):
    return database.execute(
        """SELECT * FROM wound_analyses WHERE image_id = ? AND stage = ? AND model_id = ?
           AND model_fingerprint = ? ORDER BY created_at DESC, rowid DESC LIMIT 1""",
        (image_id, stage, model_id, fingerprint),
    ).fetchone()


def _artifact(database, run_id):
    row = database.execute(
        "SELECT id, storage_name FROM wound_analysis_artifacts WHERE analysis_id = ? AND kind = 'mask' ORDER BY rowid DESC LIMIT 1",
        (run_id,),
    ).fetchone()
    if row is None:
        raise FileNotFoundError("No mask")
    return row["id"], stored_path(repository.artifact_directory(), row["storage_name"])


def _point(database, visit, images, selected, fingerprints, context_error):
    image_ids = {image["id"] for image in images}
    image_id = visit["progress_image_id"] if visit["progress_image_id"] in image_ids else (images[0]["id"] if images else None)
    point = {"visit_id": visit["id"], "visit_date": visit["visit_date"], "image_id": image_id,
             "images": images, "status": "pending", "reason": None, "percentages": None, "analysis": None}
    if context_error:
        point.update(status="unavailable", reason=context_error)
        return point
    if image_id is None:
        point["reason"] = "Upload an image for this visit."
        return point
    wound = _latest(database, image_id, "wound_segmentation", selected, fingerprints["wound_segmentation"])
    tissue = _latest(database, image_id, "tissue_segmentation", selected, fingerprints["tissue_segmentation"])
    for run, name in ((wound, "wound"), (tissue, "tissue")):
        if run is None:
            point["reason"] = f"Run {name} segmentation for this image with the current selected model."
            return point
        if run["status"] != "completed":
            point["status"] = "failed" if run["status"] == "failed" else "pending"
            point["reason"] = f"The {name} segmentation failed. Run it again." if run["status"] == "failed" else f"The {name} segmentation is still running."
            return point
    if tissue["input_analysis_id"] != wound["id"]:
        point["reason"] = "Run tissue segmentation again to use the current wound mask."
        return point
    try:
        wound_artifact, wound_path = _artifact(database, wound["id"])
        tissue_artifact, tissue_path = _artifact(database, tissue["id"])
        percentages = mask_percentages(wound_path, tissue_path)
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        point.update(status="unavailable", reason="The saved masks are missing, unreadable, or do not contain compatible numeric labels. Run segmentation again.")
        return point
    point["analysis"] = {
        "wound": {"id": wound["id"], "model_version": wound["model_version"], "artifact_id": wound_artifact},
        "tissue": {"id": tissue["id"], "model_version": tissue["model_version"], "artifact_id": tissue_artifact},
    }
    if percentages is None:
        point.update(status="no_wound", reason="No wound foreground was detected. Tissue proportions cannot be calculated; this does not establish healing.")
    else:
        point.update(status="ready", percentages=percentages)
    return point


def progress_for_wound(wound_id, owner, model_id=None):
    with repository.connection() as database:
        # Authorization comes before resolving configuration, hashes, or masks.
        repository.require_wound(database, wound_id, owner)
        try:
            selected, fingerprints, context_error = _context(model_id)
        except InvalidModelSelection as error:
            raise HTTPException(status_code=400, detail=str(error)) from None
        visits = database.execute("SELECT * FROM wound_visits WHERE wound_id = ? ORDER BY visit_date, created_at, id", (wound_id,)).fetchall()
        points = []
        for visit in visits:
            images = [dict(row) for row in database.execute("SELECT id, filename FROM wound_images WHERE visit_id = ? ORDER BY rowid", (visit["id"],))]
            points.append(_point(database, visit, images, selected, fingerprints, context_error))
    analyzed = sum(point["status"] == "ready" for point in points)
    return {"status": "ready" if points and analyzed == len(points) else "partial" if analyzed else "pending",
            "model_id": selected, "tissues": TISSUES, "points": points,
            "summary": {"visit_count": len(points), "analyzed_visit_count": analyzed}, "healing_percentage": None}
