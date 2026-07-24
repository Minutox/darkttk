from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalSubmitRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2_000)


class ApprovalDecisionRequest(BaseModel):
    decision: ApprovalDecision
    note: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def require_note_for_negative_decision(self):
        if self.decision != ApprovalDecision.APPROVED and not (self.note or "").strip():
            raise ValueError("Informe o motivo da reprovação ou das alterações.")
        return self


class ProjectWorkflowEditRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    template_key: str | None = Field(default=None, min_length=3, max_length=80)

    @model_validator(mode="after")
    def require_change(self):
        if self.title is None and self.template_key is None:
            raise ValueError("Informe ao menos uma alteração.")
        return self


class ApprovalEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str
    event_type: str
    note: str | None
    created_at: datetime


class ApprovalResponse(BaseModel):
    id: str
    video_project_id: str
    project_title: str
    project_status: str
    preview_is_mock: bool
    version: int
    status: str
    requested_by: str
    decided_by: str | None
    request_note: str | None
    decision_note: str | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    events: list[ApprovalEventResponse] = Field(default_factory=list)


class ScheduleCreateRequest(BaseModel):
    scheduled_for: datetime
    timezone: str = Field(default="America/Sao_Paulo", min_length=3, max_length=64)
    note: str | None = Field(default=None, max_length=1_000)


class ScheduleUpdateRequest(BaseModel):
    scheduled_for: datetime
    timezone: str = Field(default="America/Sao_Paulo", min_length=3, max_length=64)
    note: str | None = Field(default=None, max_length=1_000)


class ScheduleResponse(BaseModel):
    id: str
    video_project_id: str
    project_title: str
    approval_request_id: str
    scheduled_for: datetime
    timezone: str
    status: str
    note: str | None
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    title: str
    message: str
    entity_type: str | None
    entity_id: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    unread_count: int
    items: list[NotificationResponse]
