"""Isolated bridge protocol checks; never load checkpoints or call a runtime."""

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from PIL import Image

from app.models import prototype_adapter as bridge


def mask_url(labels, size=(4, 2), mode="L"):
    output = io.BytesIO()
    Image.frombytes("L", size, bytes(labels)).convert(mode).save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")


class PrototypeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.environment = patch.dict(os.environ, {"WOUND_DATA_DIR": str(self.directory / "private-output")})
        self.environment.start()
        self.model_id = "unet_resnet18"
        self.weights = self.directory / self.model_id / "final.pt"
        self.weights.parent.mkdir()
        self.weights.write_bytes(b"Isolated checkpoint fixture, not a trained model")
        self.digest = hashlib.sha256(self.weights.read_bytes()).hexdigest()
        self.original = self.directory / "visit.png"
        Image.new("RGB", (4, 2), (200, 100, 100)).save(self.original)
        self.wound_mask = self.directory / "wound-mask.png"
        Image.new("L", (4, 2), 1).save(self.wound_mask)
        self.parameters = {"model_id": self.model_id, "service_url": "http://127.0.0.1:8010",
                           "runtime_token": "synthetic-private-runtime-token-for-tests", "timeout_seconds": 10}
        self.response = {
            "source": "model_prediction", "model_id": self.model_id, "checkpoint_sha256": self.digest,
            "image_width": 4, "image_height": 2,
            "supported_tissue_classes": [0, 1, 2, 3, 5, 6, 7], "unsupported_tissue_classes": [4],
            "wound_mask_data_url": mask_url([0, 1, 0, 1, 0, 1, 0, 1]),
            "tissue_mask_data_url": mask_url([0, 1, 2, 3, 5, 6, 7, 0]),
        }

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def adapter(self, stage="wound_segmentation", **parameters):
        factory = bridge.build_wound_adapter if stage == "wound_segmentation" else bridge.build_tissue_adapter
        return factory(weights_path=self.weights, model_version="fixture-v1", parameters={**self.parameters, **parameters})

    def predict(self, adapter, response=None):
        fake_response = MagicMock()
        fake_response.__enter__.return_value = fake_response
        fake_response.read.return_value = json.dumps(response if response is not None else self.response).encode()
        fake_opener = MagicMock()
        fake_opener.open.return_value = fake_response
        with patch.object(bridge, "build_opener", return_value=fake_opener):
            result = adapter.predict(self.original, self.wound_mask) if adapter.stage == "tissue_segmentation" else adapter.predict(self.original)
        return result, fake_opener

    def test_numeric_masks_preserve_ids_palette_and_release_own_files(self):
        for stage, expected in [("wound_segmentation", [0, 1, 0, 1, 0, 1, 0, 1]),
                                ("tissue_segmentation", [0, 1, 2, 3, 5, 6, 7, 0])]:
            with self.subTest(stage=stage):
                adapter = self.adapter(stage)
                result, opener = self.predict(adapter)
                self.assertEqual(result.model_version, "fixture-v1")
                with Image.open(result.mask_path) as output:
                    self.assertEqual(output.mode, "P")
                    self.assertEqual(output.size, (4, 2))
                    self.assertEqual(list(output.tobytes()), expected)
                    palette = output.getpalette()
                    expected_colors = {0: (0, 0, 0), 1: (255, 255, 255)} if stage == "wound_segmentation" else bridge.TISSUE_COLORS
                    for label in set(expected):
                        self.assertEqual(tuple(palette[label * 3:label * 3 + 3]), expected_colors[label])
                request = opener.open.call_args.args[0]
                self.assertEqual(request.full_url, "http://127.0.0.1:8010/predict")
                self.assertEqual(request.get_header("Authorization"), "Bearer " + self.parameters["runtime_token"])
                self.assertIn(self.digest.encode(), request.data)
                self.assertIn(self.model_id.encode(), request.data)
                self.assertEqual(opener.open.call_args.kwargs["timeout"], 10)
                # The bridge deletes its scratch output; original inputs remain intact.
                adapter.release(result)
                self.assertFalse(result.mask_path.exists())
                adapter.release(result)
                self.assertTrue(self.original.is_file())
                self.assertTrue(self.wound_mask.is_file())

    def test_rejects_incorrect_response_provenance_and_protocol(self):
        changes = [
            {"checkpoint_sha256": "0" * 64}, {"model_id": "segformer_mit_b0"},
            {"image_width": 3}, {"image_height": 3}, {"source": "manual"},
            {"supported_tissue_classes": [0, 1, 2, 3, 4, 5, 6, 7]}, {"unsupported_tissue_classes": []},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.predict(self.adapter(), {**self.response, **change})
        self.assertFalse((self.directory / "private-output" / "model_scratch").exists())

    def test_rejects_unsupported_tissue_and_wound_labels(self):
        cases = [
            ("wound_segmentation", "wound_mask_data_url", mask_url([0, 1, 0, 2, 0, 1, 0, 1])),
            ("tissue_segmentation", "tissue_mask_data_url", mask_url([0, 1, 2, 3, 4, 5, 6, 7])),
            ("tissue_segmentation", "tissue_mask_data_url", mask_url([0, 1, 2, 3, 5, 6, 7, 255])),
        ]
        for stage, field, data in cases:
            with self.subTest(stage=stage, data=data[:30]), self.assertRaises(ValueError):
                self.predict(self.adapter(stage), {**self.response, field: data})

    def test_rejects_invalid_numeric_masks_before_writing_scratch_files(self):
        for data in [mask_url([0, 1, 0, 1, 0, 1, 0, 1], mode="RGB"),
                     mask_url([0, 1], size=(2, 1)), "data:image/jpeg;base64,AA==", "not-a-data-url"]:
            with self.subTest(data=data[:35]), self.assertRaises(ValueError):
                self.predict(self.adapter(), {**self.response, "wound_mask_data_url": data})
        self.assertFalse((self.directory / "private-output" / "model_scratch").exists())

    def test_rejects_changed_checkpoint_and_wrong_tissue_dependency_dimensions(self):
        adapter = self.adapter()
        self.weights.write_bytes(b"Checkpoint replaced after initialization")
        with patch.object(bridge, "build_opener") as opener, self.assertRaises(RuntimeError):
            adapter.predict(self.original)
        opener.assert_not_called()
        self.weights.write_bytes(b"Isolated checkpoint fixture, not a trained model")
        Image.new("L", (2, 2), 1).save(self.wound_mask)
        with patch.object(bridge, "build_opener") as opener, self.assertRaises(ValueError):
            self.adapter("tissue_segmentation").predict(self.original, self.wound_mask)
        opener.assert_not_called()

    def test_rejects_wrong_checkpoint_location_or_model_selection(self):
        with self.assertRaises(ValueError):
            self.adapter(model_id="unknown-model")
        with self.assertRaises(ValueError):
            self.adapter(model_id="segformer_mit_b0")
        with self.assertRaises(ValueError):
            bridge.build_wound_adapter(weights_path=self.original, model_version="fixture-v1", parameters=self.parameters)

    def test_rejects_nonloopback_urls_credentials_and_bad_tokens(self):
        for url in ["https://127.0.0.1:8010", "http://example.com:8010", "http://127.0.0.1.evil:8010",
                    "http://user:secret@127.0.0.1:8010", "http://127.0.0.1:8010/path",
                    "http://127.0.0.1:8010?token=x", "http://127.0.0.1:8010#fragment", "file:///private/model"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.adapter(service_url=url)
        for token in ["", "short", None, 123]:
            with self.subTest(token=token), self.assertRaises(ValueError):
                self.adapter(runtime_token=token)
        for timeout in [True, 0, 601, "180"]:
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.adapter(timeout_seconds=timeout)

    def test_http_errors_have_safe_public_message_and_preserve_diagnostic_cause(self):
        for error in [HTTPError("http://127.0.0.1:8010/predict", 401, "private service detail", {}, None),
                      URLError("private connection detail"), TimeoutError("private timeout detail")]:
            opener = MagicMock()
            opener.open.side_effect = error
            with patch.object(bridge, "build_opener", return_value=opener), self.assertRaises(RuntimeError) as raised:
                self.adapter().predict(self.original)
            self.assertIs(raised.exception.__cause__, error)
            self.assertNotIn("private", str(raised.exception))
            self.assertNotIn(self.parameters["runtime_token"], str(raised.exception))
        self.assertFalse((self.directory / "private-output" / "model_scratch").exists())


if __name__ == "__main__":
    unittest.main()
