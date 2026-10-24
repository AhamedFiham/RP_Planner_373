"""Input contracts for the clinic workflow, independent of future model inference."""

from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClinicInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PatientCreate(ClinicInput):
    patient_code: str = Field(min_length=2, max_length=40)
    display_name: str = Field(min_length=2, max_length=100)
    notes: str = Field(default="", max_length=2000)

    @field_validator("patient_code", "display_name")
    @classmethod
    def printable_text(cls, value):
        if any(ord(character) < 32 for character in value):
            raise ValueError("Use printable text.")
        return value


class WoundCreate(ClinicInput):
    label: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)
    onset_date: date | None = None
    status: Literal["active", "healed"] = "active"
    notes: str = Field(default="", max_length=2000)


class WoundStatusUpdate(ClinicInput):
    status: Literal["active", "healed"]


class AnalysisCreate(ClinicInput):
    stage: Literal["wound_segmentation", "tissue_segmentation"]
    model_id: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class ProgressImageUpdate(ClinicInput):
    image_id: str = Field(min_length=1, max_length=80)


class VisitCreate(ClinicInput):
    visit_date: date
    notes: str = Field(default="", max_length=2000)

    @field_validator("visit_date", mode="before")
    @classmethod
    def iso_date_only(cls, value):
        if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("Use an ISO date (YYYY-MM-DD).")
        return value
