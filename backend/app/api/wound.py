"""Private clinic workflow and explicitly configured segmentation adapters."""

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.api import auth
from app.database.repositories import wound_repository as repository
from app.schemas.wound_schema import AnalysisCreate, PatientCreate, ProgressImageUpdate, VisitCreate, WoundCreate, WoundStatusUpdate
from app.models.wound_registry import InvalidModelSelection, registry
from app.services.wound_analysis_service import analyze_image, recover_interrupted, stored_path
from app.services.wound_service import MAX_IMAGE_BYTES, validate_image
from app.services.wound_progress_service import progress_for_wound, select_progress_image

router = APIRouter(prefix="/wound", tags=["wound"])
bearer = HTTPBearer(auto_error=False)


def current_workspace(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """Use the existing signed-in account as the clinic workspace boundary."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to access clinic records.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, auth.SECRET, algorithms=[auth.ALGORITHM], options={"require_exp": True, "require_sub": True})
        owner = payload.get("sub")
        if not isinstance(owner, str) or not owner:
            raise JWTError("Missing account")
    except JWTError:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired. Sign in again.", headers={"WWW-Authenticate": "Bearer"})
    if auth.find(owner) is None:
        raise HTTPException(status_code=401, detail="This account no longer exists. Sign in again.")
    return owner


def timestamp():
    return datetime.now(timezone.utc).isoformat()


@router.get("/models")
def models(model_id: str | None = None, owner: str = Depends(current_workspace)):
    try:
        return registry.statuses(model_id)
    except InvalidModelSelection as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


@router.post("/images/{image_id}/analysis")
def create_analysis(image_id: str, payload: AnalysisCreate, owner: str = Depends(current_workspace)):
    return analyze_image(image_id, payload.stage, owner, payload.model_id)


@router.get("/images/{image_id}/analysis")
def analyses(image_id: str, owner: str = Depends(current_workspace)):
    recover_interrupted(image_id, owner)
    with repository.connection() as database:
        repository.require_image(database, image_id, owner)
        return repository.list_analyses(database, image_id)


@router.get("/analysis-artifacts/{artifact_id}")
def analysis_artifact(artifact_id: str, owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        artifact = database.execute(
            """SELECT f.* FROM wound_analysis_artifacts f JOIN wound_analyses a ON a.id = f.analysis_id
               JOIN wound_images i ON i.id = a.image_id JOIN wound_visits v ON v.id = i.visit_id
               JOIN clinic_wounds w ON w.id = v.wound_id JOIN wound_patients p ON p.id = w.patient_id
               WHERE f.id = ? AND p.owner = ? AND a.status = 'completed'""", (artifact_id, owner),
        ).fetchone()
        if artifact is None:
            raise HTTPException(status_code=404, detail="Analysis artifact not found.")
        try:
            path = stored_path(repository.artifact_directory(), artifact["storage_name"])
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Analysis artifact not found.") from None
        return FileResponse(path, media_type=artifact["content_type"], filename=artifact_id + ".png", content_disposition_type="inline", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/patients")
def patients(owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        return repository.list_patients(database, owner)


@router.post("/patients", status_code=201)
def create_patient(payload: PatientCreate, owner: str = Depends(current_workspace)):
    patient_id = str(uuid4())
    try:
        with repository.connection() as database:
            database.execute(
                "INSERT INTO wound_patients VALUES (?, ?, ?, ?, ?, ?, ?)",
                (patient_id, owner, payload.patient_code, payload.patient_code.casefold(), payload.display_name, payload.notes, timestamp()),
            )
            return next(patient for patient in repository.list_patients(database, owner) if patient["id"] == patient_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A patient with this code already exists in your clinic.")


@router.get("/patients/{patient_id}/wounds")
def wounds(patient_id: str, owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        repository.require_patient(database, patient_id, owner)
        return repository.list_wounds(database, patient_id)


@router.post("/patients/{patient_id}/wounds", status_code=201)
def create_wound(patient_id: str, payload: WoundCreate, owner: str = Depends(current_workspace)):
    wound_id = str(uuid4())
    with repository.connection() as database:
        repository.require_patient(database, patient_id, owner)
        database.execute(
            "INSERT INTO clinic_wounds VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (wound_id, patient_id, payload.label, payload.location, payload.onset_date.isoformat() if payload.onset_date else None, payload.status, payload.notes, timestamp()),
        )
        return next(wound for wound in repository.list_wounds(database, patient_id) if wound["id"] == wound_id)


@router.patch("/wounds/{wound_id}")
def update_wound(wound_id: str, payload: WoundStatusUpdate, owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        wound = repository.require_wound(database, wound_id, owner)
        database.execute("UPDATE clinic_wounds SET status = ? WHERE id = ?", (payload.status, wound_id))
        return next(item for item in repository.list_wounds(database, wound["patient_id"]) if item["id"] == wound_id)


@router.get("/wounds/{wound_id}/visits")
def visits(wound_id: str, model_id: str | None = None, owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        repository.require_wound(database, wound_id, owner)
        try:
            return repository.list_visits(database, wound_id, model_id)
        except InvalidModelSelection as error:
            raise HTTPException(status_code=400, detail=str(error)) from None


VISIT_REQUEST_SCHEMA = {
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["visit_date", "images"], "additionalProperties": False,
        "properties": {
            "visit_date": {"type": "string", "format": "date"},
            "notes": {"type": "string", "maxLength": 2000},
            "images": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string", "format": "binary"}},
        },
    }}}},
}


@router.post("/wounds/{wound_id}/visits", status_code=201, openapi_extra=VISIT_REQUEST_SCHEMA)
async def create_visit(wound_id: str, request: Request, owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        wound = repository.require_wound(database, wound_id, owner)
        if wound["status"] == "healed":
            raise HTTPException(status_code=409, detail="This wound is marked healed. Reopen it before adding another visit.")

    if not request.headers.get("content-type", "").lower().startswith("multipart/form-data"):
        raise HTTPException(status_code=422, detail="Upload visit_date, optional notes, and 1-5 images as multipart/form-data.")
    validated = []
    # Multipart limits also bound unexpected fields before reading image contents.
    async with request.form(max_files=5, max_fields=8, max_part_size=8192) as form:
        if set(form) - {"visit_date", "notes", "images"}:
            raise HTTPException(status_code=422, detail="Only visit_date, notes, and images are accepted.")
        if len(form.getlist("visit_date")) != 1 or len(form.getlist("notes")) > 1:
            raise HTTPException(status_code=422, detail="Provide one visit date and at most one notes field.")
        try:
            payload = VisitCreate.model_validate({"visit_date": form.get("visit_date"), "notes": form.get("notes", "")})
        except ValidationError:
            raise HTTPException(status_code=422, detail="Use an ISO visit date (YYYY-MM-DD) and notes of at most 2000 characters.")
        uploads = form.getlist("images")
        if not 1 <= len(uploads) <= 5 or any(not isinstance(upload, UploadFile) for upload in uploads):
            raise HTTPException(status_code=422, detail="Each visit requires 1-5 JPEG, PNG or WebP images.")
        for upload in uploads:
            content = await upload.read(MAX_IMAGE_BYTES + 1)
            content_type, extension, filename = validate_image(content, upload.content_type, upload.filename)
            image_id = str(uuid4())
            validated.append({"id": image_id, "content": content, "content_type": content_type, "filename": filename, "storage_name": image_id + extension})

    visit_id = str(uuid4())
    created_files = []
    try:
        with repository.connection() as database:
            # Serialize the status check, duplicate check, files and record insertion.
            database.execute("BEGIN IMMEDIATE")
            wound = repository.require_wound(database, wound_id, owner)
            if wound["status"] == "healed":
                raise HTTPException(status_code=409, detail="This wound is marked healed. Reopen it before adding another visit.")
            database.execute(
                "INSERT INTO wound_visits (id, wound_id, visit_date, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                (visit_id, wound_id, payload.visit_date.isoformat(), payload.notes, timestamp()),
            )
            directory = repository.image_directory()
            directory.mkdir(parents=True, exist_ok=True)
            for item in validated:
                path = directory / item["storage_name"]
                # Record only files opened by this request, for safe rollback cleanup.
                with path.open("xb") as file:
                    created_files.append(path)
                    file.write(item["content"])
                database.execute(
                    "INSERT INTO wound_images VALUES (?, ?, ?, ?, ?, ?)",
                    (item["id"], visit_id, item["filename"], item["storage_name"], item["content_type"], len(item["content"])),
                )
            result = next(visit for visit in repository.list_visits(database, wound_id) if visit["id"] == visit_id)
        return result
    except Exception as error:
        for path in created_files:
            path.unlink(missing_ok=True)
        if isinstance(error, sqlite3.IntegrityError):
            raise HTTPException(status_code=409, detail="This wound already has a visit on that date. Choose a different visit date.")
        raise


@router.get("/images/{image_id}")
def image(image_id: str, owner: str = Depends(current_workspace)):
    with repository.connection() as database:
        row = database.execute(
            """SELECT i.* FROM wound_images i JOIN wound_visits v ON v.id = i.visit_id
               JOIN clinic_wounds w ON w.id = v.wound_id JOIN wound_patients p ON p.id = w.patient_id
               WHERE i.id = ? AND p.owner = ?""", (image_id, owner),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Image not found.")
        directory = repository.image_directory().resolve()
        path = (directory / row["storage_name"]).resolve()
        if not path.is_relative_to(directory) or not path.is_file():
            raise HTTPException(status_code=404, detail="Image not found.")
        return FileResponse(path, media_type=row["content_type"], filename=row["filename"], content_disposition_type="inline", headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/wounds/{wound_id}/progress")
def progress(wound_id: str, model_id: str | None = None, owner: str = Depends(current_workspace)):
    return progress_for_wound(wound_id, owner, model_id)


@router.patch("/visits/{visit_id}/progress-image")
def update_progress_image(visit_id: str, payload: ProgressImageUpdate, owner: str = Depends(current_workspace)):
    return select_progress_image(visit_id, payload.image_id, owner)
