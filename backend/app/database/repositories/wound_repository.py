"""Persistent, account-scoped SQLite storage for clinic records."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException


def database_path():
    configured = os.getenv("WOUND_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return data_directory() / "wound_clinic.sqlite3"


def data_directory():
    configured = os.getenv("WOUND_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    database = os.getenv("WOUND_DB_PATH")
    if database:
        return Path(database).expanduser().resolve().parent
    return Path(__file__).resolve().parents[3] / "outputs"


def image_directory():
    return data_directory() / "wound_images"


def artifact_directory():
    return data_directory() / "wound_analysis"


SCHEMA = """
CREATE TABLE IF NOT EXISTS wound_patients (
    id TEXT PRIMARY KEY, owner TEXT NOT NULL, patient_code TEXT NOT NULL,
    patient_code_key TEXT NOT NULL, display_name TEXT NOT NULL, notes TEXT NOT NULL,
    created_at TEXT NOT NULL, UNIQUE(owner, patient_code_key)
);
CREATE TABLE IF NOT EXISTS clinic_wounds (
    id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES wound_patients(id),
    label TEXT NOT NULL, location TEXT NOT NULL, onset_date TEXT,
    status TEXT NOT NULL CHECK(status IN ('active', 'healed')),
    notes TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wound_visits (
    id TEXT PRIMARY KEY, wound_id TEXT NOT NULL REFERENCES clinic_wounds(id),
    visit_date TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL,
    progress_image_id TEXT REFERENCES wound_images(id),
    UNIQUE(wound_id, visit_date)
);
CREATE TABLE IF NOT EXISTS wound_images (
    id TEXT PRIMARY KEY, visit_id TEXT NOT NULL REFERENCES wound_visits(id),
    filename TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL, byte_size INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS wound_patient_owner ON wound_patients(owner);
CREATE INDEX IF NOT EXISTS wound_patient ON clinic_wounds(patient_id);
CREATE INDEX IF NOT EXISTS wound_visit ON wound_visits(wound_id, visit_date);
CREATE INDEX IF NOT EXISTS wound_image_visit ON wound_images(visit_id);
CREATE TABLE IF NOT EXISTS wound_analyses (
    id TEXT PRIMARY KEY, image_id TEXT NOT NULL REFERENCES wound_images(id),
    model_id TEXT NOT NULL DEFAULT 'default',
    stage TEXT NOT NULL CHECK(stage IN ('wound_segmentation', 'tissue_segmentation')),
    status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed')),
    model_version TEXT NOT NULL, model_fingerprint TEXT, created_at TEXT NOT NULL, completed_at TEXT,
    error TEXT, input_analysis_id TEXT REFERENCES wound_analyses(id)
);
CREATE INDEX IF NOT EXISTS wound_analysis_image ON wound_analyses(image_id, created_at);
CREATE TABLE IF NOT EXISTS wound_analysis_artifacts (
    id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL REFERENCES wound_analyses(id),
    kind TEXT NOT NULL CHECK(kind IN ('mask', 'overlay')),
    content_type TEXT NOT NULL, storage_name TEXT NOT NULL UNIQUE
);
"""


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path, timeout=10)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        database.executescript(SCHEMA)
        if "model_fingerprint" not in {row["name"] for row in database.execute("PRAGMA table_info(wound_analyses)")}:
            database.execute("ALTER TABLE wound_analyses ADD COLUMN model_fingerprint TEXT")
        if "model_id" not in {row["name"] for row in database.execute("PRAGMA table_info(wound_analyses)")}:
            database.execute("ALTER TABLE wound_analyses ADD COLUMN model_id TEXT NOT NULL DEFAULT 'default'")
        if "progress_image_id" not in {row["name"] for row in database.execute("PRAGMA table_info(wound_visits)")}:
            try:
                database.execute("ALTER TABLE wound_visits ADD COLUMN progress_image_id TEXT REFERENCES wound_images(id)")
            except sqlite3.OperationalError:
                # Another first request may have completed the same migration.
                if "progress_image_id" not in {row["name"] for row in database.execute("PRAGMA table_info(wound_visits)")}:
                    raise
        database.execute("DROP INDEX IF EXISTS wound_one_running_stage")
        database.execute("CREATE UNIQUE INDEX IF NOT EXISTS wound_one_running_profile ON wound_analyses(image_id, stage, model_id) WHERE status = 'running'")
        with database:
            yield database
    finally:
        database.close()


def require_patient(database, patient_id, owner):
    row = database.execute(
        "SELECT * FROM wound_patients WHERE id = ? AND owner = ?", (patient_id, owner)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return row


def require_wound(database, wound_id, owner):
    row = database.execute(
        """SELECT w.* FROM clinic_wounds w JOIN wound_patients p ON p.id = w.patient_id
           WHERE w.id = ? AND p.owner = ?""", (wound_id, owner)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Wound not found.")
    return row


def require_image(database, image_id, owner):
    row = database.execute(
        """SELECT i.* FROM wound_images i JOIN wound_visits v ON v.id = i.visit_id
           JOIN clinic_wounds w ON w.id = v.wound_id JOIN wound_patients p ON p.id = w.patient_id
           WHERE i.id = ? AND p.owner = ?""", (image_id, owner),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    return row


def analysis_record(database, row):
    record = dict(row)
    record.pop("model_fingerprint", None)
    record["artifacts"] = [dict(item) for item in database.execute(
        "SELECT id, kind, content_type FROM wound_analysis_artifacts WHERE analysis_id = ? ORDER BY rowid", (row["id"],)
    )]
    return record


def list_analyses(database, image_id):
    return [analysis_record(database, row) for row in database.execute(
        "SELECT * FROM wound_analyses WHERE image_id = ? ORDER BY created_at DESC, rowid DESC", (image_id,)
    )]


def list_patients(database, owner):
    return [dict(row) for row in database.execute(
        """SELECT p.id, p.patient_code, p.display_name, p.notes, p.created_at,
                  COUNT(w.id) AS wound_count
           FROM wound_patients p LEFT JOIN clinic_wounds w ON w.patient_id = p.id
           WHERE p.owner = ? GROUP BY p.id ORDER BY p.created_at DESC, p.id""", (owner,)
    )]


def list_wounds(database, patient_id):
    return [dict(row) for row in database.execute(
        """SELECT w.*, COUNT(v.id) AS visit_count, MAX(v.visit_date) AS latest_visit_date
           FROM clinic_wounds w LEFT JOIN wound_visits v ON v.wound_id = w.id
           WHERE w.patient_id = ? GROUP BY w.id ORDER BY w.created_at DESC, w.id""", (patient_id,)
    )]


def list_visits(database, wound_id, model_id=None):
    from app.models.wound_registry import registry
    models = registry.statuses(model_id)
    selected_model_id = models["selected_model_id"]
    visits = [dict(row) for row in database.execute(
        "SELECT id, wound_id, visit_date, notes, created_at, progress_image_id FROM wound_visits WHERE wound_id = ? ORDER BY visit_date, created_at, id",
        (wound_id,),
    )]
    for visit in visits:
        visit["images"] = [dict(row) for row in database.execute(
            "SELECT id, filename, content_type, byte_size FROM wound_images WHERE visit_id = ? ORDER BY rowid",
            (visit["id"],),
        )]
        if visit["progress_image_id"] not in {image["id"] for image in visit["images"]}:
            visit["progress_image_id"] = visit["images"][0]["id"] if visit["images"] else None
        visit["analysis"] = {
            "healing_analysis": "not_connected",
        }
        for stage in ("wound_segmentation", "tissue_segmentation"):
            statuses = []
            for image in visit["images"]:
                latest = database.execute(
                    """SELECT status FROM wound_analyses WHERE image_id = ? AND stage = ?
                       AND (? IS NULL OR model_id = ?) ORDER BY created_at DESC, rowid DESC LIMIT 1""",
                    (image["id"], stage, selected_model_id, selected_model_id),
                ).fetchone()
                statuses.append(latest["status"] if latest else ("pending" if models[stage]["status"] in ("configured", "ready") else "not_connected"))
            visit["analysis"][stage] = ("running" if "running" in statuses else "failed" if "failed" in statuses
                                         else "completed" if statuses and all(status == "completed" for status in statuses)
                                         else "pending" if any(status in ("completed", "pending") for status in statuses) else "not_connected")
    return visits
