from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class BlockedTopicKind(StrEnum):
    KEYWORD = "keyword"
    TOPIC = "topic"
    CATEGORY = "category"


class ScriptStyle(StrEnum):
    EDUCATIONAL = "educational"
    INSPIRATIONAL = "inspirational"
    CURIOUS = "curious"
    DRAMATIC = "dramatic"
    REFLECTIVE = "reflective"
    HUMOROUS = "humorous"
    DOCUMENTARY = "documentary"
    CINEMATIC = "cinematic"
    QUICK_LIST = "quick_list"
    NARRATED_STORY = "narrated_story"
    PROBLEM_SOLUTION = "problem_solution"
    MYTH_TRUTH = "myth_truth"


class NicheResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    description: str | None
    enabled: bool
    is_custom: bool


class NicheUpdateRequest(BaseModel):
    enabled: bool


class BlockedTopicCreateRequest(BaseModel):
    term: str = Field(min_length=2, max_length=160)
    kind: BlockedTopicKind


class BlockedTopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    term: str
    kind: str
    active: bool
    created_at: datetime


class IdeaCreateRequest(BaseModel):
    niche_id: str
    topic: str = Field(min_length=3, max_length=200)
    creative_angle: str = Field(min_length=5, max_length=1000)
    content_promise: str = Field(min_length=5, max_length=1000)
    hook: str = Field(min_length=5, max_length=500)
    narrative_structure: str = Field(min_length=5, max_length=1000)
    key_information: str = Field(min_length=5, max_length=2000)
    call_to_action: str = Field(min_length=2, max_length=500)
    visual_suggestion: str = Field(min_length=5, max_length=1000)
    duration_seconds: int = Field(ge=15, le=180)
    target_audience: str = Field(min_length=3, max_length=180)
    objective: str = Field(min_length=3, max_length=120)


class IdeaGenerateRequest(BaseModel):
    niche_id: str
    topic: str = Field(min_length=3, max_length=200)
    objective: str = Field(default="retenção e valor educativo", min_length=3, max_length=120)


class IdeaResponse(BaseModel):
    id: str
    niche_id: str
    mode: str
    topic: str
    creative_angle: str
    content_promise: str
    hook: str
    narrative_structure: str
    key_information: str
    call_to_action: str
    visual_suggestion: str
    duration_seconds: int
    target_audience: str
    objective: str
    status: str
    risk_level: str
    provider_key: str | None
    provider_is_mock: bool
    created_at: datetime


class ScriptGenerateRequest(BaseModel):
    style: ScriptStyle = ScriptStyle.DOCUMENTARY
    duration_seconds: int | None = Field(default=None, ge=15, le=180)


class ScriptRevisionRequest(BaseModel):
    content: str = Field(min_length=40, max_length=12000)
    style: ScriptStyle
    reason: str = Field(min_length=3, max_length=500)


class ScriptResponse(BaseModel):
    id: str
    idea_id: str
    version: int
    style: str
    content: str
    status: str
    moderation_status: str
    fact_check_status: str
    provider_key: str | None
    provider_is_mock: bool
    created_at: datetime


class SourceCreateRequest(BaseModel):
    url: HttpUrl
    title: str = Field(min_length=3, max_length=300)
    publisher: str = Field(min_length=2, max_length=180)
    trust_score: int = Field(ge=0, le=100)
    license_note: str | None = Field(default=None, max_length=1000)


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    title: str
    publisher: str
    trust_score: int
    license_note: str | None


class FactCheckResponse(BaseModel):
    id: str
    claim: str
    verdict: str
    confidence: int
    evidence: str
    provider_key: str
    provider_is_mock: bool
    created_at: datetime


class ContentHistoryResponse(BaseModel):
    id: str
    event_type: str
    subject_type: str
    subject_id: str
    actor_id: str | None
    payload: dict[str, object]
    created_at: datetime


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    capability: str
    provider_key: str
    display_name: str
    enabled: bool
    is_mock: bool
    secret_configured: bool


class ProviderUpdateRequest(BaseModel):
    enabled: bool
    secret_ref: str | None = Field(default=None, min_length=3, max_length=255)
