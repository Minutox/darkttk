from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LicenseType(StrEnum):
    USER_OWNED = "user_owned"
    LICENSED_STOCK = "licensed_stock"
    PUBLIC_DOMAIN = "public_domain"
    EXPLICIT_PERMISSION = "explicit_permission"
    AI_GENERATED = "ai_generated"


class CaptionStyle(StrEnum):
    MINIMAL = "minimal"
    DYNAMIC = "dynamic"
    WORD_BY_WORD = "word_by_word"
    CINEMATIC = "cinematic"
    EDUCATIONAL = "educational"
    CENTER_HIGHLIGHT = "center_highlight"
    LOWER_HIGHLIGHT = "lower_highlight"


class VoiceProfileCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    provider_voice_id: str = Field(default="mock-neutral-ptbr", min_length=2, max_length=120)
    gender_label: str | None = Field(default=None, max_length=40)
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    speaking_rate: int = Field(default=100, ge=60, le=160)
    pitch: int = Field(default=0, ge=-20, le=20)
    emotion: str = Field(default="neutral", min_length=2, max_length=40)
    consent_reference: str | None = Field(default=None, max_length=255)


class VoiceProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider_key: str
    provider_voice_id: str
    gender_label: str | None
    language: str
    speaking_rate: int
    pitch: int
    emotion: str
    is_mock: bool
    active: bool


class NarrationCreateRequest(BaseModel):
    voice_profile_id: str


class MediaAssetResponse(BaseModel):
    id: str
    kind: str
    origin: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    duration_ms: int | None
    width: int | None
    height: int | None
    status: str
    provider_key: str | None
    is_mock: bool
    license_status: str | None = None
    created_at: datetime


class CaptionGenerateRequest(BaseModel):
    style: CaptionStyle = CaptionStyle.DYNAMIC
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    duration_ms: int | None = Field(default=None, ge=1_000, le=180_000)
    words_per_cue: int = Field(default=5, ge=1, le=10)


class CaptionCueResponse(BaseModel):
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    highlights: list[str]


class CaptionTrackResponse(BaseModel):
    id: str
    script_id: str
    language: str
    style: str
    status: str
    safe_area: dict[str, int]
    cues: list[CaptionCueResponse]
    created_at: datetime


class VideoProjectCreateRequest(BaseModel):
    script_id: str
    title: str = Field(min_length=3, max_length=200)
    voice_profile_id: str | None = None
    narration_asset_id: str | None = None
    caption_track_id: str | None = None
    template_key: str = Field(default="dark-minimal-v1", min_length=3, max_length=80)


class SceneCreateRequest(BaseModel):
    media_asset_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    trim_start_ms: int = Field(default=0, ge=0)
    transition: str = Field(default="cut", pattern="^(cut|fade|dissolve)$")
    motion: str = Field(default="none", pattern="^(none|zoom_in|zoom_out|pan_left|pan_right)$")
    text_overlay: dict[str, object] = Field(default_factory=dict)


class SceneUpdateRequest(BaseModel):
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, gt=0)
    trim_start_ms: int | None = Field(default=None, ge=0)
    transition: str | None = Field(default=None, pattern="^(cut|fade|dissolve)$")
    motion: str | None = Field(
        default=None,
        pattern="^(none|zoom_in|zoom_out|pan_left|pan_right)$",
    )
    text_overlay: dict[str, object] | None = None


class SceneResponse(BaseModel):
    id: str
    sequence: int
    media_asset_id: str | None
    start_ms: int
    end_ms: int
    trim_start_ms: int
    transition: str
    motion: str
    text_overlay: dict[str, object]


class VideoProjectResponse(BaseModel):
    id: str
    script_id: str
    title: str
    status: str
    width: int
    height: int
    fps: int
    duration_ms: int | None
    template_key: str
    narration_asset_id: str | None
    caption_track_id: str | None
    preview_is_mock: bool
    scenes: list[SceneResponse]
    created_at: datetime


class RenderRequest(BaseModel):
    idempotency_key: str = Field(min_length=12, max_length=100)


class RenderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_project_id: str
    status: str
    progress: int
    attempts: int
    output_asset_id: str | None
    error_code: str | None
    created_at: datetime
