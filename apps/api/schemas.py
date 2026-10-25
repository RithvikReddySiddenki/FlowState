"""Public API schemas. Action reminders are independent of recruiting stage."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints, model_validator


class Stage(str, Enum):
    RECEIVED = "Application Received"
    REVIEW = "Under Review"
    ASSESSMENT = "Assessment Invite"
    INTERVIEW = "Interview Scheduled"
    OFFER = "Offer"
    REJECTED = "Rejected"


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class CreateApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: Name
    role: Name
    current_status: Stage = Stage.RECEIVED
    action_required: bool = False
    deadline: AwareDatetime | None = None


class UpdateApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: Name | None = None
    role: Name | None = None
    current_status: Stage | None = None
    action_required: bool | None = None
    deadline: AwareDatetime | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for key in self.model_fields_set - {"deadline"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        return self


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: str
    role: str
    current_status: Stage
    action_required: bool
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime


class HistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    previous_status: str | None
    current_status: str
    source: str
    source_message_id: int | None
    created_at: datetime
