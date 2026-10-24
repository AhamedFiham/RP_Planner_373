"""Mask-derived tissue trends against isolated records and numeric PNG fixtures."""

import io
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from PIL import Image

from app.database.repositories import wound_repository as repository
from app.models.wound_registry import registry
from app.services.wound_progress_service import TISSUES
import test_wound_clinic as clinic_tests


class WoundProgressTests(unittest.TestCase):
    headers_for = clinic_tests.ClinicApiTests.headers_for
    patient = clinic_tests.ClinicApiTests.patient
    wound = clinic_tests.ClinicApiTests.wound
    visit = clinic_tests.ClinicApiTests.visit

    def setUp(self):
        clinic_tests.ClinicApiTests.setUp(self)
        self.root = Path(self.directory.name)
        self.weights = self.root / "fixture.pt"
        self.weights.write_bytes(b"Only identity is read; inference must not run")
        self.config = self.root / "models.json"
        self.document = {"default_model_id": "model_a", "profiles": {}}
        for name, actual in (("model_a", "unet_resnet18"), ("model_b", "segformer_mit_b0")):
            self.document["profiles"][name] = {"label": name}
            for stage, factory in (("wound_segmentation", "build_wound_adapter"), ("tissue_segmentation", "build_tissue_adapter")):
                self.document["profiles"][name][stage] = {
                    "adapter": "app.models.prototype_adapter:" + factory,
                    "weights_path": str(self.weights), "model_version": "fixture-v1",
                    "parameters": {"model_id": actual},
                }
        self.save_config()
        os.environ["WOUND_MODEL_CONFIG"] = str(self.config)
        self.no_inference = patch.object(registry, "adapter", side_effect=AssertionError("Trends must not initialize inference"))
        self.no_inference.start()

    def tearDown(self):
        self.no_inference.stop()
        clinic_tests.ClinicApiTests.tearDown(self)

    def save_config(self):
        self.config.write_text(json.dumps(self.document), encoding="utf-8")

    def uploaded(self, wound, day="2026-10-01", count=1):
        response = self.client.post(
            f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers, data={"visit_date": day},
            files=[("images", (f"image-{index}.png", clinic_tests.image_bytes(), "image/png")) for index in range(count)],
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def add_run(self, image_id, stage, values=None, *, model_id="model_a", dependency=None, status="completed", mode="P", size=(12, 10), fingerprint=None):
        run_id = str(uuid4())
        if fingerprint is None:
            fingerprint = registry.identity(stage, model_id)[0]
        with repository.connection() as database:
            database.execute(
                """INSERT INTO wound_analyses (id,image_id,model_id,stage,status,model_version,model_fingerprint,created_at,input_analysis_id)
                   VALUES (?,?,?,?,?,'fixture-v1',?,'2026-10-21T12:00:00Z',?)""",
                (run_id, image_id, model_id, stage, status, fingerprint, dependency),
            )
            if values is not None:
                artifact_id = str(uuid4())
                path = repository.artifact_directory() / (artifact_id + ".png")
                path.parent.mkdir(parents=True, exist_ok=True)
                image = Image.new(mode, size)
                if mode == "P":
                    # Palette colours deliberately differ from numeric IDs.
                    image.putpalette([channel for i in range(256) for channel in (255 - i, i, 255)])
                image.putdata(values)
                image.save(path, format="PNG")
                database.execute("INSERT INTO wound_analysis_artifacts VALUES (?,?,'mask','image/png',?)", (artifact_id, run_id, path.name))
        return run_id

    def pair(self, image_id, *, model_id="model_a", wound=None, tissue=None, mode="P", tissue_size=(12, 10)):
        wound_run = self.add_run(image_id, "wound_segmentation", wound if wound is not None else [1] * 120, model_id=model_id)
        tissue_run = self.add_run(image_id, "tissue_segmentation", tissue if tissue is not None else [2] * (tissue_size[0] * tissue_size[1]),
                              model_id=model_id, dependency=wound_run, mode=mode, size=tissue_size)
        return wound_run, tissue_run

    def progress(self, wound, model="model_a", headers=None):
        return self.client.get(f"/api/wound/wounds/{wound['id']}/progress", params={"model_id": model} if model else {}, headers=headers or self.headers)

    def expected_analysis(self, runs):
        with repository.connection() as database:
            return {stage: {"id": run_id, "model_version": "fixture-v1", "artifact_id": database.execute(
                "SELECT id FROM wound_analysis_artifacts WHERE analysis_id=?", (run_id,),
            ).fetchone()[0]} for stage, run_id in zip(("wound", "tissue"), runs)}

    def test_percentages_use_wound_pixels_and_palette_indices_not_colours(self):
        wound = self.wound()
        visit = self.uploaded(wound)
        # Eight wound pixels; most tissue predictions are outside the wound.
        self.pair(visit["images"][0]["id"], wound=[1] * 8 + [0] * 112,
                  tissue=[1, 2, 2, 3, 5, 6, 7, 0] + [3] * 112)
        result = self.progress(wound).json()
        self.assertEqual(result["status"], "ready")
        point = result["points"][0]
        self.assertEqual(point["status"], "ready")
        self.assertEqual(point["percentages"], {"epithelialization": 12.5, "granulation": 25.0, "slough": 12.5,
                                              "necrosis": 12.5, "bone_tendon_muscle": 12.5, "other": 12.5, "unclassified": 12.5})
        self.assertEqual(sum(point["percentages"].values()), 100)
        self.assertEqual(result["summary"], {"visit_count": 1, "analyzed_visit_count": 1})
        self.assertIsNone(result["healing_percentage"])
        self.assertEqual(result["tissues"], TISSUES)
        for secret in (self.directory.name, "model_fingerprint", "storage_name", "wound_pixels", "area_cm2"):
            self.assertNotIn(secret, json.dumps(result))

    def test_all_dates_remain_with_null_gaps_and_empty_wound_is_pending(self):
        wound = self.wound()
        empty = self.progress(wound).json()
        self.assertEqual((empty["status"], empty["points"]), ("pending", []))
        later = self.uploaded(wound, "2026-10-14")
        first = self.uploaded(wound, "2026-10-01")
        middle = self.uploaded(wound, "2026-10-07")
        self.pair(first["images"][0]["id"])
        self.pair(later["images"][0]["id"], tissue=[3] * 120)
        result = self.progress(wound).json()
        self.assertEqual(result["status"], "partial")
        self.assertEqual([point["visit_date"] for point in result["points"]], ["2026-10-01", "2026-10-07", "2026-10-14"])
        self.assertEqual([point["status"] for point in result["points"]], ["ready", "pending", "ready"])
        self.assertIsNone(result["points"][1]["percentages"])
        self.assertIsNone(result["points"][1]["analysis"])
        self.assertEqual(result["points"][1]["visit_id"], middle["id"])
        self.assertEqual(result["summary"]["analyzed_visit_count"], 2)

    def test_comparison_metadata_uses_only_selected_image_model_and_owned_artifacts(self):
        wound = self.wound()
        first = self.uploaded(wound, count=2)
        later = self.uploaded(wound, "2026-10-07")
        image_a, image_b = [image["id"] for image in first["images"]]
        first_runs = self.pair(image_a)
        alternate_runs = self.pair(image_b)
        other_model_runs = self.pair(image_a, model_id="model_b")
        later_runs = self.pair(later["images"][0]["id"])
        points = self.progress(wound).json()["points"]
        self.assertEqual(points[0]["analysis"], self.expected_analysis(first_runs))
        self.assertEqual(points[1]["analysis"], self.expected_analysis(later_runs))
        model_b = self.progress(wound, "model_b").json()["points"]
        self.assertEqual(model_b[0]["analysis"], self.expected_analysis(other_model_runs))
        self.assertIsNone(model_b[1]["analysis"])
        chosen = self.client.patch(f"/api/wound/visits/{first['id']}/progress-image", headers=self.headers, json={"image_id": image_b})
        self.assertEqual(chosen.status_code, 200)
        selected = self.progress(wound).json()["points"][0]
        self.assertEqual(selected["analysis"], self.expected_analysis(alternate_runs))
        for stage in selected["analysis"].values():
            endpoint = f"/api/wound/analysis-artifacts/{stage['artifact_id']}"
            self.assertEqual(self.client.get(endpoint).status_code, 401)
            self.assertEqual(self.client.get(endpoint, headers=self.other_headers).status_code, 404)
            response = self.client.get(endpoint, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "image/png")

    def test_representative_image_is_explicit_persistent_and_same_owned_visit(self):
        wound = self.wound()
        first = self.uploaded(wound, count=2)
        second = self.uploaded(wound, "2026-10-07")
        image_a, image_b = [image["id"] for image in first["images"]]
        self.pair(image_b)
        result = self.progress(wound).json()["points"][0]
        self.assertEqual((result["image_id"], result["status"]), (image_a, "pending"))
        self.assertIsNone(result["analysis"])
        endpoint = f"/api/wound/visits/{first['id']}/progress-image"
        self.assertEqual(self.client.patch(endpoint, json={"image_id": image_b}).status_code, 401)
        self.assertEqual(self.client.patch(endpoint, headers=self.other_headers, json={"image_id": image_b}).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, headers=self.headers, json={"image_id": second["images"][0]["id"]}).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, headers=self.headers, json={"image_id": image_b, "unknown": True}).status_code, 422)
        chosen = self.client.patch(endpoint, headers=self.headers, json={"image_id": image_b})
        self.assertEqual(chosen.status_code, 200, chosen.text)
        self.assertEqual(chosen.json(), {"visit_id": first["id"], "image_id": image_b})
        self.assertEqual(self.progress(wound).json()["points"][0]["status"], "ready")
        with repository.connection() as database:
            self.assertEqual(database.execute("SELECT progress_image_id FROM wound_visits WHERE id=?", (first["id"],)).fetchone()[0], image_b)
        listed = self.client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json()
        self.assertEqual(listed[0]["progress_image_id"], image_b)

    def test_profiles_checkpoint_and_preprocessing_changes_never_reuse_old_metrics(self):
        wound = self.wound()
        image = self.uploaded(wound)["images"][0]["id"]
        self.pair(image)
        self.assertEqual(self.progress(wound, "model_a").json()["points"][0]["status"], "ready")
        self.assertEqual(self.progress(wound, "model_b").json()["points"][0]["status"], "pending")
        self.assertEqual(self.progress(wound, "unknown").status_code, 400)
        self.weights.write_bytes(b"New checkpoint with the same version label")
        self.assertEqual(self.progress(wound).json()["points"][0]["status"], "pending")
        self.pair(image)
        self.assertEqual(self.progress(wound).json()["points"][0]["status"], "ready")
        self.document["profiles"]["model_a"]["tissue_segmentation"]["parameters"]["changed_preprocessing"] = True
        self.save_config()
        point = self.progress(wound).json()["points"][0]
        self.assertEqual(point["status"], "pending")
        self.assertIsNone(point["percentages"])
        self.assertIsNone(point["analysis"])

    def test_latest_failed_running_and_new_wound_dependency_are_gaps(self):
        wound = self.wound()
        image = self.uploaded(wound)["images"][0]["id"]
        first_wound, _ = self.pair(image)
        current_wound = self.add_run(image, "wound_segmentation", [1] * 120)
        point = self.progress(wound).json()["points"][0]
        self.assertEqual(point["status"], "pending")
        self.assertIn("current wound mask", point["reason"])
        self.assertIsNone(point["analysis"])
        self.add_run(image, "tissue_segmentation", [2] * 120, dependency=current_wound)
        self.assertEqual(self.progress(wound).json()["points"][0]["status"], "ready")
        self.add_run(image, "tissue_segmentation", status="failed", dependency=current_wound)
        self.assertEqual(self.progress(wound).json()["points"][0]["status"], "failed")
        self.add_run(image, "tissue_segmentation", status="running", dependency=current_wound)
        self.assertEqual(self.progress(wound).json()["points"][0]["status"], "pending")

    def test_invalid_or_missing_masks_are_unavailable_without_leaking_paths(self):
        wound = self.wound()
        for index, kind in enumerate(("rgb", "fibrin", "unknown", "geometry", "missing", "corrupt", "traversal")):
            with self.subTest(kind=kind):
                image = self.uploaded(wound, f"2026-10-{index + 1:02d}")["images"][0]["id"]
                values = [(255, 0, 0)] * 120 if kind == "rgb" else [4 if kind == "fibrin" else 255 if kind == "unknown" else 2] * 120
                _, tissue_run = self.pair(image, tissue=values, mode="RGB" if kind == "rgb" else "P", tissue_size=(10, 12) if kind == "geometry" else (12, 10))
                with repository.connection() as database:
                    artifact = database.execute("SELECT id,storage_name FROM wound_analysis_artifacts WHERE analysis_id=?", (tissue_run,)).fetchone()
                    path = repository.artifact_directory() / artifact["storage_name"]
                    if kind == "missing":
                        path.unlink()
                    elif kind == "corrupt":
                        path.write_bytes(b"Private corrupted mask")
                    elif kind == "traversal":
                        database.execute("UPDATE wound_analysis_artifacts SET storage_name='../clinic.sqlite3' WHERE id=?", (artifact["id"],))
                point = self.progress(wound).json()["points"][index]
                self.assertEqual(point["status"], "unavailable")
                self.assertIsNone(point["percentages"])
                self.assertIsNone(point["analysis"])
                self.assertNotIn(self.directory.name, point["reason"])
                self.assertNotIn("clinic.sqlite3", point["reason"])

    def test_zero_wound_is_not_reported_as_healed_or_zero_tissue_percentages(self):
        wound = self.wound()
        image = self.uploaded(wound)["images"][0]["id"]
        runs = self.pair(image, wound=[0] * 120)
        result = self.progress(wound).json()
        self.assertEqual(result["points"][0]["status"], "no_wound")
        self.assertIsNone(result["points"][0]["percentages"])
        self.assertEqual(result["points"][0]["analysis"], self.expected_analysis(runs))
        self.assertIsNone(result["healing_percentage"])
        self.assertIn("does not establish healing", result["points"][0]["reason"])

    def test_authorization_precedes_config_or_mask_access(self):
        wound = self.wound()
        self.uploaded(wound)
        endpoint = f"/api/wound/wounds/{wound['id']}/progress?model_id=unknown"
        with patch.object(registry, "identity", side_effect=AssertionError("Unauthorized model access")) as identity:
            self.assertEqual(self.client.get(endpoint).status_code, 401)
            self.assertEqual(self.client.get(endpoint, headers=self.other_headers).status_code, 404)
            identity.assert_not_called()

    def test_unknown_ontology_and_missing_config_remain_unavailable(self):
        wound = self.wound()
        image = self.uploaded(wound)["images"][0]["id"]
        self.pair(image)
        self.document["profiles"]["model_a"]["tissue_segmentation"]["adapter"] = "custom.module:factory"
        self.save_config()
        result = self.progress(wound).json()
        self.assertEqual(result["points"][0]["status"], "unavailable")
        self.assertIn("labels are not defined", result["points"][0]["reason"])
        os.environ["WOUND_MODEL_CONFIG"] = ""
        result = self.progress(wound, model=None).json()
        self.assertIsNone(result["model_id"])
        self.assertEqual(result["points"][0]["status"], "unavailable")
        self.assertIsNone(result["points"][0]["percentages"])

    def test_existing_visit_storage_is_migrated_without_losing_records(self):
        legacy_path = self.root / "legacy.sqlite3"
        legacy = sqlite3.connect(legacy_path)
        try:
            legacy.executescript(repository.SCHEMA.replace("    progress_image_id TEXT REFERENCES wound_images(id),\n", ""))
            legacy.execute("INSERT INTO wound_patients VALUES ('p','clinic-a@example.com','P','p','Patient','','2026-10-01')")
            legacy.execute("INSERT INTO clinic_wounds VALUES ('w','p','Wound','Foot',NULL,'active','','2026-10-01')")
            legacy.execute("INSERT INTO wound_visits VALUES ('v','w','2026-10-01','','2026-10-01')")
            legacy.execute("INSERT INTO wound_images VALUES ('i','v','image.png','image.png','image/png',10)")
            legacy.commit()
        finally:
            legacy.close()
        with patch.dict(os.environ, {"WOUND_DB_PATH": str(legacy_path)}):
            with repository.connection() as database:
                stored = database.execute("SELECT * FROM wound_visits WHERE id='v'").fetchone()
                self.assertIsNone(stored["progress_image_id"])
                self.assertEqual(stored["visit_date"], "2026-10-01")
                listed = repository.list_visits(database, "w")
                self.assertEqual(listed[0]["progress_image_id"], "i")
                self.assertEqual(len(listed[0]["images"]), 1)


if __name__ == "__main__":
    unittest.main()
