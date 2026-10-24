"""Isolated clinic API regression checks. No real accounts or clinic data are used."""

import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from jose import jwt
from PIL import Image

from app.api import auth
from app.database.repositories import wound_repository as repository
from app.main import app
from app.services.wound_service import MAX_IMAGE_BYTES


def image_bytes(image_format="PNG", size=(12, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, format=image_format)
    return buffer.getvalue()


class ClinicApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"WOUND_DATA_DIR": self.directory.name, "WOUND_DB_PATH": str(Path(self.directory.name) / "clinic.sqlite3"), "WOUND_MODEL_CONFIG": ""})
        self.env.start()
        self.accounts = {"clinic-a@example.com", "clinic-b@example.com"}
        self.account_lookup = patch.object(auth, "find", side_effect=lambda email: {"email": email} if email in self.accounts else None)
        self.account_lookup.start()
        self.client = TestClient(app)
        self.headers = self.headers_for("clinic-a@example.com")
        self.other_headers = self.headers_for("clinic-b@example.com")

    def tearDown(self):
        self.client.close()
        self.account_lookup.stop()
        self.env.stop()
        self.directory.cleanup()

    def headers_for(self, owner, expires=None):
        token = jwt.encode({"sub": owner, "exp": expires or datetime.now(timezone.utc) + timedelta(minutes=10)}, auth.SECRET, algorithm=auth.ALGORITHM)
        return {"Authorization": "Bearer " + token}

    def patient(self, code="PT-001", headers=None):
        response = self.client.post("/api/wound/patients", headers=headers or self.headers, json={"patient_code": code, "display_name": "Test patient"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def wound(self, patient=None):
        patient = patient or self.patient()
        response = self.client.post(f"/api/wound/patients/{patient['id']}/wounds", headers=self.headers, json={"label": "Left foot wound", "location": "Left heel"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def visit(self, wound, visit_date="2026-10-01", content=None, filename="wound.png", content_type="image/png", fields=None):
        return self.client.post(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers,
            data={"visit_date": visit_date, **(fields or {})}, files=[("images", (filename, content if content is not None else image_bytes(), content_type))])

    def assert_pending_progress(self, progress, visits):
        self.assertEqual(progress["status"], "pending")
        self.assertIsNone(progress["healing_percentage"])
        self.assertEqual(progress["summary"], {"visit_count": len(visits), "analyzed_visit_count": 0})
        self.assertEqual([point["visit_id"] for point in progress["points"]], [visit["id"] for visit in visits])
        self.assertEqual([point["visit_date"] for point in progress["points"]], [visit["visit_date"] for visit in visits])
        self.assertEqual(len(progress["tissues"]), 7)
        for point, visit in zip(progress["points"], visits):
            self.assertEqual(point["image_id"], visit["images"][0]["id"])
            self.assertIsNone(point["percentages"])
            self.assertIn(point["status"], ("pending", "unavailable"))
            self.assertTrue(point["reason"])
            self.assertNotIn("area_cm2", point)
            self.assertNotIn("healing_percentage", point)

    def test_authentication_and_deleted_account(self):
        url = "/api/wound/patients"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers={"Authorization": "Bearer bad-token"}).status_code, 401)
        expired = self.headers_for("clinic-a@example.com", datetime.now(timezone.utc) - timedelta(seconds=1))
        self.assertEqual(self.client.get(url, headers=expired).status_code, 401)
        self.accounts.remove("clinic-a@example.com")
        self.assertEqual(self.client.get(url, headers=self.headers).status_code, 401)

    def test_duplicate_codes_are_case_insensitive_and_workspace_scoped(self):
        self.patient("PT-001")
        duplicate = self.client.post("/api/wound/patients", headers=self.headers, json={"patient_code": "pt-001", "display_name": "Other patient"})
        self.assertEqual(duplicate.status_code, 409)
        self.patient("pt-001", self.other_headers)
        self.assertEqual(len(self.client.get("/api/wound/patients", headers=self.headers).json()), 1)
        with repository.connection() as database:
            self.assertEqual(database.execute("SELECT COUNT(*) FROM wound_patients").fetchone()[0], 2)

    def test_patient_wound_and_image_ownership(self):
        patient = self.patient()
        wound = self.wound(patient)
        visit = self.visit(wound).json()
        paths = [f"/api/wound/patients/{patient['id']}/wounds", f"/api/wound/wounds/{wound['id']}/visits", f"/api/wound/wounds/{wound['id']}/progress", f"/api/wound/images/{visit['images'][0]['id']}"]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.post(paths[0], headers=self.other_headers, json={"label": "Test", "location": "Heel"}).status_code, 404)
        self.assertEqual(self.client.patch(f"/api/wound/wounds/{wound['id']}", headers=self.other_headers, json={"status": "healed"}).status_code, 404)
        self.assertEqual(self.client.get("/api/wound/patients", headers=self.other_headers).json(), [])
        image_response = self.client.get(paths[-1], headers=self.headers)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.content, image_bytes())
        self.assertIn("no-store", image_response.headers["cache-control"])
        self.assertEqual(self.client.get(paths[-1]).status_code, 401)

    def test_persistence_chronology_counts_and_pending_results(self):
        patient = self.patient()
        wound = self.wound(patient)
        for date in ["2026-10-14", "2026-10-01", "2026-10-07"]:
            response = self.visit(wound, date)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertNotIn("area_cm2", response.json())
            self.assertNotIn("measurement_source", response.json())
            self.assertEqual(set(response.json()["analysis"].values()), {"not_connected"})
        # A fresh client/repository connection reads persistent files, not process memory.
        with TestClient(app) as client:
            visits = client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json()
            self.assertEqual([v["visit_date"] for v in visits], ["2026-10-01", "2026-10-07", "2026-10-14"])
            progress = client.get(f"/api/wound/wounds/{wound['id']}/progress", headers=self.headers).json()
            self.assert_pending_progress(progress, visits)
        self.assertEqual(self.client.get("/api/wound/patients", headers=self.headers).json()[0]["wound_count"], 1)
        listed = self.client.get(f"/api/wound/patients/{patient['id']}/wounds", headers=self.headers).json()[0]
        self.assertEqual((listed["visit_count"], listed["latest_visit_date"]), (3, "2026-10-14"))

    def test_duplicate_visit_is_atomic_and_healed_wound_can_be_reopened(self):
        wound = self.wound()
        self.assertEqual(self.visit(wound).status_code, 201)
        self.assertEqual(self.visit(wound).status_code, 409)
        self.assertEqual(len(list(repository.image_directory().iterdir())), 1)
        url = f"/api/wound/wounds/{wound['id']}"
        self.assertEqual(self.client.patch(url, headers=self.headers, json={"status": "healed"}).status_code, 200)
        self.assertEqual(self.visit(wound, "2026-10-02").status_code, 409)
        self.assertEqual(self.client.patch(url, headers=self.headers, json={"status": "active"}).status_code, 200)
        self.assertEqual(self.visit(wound, "2026-10-02").status_code, 201)

    def test_validation_rejects_bad_images_dates_and_manual_measurements(self):
        wound = self.wound()
        cases = [
            {"content": b"not an image"},
            {"content_type": "image/jpeg"},
            {"visit_date": "not-a-date"},
            {"visit_date": "0"},
            {"content": b"x" * (MAX_IMAGE_BYTES + 1)},
            {"fields": {"notes": "x" * 2001}},
            {"fields": {"area_cm2": "4.2"}},
            {"content": image_bytes(size=(8193, 1))},
        ]
        for arguments in cases:
            with self.subTest(arguments=list(arguments)):
                self.assertEqual(self.visit(wound, **arguments).status_code, 422)
        self.assertEqual(self.client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json(), [])
        self.assertFalse(repository.image_directory().exists())

    def test_upload_count_and_batch_validation_are_atomic(self):
        wound = self.wound()
        url = f"/api/wound/wounds/{wound['id']}/visits"
        no_images = self.client.post(url, headers=self.headers, data={"visit_date": "2026-10-01"})
        self.assertEqual(no_images.status_code, 422)
        too_many = [("images", (f"{i}.png", image_bytes(), "image/png")) for i in range(6)]
        self.assertIn(self.client.post(url, headers=self.headers, data={"visit_date": "2026-10-01"}, files=too_many).status_code, (400, 422))
        batch = [("images", ("valid.png", image_bytes(), "image/png")), ("images", ("invalid.png", b"invalid", "image/png"))]
        self.assertEqual(self.client.post(url, headers=self.headers, data={"visit_date": "2026-10-01"}, files=batch).status_code, 422)
        self.assertEqual(self.client.get(url, headers=self.headers).json(), [])
        self.assertFalse(repository.image_directory().exists())

    def test_file_write_failure_rolls_back_rows_and_files(self):
        wound = self.wound()
        original_open = Path.open
        calls = 0

        def fail_second(path, *args, **kwargs):
            nonlocal calls
            if args and args[0] == "xb":
                calls += 1
                if calls == 2:
                    raise OSError("Synthetic storage failure")
            return original_open(path, *args, **kwargs)

        files = [("images", (f"{i}.png", image_bytes(), "image/png")) for i in range(2)]
        with patch.object(Path, "open", fail_second):
            with self.assertRaises(OSError):
                self.client.post(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers, data={"visit_date": "2026-10-01"}, files=files)
        self.assertEqual(list(repository.image_directory().iterdir()), [])
        with repository.connection() as database:
            self.assertEqual(database.execute("SELECT COUNT(*) FROM wound_visits").fetchone()[0], 0)
            self.assertEqual(database.execute("SELECT COUNT(*) FROM wound_images").fetchone()[0], 0)

    def test_safe_filename_and_path_containment(self):
        wound = self.wound()
        response = self.visit(wound, filename="../../private.png")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["images"][0]["filename"], "private.png")
        image_id = response.json()["images"][0]["id"]
        stored_files = list(repository.image_directory().iterdir())
        self.assertEqual(len(stored_files), 1)
        self.assertEqual(stored_files[0].name, image_id + ".png")
        with repository.connection() as database:
            database.execute("UPDATE wound_images SET storage_name = ? WHERE id = ?", ("../clinic.sqlite3", image_id))
        self.assertEqual(self.client.get(f"/api/wound/images/{image_id}", headers=self.headers).status_code, 404)

    def test_request_field_validation(self):
        for payload in [{"patient_code": " ", "display_name": "Name"}, {"patient_code": "AA", "display_name": " ", "notes": ""}, {"patient_code": "AA", "display_name": "Name", "notes": "x" * 2001}]:
            self.assertEqual(self.client.post("/api/wound/patients", headers=self.headers, json=payload).status_code, 422)
        wound = self.wound()
        self.assertEqual(self.client.patch(f"/api/wound/wounds/{wound['id']}", headers=self.headers, json={"status": "unknown"}).status_code, 422)

    def test_legacy_nullable_columns_do_not_affect_visit_uploads_or_progress(self):
        wound = self.wound()
        with repository.connection() as database:
            database.execute("ALTER TABLE wound_visits ADD COLUMN area_cm2 REAL")
            database.execute("ALTER TABLE wound_visits ADD COLUMN measurement_source TEXT")
        visit = self.visit(wound)
        self.assertEqual(visit.status_code, 201, visit.text)
        self.assertNotIn("area_cm2", visit.json())
        self.assertNotIn("measurement_source", visit.json())
        with repository.connection() as database:
            database.execute("UPDATE wound_visits SET area_cm2 = 10.0, measurement_source = 'legacy manual value' WHERE id = ?", (visit.json()["id"],))
        progress = self.client.get(f"/api/wound/wounds/{wound['id']}/progress", headers=self.headers).json()
        self.assert_pending_progress(progress, [visit.json()])

    def test_progress_without_visits_has_no_computed_values(self):
        wound = self.wound()
        progress = self.client.get(f"/api/wound/wounds/{wound['id']}/progress", headers=self.headers).json()
        self.assert_pending_progress(progress, [])


