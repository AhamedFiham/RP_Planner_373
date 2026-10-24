"""Real storage/API tests with isolated deterministic adapter fixtures, no .pt files."""

import io
import json
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from app.database.repositories import wound_repository as repository
from app.models.wound_registry import registry
from app.services.wound_analysis_lock import RunLock
from uuid import uuid4
import test_wound_clinic as clinic_tests


class WoundAnalysisTests(unittest.TestCase):
    headers_for = clinic_tests.ClinicApiTests.headers_for
    patient = clinic_tests.ClinicApiTests.patient
    wound = clinic_tests.ClinicApiTests.wound
    visit = clinic_tests.ClinicApiTests.visit

    def setUp(self):
        clinic_tests.ClinicApiTests.setUp(self)
        self.config_env = patch.dict(os.environ, {"WOUND_MODEL_CONFIG": ""})
        self.config_env.start()
        registry._loaded.clear()
        registry._errors.clear()
        self.factory_calls = []
        self.predict_calls = []
        self.result_size = (12, 10)
        self.result_version = None
        self.invalid_output = False
        self.adapter_module = ModuleType("synthetic_wound_test_adapter")
        self.adapter_module.create = self.factory
        self.module_patch = patch.dict(sys.modules, {"synthetic_wound_test_adapter": self.adapter_module})
        self.module_patch.start()

    def tearDown(self):
        registry._loaded.clear()
        registry._errors.clear()
        self.module_patch.stop()
        self.config_env.stop()
        clinic_tests.ClinicApiTests.tearDown(self)

    def factory(self, *, weights_path, model_version, parameters):
        self.factory_calls.append((weights_path, model_version, parameters))

        def predict(image_path, wound_mask=None):
            self.predict_calls.append((image_path, wound_mask))
            output = Path(self.directory.name) / ("fixture-output-" + str(len(self.predict_calls)) + ".png")
            if self.invalid_output:
                output.write_bytes(b"not a mask: private-model-path")
            else:
                Image.new("L", self.result_size, 7).save(output)
            return SimpleNamespace(mask_path=output, model_version=self.result_version or model_version)

        return SimpleNamespace(predict=predict)

    def configure(self, stages=("wound_segmentation", "tissue_segmentation"), *, weights_exist=True, version="test-v1"):
        weights = Path(self.directory.name) / "fixture-model.pt"
        if weights_exist:
            weights.write_bytes(b"Test factory does not load PyTorch")
        config = {stage: {"adapter": "synthetic_wound_test_adapter:create", "weights_path": weights.name,
                          "model_version": version, "parameters": {"fixture": True}} for stage in stages}
        path = Path(self.directory.name) / "models.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        os.environ["WOUND_MODEL_CONFIG"] = str(path)
        return path

    def uploaded_image(self, wound=None, date="2026-10-01"):
        result = self.visit(wound or self.wound(), date)
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()["images"][0]["id"]

    def analyze(self, image_id, stage="wound_segmentation", headers=None, **extra):
        return self.client.post(f"/api/wound/images/{image_id}/analysis", headers=headers or self.headers,
                                json={"stage": stage, **extra})

    def test_relocated_identical_checkpoint_updates_adapter_and_preserves_results(self):
        config_path = self.configure()
        image_id = self.uploaded_image()
        first = self.analyze(image_id).json()
        previous_identity = registry.identity("wound_segmentation")[0]
        config = json.loads(config_path.read_text())
        previous_weights = Path(self.directory.name) / config["wound_segmentation"]["weights_path"]
        relocated = Path(self.directory.name) / "relocated" / "fixture-model.pt"
        relocated.parent.mkdir()
        relocated.write_bytes(previous_weights.read_bytes())
        config["wound_segmentation"]["weights_path"] = relocated.relative_to(self.directory.name).as_posix()
        config_path.write_text(json.dumps(config))

        self.assertEqual(registry.identity("wound_segmentation")[0], previous_identity)
        cached = self.analyze(image_id).json()
        self.assertEqual(cached["id"], first["id"])
        self.assertEqual(len(self.factory_calls), 2)
        self.assertEqual(self.factory_calls[-1][0], relocated.resolve())
        self.assertEqual(len(self.predict_calls), 1)

    def test_missing_models_leave_no_analysis_or_artifacts(self):
        image_id = self.uploaded_image()
        response = self.client.get("/api/wound/models", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["wound_segmentation"], {"status": "not_configured", "model_version": None})
        self.assertEqual(response.json()["healing_analysis"]["status"], "awaiting_method")
        self.assertEqual(self.analyze(image_id).status_code, 503)
        with repository.connection() as database:
            self.assertEqual(database.execute("SELECT COUNT(*) FROM wound_analyses").fetchone()[0], 0)
        self.assertFalse(repository.artifact_directory().exists())
        self.configure(weights_exist=False)
        self.assertEqual(self.client.get("/api/wound/models", headers=self.headers).json()["wound_segmentation"]["status"], "weights_missing")
        self.assertEqual(self.analyze(image_id).status_code, 503)

    def test_success_persistence_private_mask_lazy_load_and_cache(self):
        self.configure()
        wound = self.wound()
        image_id = self.uploaded_image(wound)
        self.assertEqual(self.factory_calls, [])
        self.assertEqual(self.client.get("/api/wound/models", headers=self.headers).json()["wound_segmentation"]["status"], "configured")
        result = self.analyze(image_id)
        self.assertEqual(result.status_code, 200, result.text)
        analysis = result.json()
        self.assertEqual(analysis["status"], "completed")
        self.assertEqual(analysis["image_id"], image_id)
        self.assertEqual(analysis["model_version"], "test-v1")
        self.assertIsNone(analysis["error"])
        self.assertIsNotNone(analysis["completed_at"])
        self.assertIsNone(analysis["input_analysis_id"])
        artifact = analysis["artifacts"][0]
        self.assertEqual((artifact["kind"], artifact["content_type"]), ("mask", "image/png"))
        url = f"/api/wound/analysis-artifacts/{artifact['id']}"
        response = self.client.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["cache-control"])
        with Image.open(io.BytesIO(response.content)) as mask:
            self.assertEqual(mask.size, (12, 10))
            self.assertEqual(mask.getextrema(), (7, 7))
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.analyze(image_id).json()["id"], analysis["id"])
        self.assertEqual(len(self.factory_calls), 1)
        self.assertEqual(len(self.predict_calls), 1)
        self.assertEqual(self.client.get("/api/wound/models", headers=self.headers).json()["wound_segmentation"]["status"], "ready")
        history = self.client.get(f"/api/wound/images/{image_id}/analysis", headers=self.headers).json()
        self.assertEqual(history, [analysis])
        visits = self.client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json()
        self.assertEqual(visits[0]["analysis"]["wound_segmentation"], "completed")
        progress = self.client.get(f"/api/wound/wounds/{wound['id']}/progress", headers=self.headers).json()
        self.assertEqual(len(progress["points"]), 1)
        # This generic fixture adapter has no declared tissue label ontology.
        self.assertEqual(progress["points"][0]["status"], "unavailable")
        self.assertIsNone(progress["points"][0]["percentages"])
        self.assertIsNone(progress["healing_percentage"])
        self.assertEqual(progress["status"], "pending")

    def test_authorization_before_loading_and_for_history(self):
        self.configure()
        image_id = self.uploaded_image()
        self.assertEqual(self.analyze(image_id, headers=self.other_headers).status_code, 404)
        url = f"/api/wound/images/{image_id}/analysis"
        self.assertEqual(self.client.get(url, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.post(url, json={"stage": "wound_segmentation"}).status_code, 401)
        self.assertEqual(self.client.get("/api/wound/models").status_code, 401)
        self.assertEqual(self.factory_calls, [])

    def test_invalid_output_dimensions_and_version_fail_without_artifacts(self):
        self.configure()
        wound = self.wound()
        image_id = self.uploaded_image(wound)
        for mode in ("invalid_bytes", "wrong_dimensions", "wrong_version"):
            with self.subTest(mode=mode):
                self.invalid_output = mode == "invalid_bytes"
                self.result_size = (2, 3) if mode == "wrong_dimensions" else (12, 10)
                self.result_version = "unexpected-version" if mode == "wrong_version" else None
                result = self.analyze(image_id)
                self.assertEqual(result.status_code, 200, result.text)
                analysis = result.json()
                self.assertEqual(analysis["status"], "failed")
                self.assertEqual(analysis["artifacts"], [])
                self.assertNotIn(self.directory.name, analysis["error"])
                self.assertNotIn("private-model-path", analysis["error"])
                self.assertIsNotNone(analysis["completed_at"])
                if repository.artifact_directory().exists():
                    self.assertEqual(list(repository.artifact_directory().iterdir()), [])
        self.assertEqual(len(self.client.get(f"/api/wound/images/{image_id}/analysis", headers=self.headers).json()), 3)
        visits = self.client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json()
        self.assertEqual(visits[0]["analysis"]["wound_segmentation"], "failed")

    def test_tissue_requires_same_image_wound_mask_and_pins_dependency(self):
        self.configure()
        wound = self.wound()
        first_image = self.uploaded_image(wound)
        second_image = self.uploaded_image(wound, "2026-10-07")
        self.assertEqual(self.analyze(first_image, "tissue_segmentation").status_code, 409)
        first_run = self.analyze(first_image).json()
        self.assertEqual(self.analyze(second_image, "tissue_segmentation").status_code, 409)
        tissue = self.analyze(first_image, "tissue_segmentation")
        self.assertEqual(tissue.status_code, 200, tissue.text)
        self.assertEqual(tissue.json()["status"], "completed")
        self.assertEqual(tissue.json()["input_analysis_id"], first_run["id"])
        self.assertIsNotNone(self.predict_calls[-1][1])
        self.assertTrue(self.predict_calls[-1][1].is_file())
        self.assertEqual(self.analyze(first_image, "tissue_segmentation").json()["id"], tissue.json()["id"])
        with repository.connection() as database:
            self.assertEqual(database.execute("SELECT COUNT(*) FROM wound_analyses WHERE image_id = ?", (second_image,)).fetchone()[0], 0)

    def test_no_http_supplied_models_or_healing_and_safe_config_errors(self):
        image_id = self.uploaded_image()
        for stage in ("healing_analysis", "unknown"):
            self.assertEqual(self.analyze(image_id, stage).status_code, 422)
        self.assertEqual(self.analyze(image_id, weights_path="private.pt").status_code, 422)
        path = self.configure()
        document = json.loads(path.read_text())
        document["wound_segmentation"]["adapter"] = "missing_private_module:create"
        path.write_text(json.dumps(document))
        result = self.analyze(image_id)
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("missing_private_module", result.text)
        status = self.client.get("/api/wound/models", headers=self.headers).json()
        self.assertEqual(status["wound_segmentation"]["status"], "error")
        self.assertNotIn(self.directory.name, json.dumps(status))
        with repository.connection() as database:
            self.assertEqual(database.execute("SELECT COUNT(*) FROM wound_analyses").fetchone()[0], 0)
        path.write_text("not json")
        self.assertEqual(self.client.get("/api/wound/models", headers=self.headers).json()["wound_segmentation"]["status"], "error")

    def test_artifact_path_containment_and_missing_cached_file(self):
        self.configure()
        image_id = self.uploaded_image()
        first = self.analyze(image_id).json()
        artifact = first["artifacts"][0]
        with repository.connection() as database:
            database.execute("UPDATE wound_analysis_artifacts SET storage_name = '../clinic.sqlite3' WHERE id = ?", (artifact["id"],))
        self.assertEqual(self.client.get(f"/api/wound/analysis-artifacts/{artifact['id']}", headers=self.headers).status_code, 404)
        rerun = self.analyze(image_id).json()
        self.assertEqual(rerun["status"], "completed")
        self.assertNotEqual(first["id"], rerun["id"])

    def test_profiles_separate_results_dependencies_and_validate_selection(self):
        path = self.configure()
        stages = json.loads(path.read_text())
        path.write_text(json.dumps({"default_model_id": "model_a", "profiles": {
            "model_a": {"label": "First model", **stages}, "model_b": {"label": "Second model", **stages}}}))
        wound = self.wound()
        image_id = self.uploaded_image(wound)
        models = self.client.get("/api/wound/models", headers=self.headers).json()
        self.assertEqual(models["default_model_id"], "model_a")
        self.assertEqual(models["selected_model_id"], "model_a")
        self.assertEqual([model["id"] for model in models["models"]], ["model_a", "model_b"])
        self.assertEqual(self.client.get("/api/wound/models?model_id=model_b", headers=self.headers).json()["selected_model_id"], "model_b")
        self.assertEqual(self.client.get("/api/wound/models?model_id=unknown", headers=self.headers).status_code, 400)
        self.assertEqual(self.analyze(image_id, model_id="unknown").status_code, 400)
        first = self.analyze(image_id, model_id="model_a").json()
        self.assertEqual(first["model_id"], "model_a")
        self.assertEqual(self.analyze(image_id, "tissue_segmentation", model_id="model_b").status_code, 409)
        second = self.analyze(image_id, model_id="model_b").json()
        self.assertEqual(second["model_id"], "model_b")
        self.assertNotEqual(first["id"], second["id"])
        tissue = self.analyze(image_id, "tissue_segmentation", model_id="model_b").json()
        self.assertEqual(tissue["input_analysis_id"], second["id"])
        default_summary = self.client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json()[0]
        selected_summary = self.client.get(f"/api/wound/wounds/{wound['id']}/visits?model_id=model_b", headers=self.headers).json()[0]
        self.assertEqual(default_summary["analysis"]["tissue_segmentation"], "pending")
        self.assertEqual(selected_summary["analysis"]["tissue_segmentation"], "completed")

    def test_changed_weights_or_parameters_do_not_reuse_stale_same_version_results(self):
        path = self.configure()
        image_id = self.uploaded_image()
        first = self.analyze(image_id).json()
        (Path(self.directory.name) / "fixture-model.pt").write_bytes(b"Different synthetic checkpoint bytes")
        second = self.analyze(image_id).json()
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["model_version"], second["model_version"])
        document = json.loads(path.read_text())
        document["wound_segmentation"]["parameters"]["fixture"] = "changed-preprocessing"
        path.write_text(json.dumps(document))
        third = self.analyze(image_id).json()
        self.assertNotEqual(second["id"], third["id"])
        self.assertEqual(len(registry._loaded), 1)
        self.assertNotIn("model_fingerprint", third)

    def test_tissue_rejects_wound_mask_from_outdated_checkpoint_or_preprocessing(self):
        path = self.configure()
        image_id = self.uploaded_image()
        original = self.analyze(image_id).json()
        (Path(self.directory.name) / "fixture-model.pt").write_bytes(b"Updated checkpoint, same version label")
        self.assertEqual(self.analyze(image_id, "tissue_segmentation").status_code, 409)
        updated = self.analyze(image_id).json()
        self.assertNotEqual(original["id"], updated["id"])
        document = json.loads(path.read_text())
        document["wound_segmentation"]["parameters"]["input_size"] = 256
        path.write_text(json.dumps(document))
        self.assertEqual(self.analyze(image_id, "tissue_segmentation").status_code, 409)
        current = self.analyze(image_id).json()
        tissue = self.analyze(image_id, "tissue_segmentation").json()
        self.assertEqual(tissue["status"], "completed")
        self.assertEqual(tissue["input_analysis_id"], current["id"])

    def test_recovery_marks_only_unlocked_interrupted_runs_failed(self):
        image_id = self.uploaded_image()
        run_id = str(uuid4())
        lock = RunLock(run_id)
        self.assertTrue(lock.acquired)
        with repository.connection() as database:
            database.execute("""INSERT INTO wound_analyses (id, image_id, stage, status, model_version, created_at)
                                VALUES (?, ?, 'wound_segmentation', 'running', 'test-v1', '2026-10-21T00:00:00Z')""", (run_id, image_id))
        try:
            live = self.client.get(f"/api/wound/images/{image_id}/analysis", headers=self.headers).json()[0]
            self.assertEqual(live["status"], "running")
        finally:
            lock.close()
        recovered = self.client.get(f"/api/wound/images/{image_id}/analysis", headers=self.headers).json()[0]
        self.assertEqual(recovered["status"], "failed")
        self.assertIn("interrupted", recovered["error"])
        self.assertEqual(recovered["artifacts"], [])

    def test_adapter_release_after_copy_including_invalid_output(self):
        path = self.configure()
        released = []
        original_factory = self.adapter_module.create

        def factory(**kwargs):
            adapter = original_factory(**kwargs)

            def release(result):
                released.append(result.mask_path)
                result.mask_path.unlink()

            adapter.release = release
            return adapter

        self.adapter_module.create = factory
        wound = self.wound()
        first_image = self.uploaded_image(wound)
        result = self.analyze(first_image).json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(released), 1)
        self.assertFalse(released[0].exists())
        self.invalid_output = True
        second_image = self.uploaded_image(wound, "2026-10-07")
        result = self.analyze(second_image).json()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(released), 2)
        self.assertFalse(released[1].exists())


if __name__ == "__main__":
    unittest.main()
