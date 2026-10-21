"""Database repository for diabetes assessments with SQLite local fallback and MongoDB support."""
from pathlib import Path
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_mongo_uri = os.getenv("MONGODB_URI")
_mongo_db_name = os.getenv("MONGODB_DATABASE", "dcare")
_sqlite_path = Path(__file__).resolve().parents[3] / "outputs" / "diabetes_assessments.sqlite3"

_mongo_col = None
if _mongo_uri:
    try:
        from pymongo import MongoClient
        _client = MongoClient(_mongo_uri, serverSelectionTimeoutMS=2000)
        _mongo_col = _client[_mongo_db_name]["diabetes_assessments"]
    except Exception:
        _mongo_col = None


def _get_sqlite_connection():
    _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_sqlite_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS diabetes_assessments (
            id TEXT PRIMARY KEY,
            user_email TEXT,
            timestamp TEXT,
            prediction_label TEXT,
            probability REAL,
            threshold REAL,
            model_version TEXT,
            clinical_status TEXT,
            input_data TEXT,
            clinical_assessment TEXT,
            explainability TEXT,
            risk_factors TEXT,
            personalized_awareness TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_email ON diabetes_assessments(user_email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON diabetes_assessments(timestamp)")
    return conn


class DiabetesRepository:
    def save_assessment(self, record: dict[str, Any]) -> str:
        record_id = record.get("id") or str(uuid.uuid4())
        record["id"] = record_id
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()

        # If MongoDB is available and healthy
        if _mongo_col is not None:
            try:
                _mongo_col.insert_one(dict(record))
                return record_id
            except Exception:
                pass  # fallback to SQLite seamlessly

        # Local SQLite fallback
        with _get_sqlite_connection() as conn:
            conn.execute(
                """
                INSERT INTO diabetes_assessments (
                    id, user_email, timestamp, prediction_label, probability, threshold,
                    model_version, clinical_status, input_data, clinical_assessment,
                    explainability, risk_factors, personalized_awareness
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    record.get("user_email") or "anonymous@patient.local",
                    record["timestamp"],
                    record.get("prediction", {}).get("label", "unknown"),
                    record.get("prediction", {}).get("probability", 0.0),
                    record.get("prediction", {}).get("threshold", 0.40),
                    record.get("prediction", {}).get("model_version", "1.0.0"),
                    record.get("clinical_assessment", {}).get("status", "normal"),
                    json.dumps(record.get("input", {})),
                    json.dumps(record.get("clinical_assessment", {})),
                    json.dumps(record.get("explainability", {})),
                    json.dumps(record.get("risk_factor_categories", {})),
                    json.dumps(record.get("personalized_awareness", {}))
                )
            )
            conn.commit()

        return record_id

    def get_history(self, user_email: Optional[str] = None, limit: int = 30) -> list[dict[str, Any]]:
        # If MongoDB is configured
        if _mongo_col is not None:
            try:
                query = {"user_email": user_email} if user_email else {}
                cursor = _mongo_col.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
                return list(cursor)
            except Exception:
                pass

        # SQLite query
        with _get_sqlite_connection() as conn:
            if user_email:
                cur = conn.execute(
                    "SELECT * FROM diabetes_assessments WHERE user_email = ? ORDER BY timestamp DESC LIMIT ?",
                    (user_email, limit)
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM diabetes_assessments ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
            rows = cur.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "user_email": r["user_email"],
                "timestamp": r["timestamp"],
                "prediction": {
                    "label": r["prediction_label"],
                    "probability": r["probability"],
                    "threshold": r["threshold"],
                    "model_version": r["model_version"]
                },
                "clinical_assessment": json.loads(r["clinical_assessment"]) if r["clinical_assessment"] else {},
                "input": json.loads(r["input_data"]) if r["input_data"] else {},
                "explainability": json.loads(r["explainability"]) if r["explainability"] else {},
                "risk_factor_categories": json.loads(r["risk_factors"]) if r["risk_factors"] else {},
                "personalized_awareness": json.loads(r["personalized_awareness"]) if r["personalized_awareness"] else {}
            })
        return results

    def get_assessment_by_id(self, assessment_id: str) -> Optional[dict[str, Any]]:
        if _mongo_col is not None:
            try:
                doc = _mongo_col.find_one({"id": assessment_id}, {"_id": 0})
                if doc:
                    return doc
            except Exception:
                pass

        with _get_sqlite_connection() as conn:
            cur = conn.execute("SELECT * FROM diabetes_assessments WHERE id = ?", (assessment_id,))
            r = cur.fetchone()
            if not r:
                return None
            return {
                "id": r["id"],
                "user_email": r["user_email"],
                "timestamp": r["timestamp"],
                "prediction": {
                    "label": r["prediction_label"],
                    "probability": r["probability"],
                    "threshold": r["threshold"],
                    "model_version": r["model_version"]
                },
                "clinical_assessment": json.loads(r["clinical_assessment"]) if r["clinical_assessment"] else {},
                "input": json.loads(r["input_data"]) if r["input_data"] else {},
                "explainability": json.loads(r["explainability"]) if r["explainability"] else {},
                "risk_factor_categories": json.loads(r["risk_factors"]) if r["risk_factors"] else {},
                "personalized_awareness": json.loads(r["personalized_awareness"]) if r["personalized_awareness"] else {}
            }


diabetes_repository = DiabetesRepository()
