"""Exercise real configured models using synthetic images and temporary accounts.

Requires the model runtime plus requirements-dev.txt. Never reads clinic records
or photographs, and never writes to the normal account/clinic database.
"""

import argparse
import base64
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api import auth
from app.main import app


def expect(response, status=200):
    if response.status_code != status:
        raise RuntimeError(f"API check failed ({response.status_code}): {response.text}")
    return response.json()


def synthetic_fixtures():
    fixtures = []
    for index, visit_date in enumerate(("2026-10-21", "2026-10-22")):
        image = Image.new("RGB", (128, 96), (80, 110, 140))
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((12, 15, 115, 82), fill=(155, 115, 95))
        drawing.ellipse((43 + index * 4, 30 + index * 3, 88 - index * 4, 69 - index * 3), fill=(175, 65 + index * 15, 70))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        fixtures.append({"visit_date": visit_date, "bytes": buffer.getvalue(), "size": image.size})
    return fixtures


def check_progress(progress, fixtures, masks, model_id):
    if progress["model_id"] != model_id or progress["healing_percentage"] is not None:
        raise RuntimeError("Progress changed model selection or invented a healing percentage")
    if [point["visit_id"] for point in progress["points"]] != [fixture["visit_id"] for fixture in fixtures]:
        raise RuntimeError("Progress lost a visit or changed chronological order")
    tissue_keys = {1: "epithelialization", 2: "granulation", 3: "slough", 5: "necrosis", 6: "bone_tendon_muscle", 7: "other"}
    analyzed = 0
    for fixture, point in zip(fixtures, progress["points"]):
        if point["image_id"] != fixture["image_id"] or point["visit_date"] != fixture["visit_date"]:
            raise RuntimeError("Progress used an image from another visit")
        generated = masks[fixture["image_id"]]
        foreground = sum(pixel == 1 for pixel in generated["wound_segmentation"])
        if foreground == 0:
            if point["status"] != "no_wound" or point["percentages"] is not None:
                raise RuntimeError("An empty wound mask must not generate tissue percentages")
            continue
        analyzed += 1
        counts = {key: 0 for key in (*tissue_keys.values(), "unclassified")}
        for wound_pixel, tissue_pixel in zip(generated["wound_segmentation"], generated["tissue_segmentation"]):
            if wound_pixel == 1:
                counts[tissue_keys.get(tissue_pixel, "unclassified")] += 1
        percentages = point["percentages"]
        if point["status"] != "ready" or percentages is None or set(percentages) != set(counts):
            raise RuntimeError("Completed masks did not produce the expected tissue trend point")
        if abs(sum(percentages.values()) - 100.0) > 0.02:
            raise RuntimeError("Tissue proportions did not sum to 100 percent")
        for key, count in counts.items():
            if abs(percentages[key] - 100.0 * count / foreground) > 0.02:
                raise RuntimeError(f"Progress tissue proportion disagrees with saved masks: {key}")
    if progress["summary"] != {"visit_count": len(fixtures), "analyzed_visit_count": analyzed}:
        raise RuntimeError("Progress visit counts disagree with analyzed masks")
    expected_status = "ready" if analyzed == len(fixtures) else "partial" if analyzed else "pending"
    if progress["status"] != expected_status:
        raise RuntimeError("Progress availability does not match its visit points")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "wound-models.local.json")
    parser.add_argument("--reference-url", help="Optional existing prototype URL for exact numeric-mask comparison")
    args = parser.parse_args()
    if not args.config.is_file():
        parser.error("Configure the trained models and start their runtime first.")
    fixtures = synthetic_fixtures()
    checked = 0
    with tempfile.TemporaryDirectory(prefix="wound-model-smoke-") as temporary:
        directory = Path(temporary)
        env = {"WOUND_DATA_DIR": str(directory), "WOUND_DB_PATH": str(directory / "clinic.sqlite3"), "WOUND_MODEL_CONFIG": str(args.config.resolve())}
        with patch.dict(os.environ, env), patch.object(auth, "_users", None), patch.object(auth, "_local_db", directory / "accounts.sqlite3"), TestClient(app) as client:
            registration = expect(client.post("/api/auth/register", json={
                "email": "model-smoke@example.com", "password": "SyntheticModel2026!", "confirm_password": "SyntheticModel2026!",
                "name": "Synthetic Model Test", "username": "model_smoke", "phone": "0712345678", "is_diabetic": False,
            }))
            headers = {"Authorization": "Bearer " + registration["access_token"]}
            patient = expect(client.post("/api/wound/patients", headers=headers, json={"patient_code": "SYNTHETIC-MODEL-TEST", "display_name": "Synthetic fixture only"}), 201)
            wound = expect(client.post(f"/api/wound/patients/{patient['id']}/wounds", headers=headers, json={"label": "Synthetic model fixture", "location": "Synthetic drawing, no patient image"}), 201)
            for fixture in fixtures:
                visit = expect(client.post(f"/api/wound/wounds/{wound['id']}/visits", headers=headers, data={"visit_date": fixture["visit_date"]}, files=[("images", ("synthetic.png", fixture["bytes"], "image/png"))]), 201)
                fixture.update({"visit_id": visit["id"], "image_id": visit["images"][0]["id"]})
            models = expect(client.get("/api/wound/models", headers=headers))
            for model in models["models"]:
                model_id = model["id"]
                model_masks = {}
                for fixture in fixtures:
                    image_id = fixture["image_id"]
                    generated = {}
                    wound_run = None
                    for stage in ("wound_segmentation", "tissue_segmentation"):
                        run = expect(client.post(f"/api/wound/images/{image_id}/analysis", headers=headers, json={"stage": stage, "model_id": model_id}))
                        if run["status"] != "completed":
                            raise RuntimeError(f"{model_id}/{stage}: {run['status']}: {run.get('error')}")
                        if run["model_id"] != model_id:
                            raise RuntimeError("Model profile did not match the requested model")
                        if stage == "wound_segmentation":
                            wound_run = run["id"]
                        elif run["input_analysis_id"] != wound_run:
                            raise RuntimeError("Tissue run used a different wound-mask dependency")
                        artifact_url = f"/api/wound/analysis-artifacts/{run['artifacts'][0]['id']}"
                        artifact = client.get(artifact_url, headers=headers)
                        if artifact.status_code != 200 or client.get(artifact_url).status_code != 401:
                            raise RuntimeError("Private artifact access check failed")
                        with Image.open(io.BytesIO(artifact.content)) as mask:
                            mask.load()
                            if mask.size != fixture["size"] or mask.mode != "P":
                                raise RuntimeError("Output mask geometry or palette encoding changed")
                            generated[stage] = mask.tobytes()
                    model_masks[image_id] = generated
                    if args.reference_url:
                        reference = httpx.post(args.reference_url.rstrip("/") + "/api/wound/predict", data={"model_id": model_id}, files={"image": ("synthetic.png", fixture["bytes"], "image/png")}, timeout=180)
                        reference_result = expect(reference)
                        for stage, field in [("wound_segmentation", "wound_mask_data_url"), ("tissue_segmentation", "tissue_mask_data_url")]:
                            data = base64.b64decode(reference_result[field].split(",", 1)[1])
                            with Image.open(io.BytesIO(data)) as reference_mask:
                                if reference_mask.size != fixture["size"] or reference_mask.tobytes() != generated[stage]:
                                    raise RuntimeError(f"{model_id}/{stage} differs from the original inference implementation")
                progress = expect(client.get(f"/api/wound/wounds/{wound['id']}/progress", headers=headers, params={"model_id": model_id}))
                check_progress(progress, fixtures, model_masks, model_id)
                print(json.dumps({"model_id": model_id, "wound_segmentation": "completed", "tissue_segmentation": "completed", "visit_points": len(progress["points"]), "analyzed_visit_count": progress["summary"]["analyzed_visit_count"], "reference_match": True if args.reference_url else "not_requested"}), flush=True)
                checked += 1
            for fixture in fixtures:
                history = expect(client.get(f"/api/wound/images/{fixture['image_id']}/analysis", headers=headers))
                if len(history) != checked * 2:
                    raise RuntimeError("Model runs were not persisted separately")
    print(json.dumps({"models_checked": checked, "mask_runs": checked * 2 * len(fixtures), "visit_points_per_model": len(fixtures), "healing_percentage": None, "data": "temporary synthetic fixtures only"}), flush=True)


if __name__ == "__main__":
    main()
