from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TrendSourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    connector_type: str = Field(pattern="^(api|rss|manual_import)$")
    endpoint_url: HttpUrl | None = None
    terms_url: HttpUrl
    authorization_confirmed: bool


class TrendSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    connector_type: str
    endpoint_url: str | None
    terms_url: str
    authorized_at: datetime
    enabled: bool


class TrendSignalCreate(BaseModel):
    source_id: str
    topic: str = Field(min_length=3, max_length=200)
    category: str = Field(min_length=2, max_length=100)
    relevance_reason: str = Field(min_length=10, max_length=1000)
    growth_percent: float = Field(ge=-100, le=100_000)
    interest_volume: int = Field(ge=0)
    competition: str = Field(pattern="^(low|medium|high)$")
    retention_score: int = Field(ge=0, le=100)
    share_score: int = Field(ge=0, le=100)
    sensitivity_risk: str = Field(pattern="^(low|medium|high|blocked)$")
    saturation_risk: str = Field(pattern="^(low|medium|high)$")
    suggested_approach: str = Field(min_length=5, max_length=1000)
    likely_audience: str = Field(min_length=3, max_length=180)
    valid_until: datetime


class TrendSignalResponse(TrendSignalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    captured_at: datetime


class ContentSeriesCreate(BaseModel):
    name: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=10, max_length=1200)
    niche_id: str | None = None
    cadence: str = Field(pattern="^(daily|weekdays|weekly|biweekly|monthly)$")
    target_episode_count: int = Field(ge=2, le=365)


class ContentSeriesResponse(ContentSeriesCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_at: datetime