class ActualAuthenticationClinicIntegrationTests(unittest.TestCase):
    """Real register/login API with synthetic accounts in isolated SQLite files."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "WOUND_DATA_DIR": self.directory.name,
            "WOUND_DB_PATH": str(Path(self.directory.name) / "clinic.sqlite3"),
            "WOUND_MODEL_CONFIG": "",
        })
        self.env.start()
        self.mongo = patch.object(auth, "_users", None)
        self.mongo.start()
        self.account_database = patch.object(auth, "_local_db", Path(self.directory.name) / "accounts.sqlite3")
        self.account_database.start()
        self.client = TestClient(app)
        self.credentials = {"email": "synthetic-clinic@example.com", "password": "ClinicTest2026!"}
        registration = self.client.post("/api/auth/register", json={
            **self.credentials, "confirm_password": self.credentials["password"],
            "name": "Synthetic Clinic", "username": "synthetic_clinic", "phone": "0712345678",
            "is_diabetic": False,
        })
        self.assertEqual(registration.status_code, 200, registration.text)
        self.headers = {"Authorization": "Bearer " + registration.json()["access_token"]}

    def tearDown(self):
        self.client.close()
        self.account_database.stop()
        self.mongo.stop()
        self.env.stop()
        self.directory.cleanup()

    def create_patient(self, code):
        response = self.client.post("/api/wound/patients", headers=self.headers,
            json={"patient_code": code, "display_name": "Synthetic patient " + code})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def create_wound(self, patient, label):
        response = self.client.post(f"/api/wound/patients/{patient['id']}/wounds", headers=self.headers,
            json={"label": label, "location": "Synthetic heel location"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def create_visit(self, wound):
        response = self.client.post(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers,
            data={"visit_date": "2026-10-21", "notes": "Synthetic integration fixture"},
            files=[("images", ("synthetic-image.png", image_bytes(), "image/png"))])
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_register_login_token_workflow_and_persistence(self):
        # This exercises the actual account lookup and token, without auth.find mocks.
        patient = self.create_patient("SYN-001")
        wound = self.create_wound(patient, "Synthetic first wound")
        visit = self.create_visit(wound)
        image_url = f"/api/wound/images/{visit['images'][0]['id']}"
        self.assertEqual(self.client.get(image_url, headers=self.headers).content, image_bytes())
        with TestClient(app) as new_client:
            bad_login = new_client.post("/api/auth/login", json={**self.credentials, "password": "WrongPassword2026!"})
            self.assertEqual(bad_login.status_code, 401)
            login = new_client.post("/api/auth/login", json=self.credentials)
            self.assertEqual(login.status_code, 200, login.text)
            headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            self.assertEqual(new_client.get("/api/wound/patients", headers=headers).json()[0]["id"], patient["id"])
            records = new_client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=headers).json()
            self.assertEqual(records[0]["id"], visit["id"])
            self.assertEqual(set(records[0]["analysis"].values()), {"not_connected"})
            image_response = new_client.get(image_url, headers=headers)
            self.assertEqual(image_response.status_code, 200)
            self.assertEqual(image_response.content, image_bytes())
        self.assertTrue((Path(self.directory.name) / "accounts.sqlite3").is_file())
        self.assertTrue((Path(self.directory.name) / "clinic.sqlite3").is_file())

    def test_distinct_patients_and_sibling_wounds_keep_separate_visits(self):
        first_patient = self.create_patient("SYN-001")
        second_patient = self.create_patient("SYN-002")
        first_wound = self.create_wound(first_patient, "First patient's first wound")
        sibling_wound = self.create_wound(first_patient, "First patient's second wound")
        other_patient_wound = self.create_wound(second_patient, "Second patient's wound")
        wounds = [first_wound, sibling_wound, other_patient_wound]
        visits = [self.create_visit(wound) for wound in wounds]
        self.assertEqual(len({visit["id"] for visit in visits}), 3)
        for wound, visit in zip(wounds, visits):
            listed = self.client.get(f"/api/wound/wounds/{wound['id']}/visits", headers=self.headers).json()
            self.assertEqual([record["id"] for record in listed], [visit["id"]])
            self.assertEqual(listed[0]["wound_id"], wound["id"])
        first_wounds = self.client.get(f"/api/wound/patients/{first_patient['id']}/wounds", headers=self.headers).json()
        second_wounds = self.client.get(f"/api/wound/patients/{second_patient['id']}/wounds", headers=self.headers).json()
        self.assertEqual({wound["id"] for wound in first_wounds}, {first_wound["id"], sibling_wound["id"]})
        self.assertEqual([wound["id"] for wound in second_wounds], [other_patient_wound["id"]])


if __name__ == "__main__":
    unittest.main()
