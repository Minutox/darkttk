from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetentionImportRequest(BaseModel):
    source: str = Field(pattern="^(manual_tiktok_analytics_export|manual_creator_report)$")
    average_watch_time_seconds: float | None = Field(default=None, ge=0, le=3600)
    completion_rate: float | None = Field(default=None, ge=0, le=1)
    watched_full_rate: float | None = Field(default=None, ge=0, le=1)
    saved_count: int | None = Field(default=None, ge=0)
    retention_curve: list[float] = Field(default_factory=list, max_length=101)
    collected_at: datetime

    @model_validator(mode="after")
    def validate_observation(self):
        if all(
            value is None
            for value in (
                self.average_watch_time_seconds,
                self.completion_rate,
                self.watched_full_rate,
                self.saved_count,
            )
        ) and not self.retention_curve:
            raise ValueError("Informe ao menos uma métrica de retenção.")
        if any(point < 0 or point > 1 for point in self.retention_curve):
            raise ValueError("Cada ponto da curva deve estar entre 0 e 1.")
        return self


class MetricSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    publication_job_id: str
    provider_video_id: str
    view_count: int
    like_count: int
    comment_count: int
    share_count: int
    source: str
    is_mock: bool
    collected_at: datetime


class RetentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    publication_job_id: str
    source: str
    average_watch_time_seconds: float | None
    completion_rate: float | None
    watched_full_rate: float | None
    saved_count: int | None
    retention_curve: list[float]
    collected_at: datetime


class OverviewResponse(BaseModel):
    videos_with_data: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    engagement_rate: float
    follower_count: int | None
    follower_delta: int | None
    average_completion_rate: float | None
    source_notice: str
    is_mock: bool


class RecommendationDecision(StrEnum):
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


class RecommendationDecisionRequest(BaseModel):
    decision: RecommendationDecision


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    title: str
    rationale: str
    confidence: int
    status: str
    created_at: datetime


class ExperimentVariable(StrEnum):
    HOOK = "hook"
    DESCRIPTION = "description"
    CAPTION_STYLE = "caption_style"
    VOICE = "voice"
    DURATION = "duration"
    SCHEDULE = "schedule"
    CTA = "cta"
    SCRIPT_STRUCTURE = "script_structure"


class ExperimentMetric(StrEnum):
    ENGAGEMENT_RATE = "engagement_rate"
    SHARE_RATE = "share_rate"
    COMPLETION_RATE = "completion_rate"
    VIEWS = "views"


class ExperimentVariantRequest(BaseModel):
    label: str = Field(pattern="^[A-Z]$")
    video_project_id: str
    variable_value: str = Field(min_length=1, max_length=500)


class ExperimentCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    hypothesis: str = Field(min_length=10, max_length=1000)
    variable: ExperimentVariable
    primary_metric: ExperimentMetric
    variants: list[ExperimentVariantRequest] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_variants(self):
        if len({item.label for item in self.variants}) != 2:
            raise ValueError("Use dois rótulos distintos.")
        if len({item.video_project_id for item in self.variants}) != 2:
            raise ValueError("Cada variante precisa usar um projeto diferente.")
        if len({item.variable_value.strip().lower() for item in self.variants}) != 2:
            raise ValueError("As variantes precisam testar valores diferentes.")
        return self


class ExperimentStatusRequest(BaseModel):
    status: str = Field(pattern="^(running|completed|cancelled)$")


class ExperimentVariantResponse(BaseModel):
    id: str
    label: str
    video_project_id: str
    variable_value: str
    views: int
    metric_value: float | None


class ExperimentResponse(BaseModel):
    id: str
    name: str
    hypothesis: str
    variable: str
    primary_metric: str
    status: str
    created_at: datetime
    variants: list[ExperimentVariantResponse]
    winner_label: str | None
