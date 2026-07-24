from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PublishMode(StrEnum):
    DIRECT_POST = "direct_post"
    INBOX_UPLOAD = "inbox_upload"


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    expires_at: datetime


class TikTokConnectionResponse(BaseModel):
    id: str
    open_id: str
    display_name: str | None
    avatar_url: str | None
    scopes: list[str]
    status: str
    is_mock: bool
    access_expires_at: datetime
    refresh_expires_at: datetime
    creator_info_fetched_at: datetime | None


class CreatorInfoResponse(BaseModel):
    connection_id: str
    creator_username: str | None
    creator_nickname: str | None
    creator_avatar_url: str | None
    privacy_level_options: list[str]
    comment_disabled: bool
    duet_disabled: bool
    stitch_disabled: bool
    max_video_post_duration_sec: int
    is_mock: bool
    fetched_at: datetime


class PublicationCreateRequest(BaseModel):
    connection_id: str
    publish_mode: PublishMode
    idempotency_key: str = Field(min_length=12, max_length=100)
    caption: str = Field(default="", max_length=2_200)
    privacy_level: str | None = None
    allow_comment: bool | None = None
    allow_duet: bool | None = None
    allow_stitch: bool | None = None
    brand_content_toggle: bool = False
    brand_organic_toggle: bool = False
    is_aigc: bool = False
    explicit_consent: bool
    music_usage_confirmed: bool
    branded_content_policy_confirmed: bool = False

    @model_validator(mode="after")
    def validate_consent_and_metadata(self):
        if not self.explicit_consent or not self.music_usage_confirmed:
            raise ValueError("O consentimento expresso e a confirmação de uso de música são obrigatórios.")
        if self.publish_mode == PublishMode.DIRECT_POST:
            if not self.privacy_level:
                raise ValueError("Selecione manualmente a privacidade.")
            if None in (self.allow_comment, self.allow_duet, self.allow_stitch):
                raise ValueError("Selecione manualmente as permissões de interação.")
        if self.brand_content_toggle and not self.branded_content_policy_confirmed:
            raise ValueError("Confirme a política de conteúdo de marca.")
        if self.brand_content_toggle and self.privacy_level == "SELF_ONLY":
            raise ValueError("Conteúdo de marca não pode usar visibilidade privada.")
        return self


class PublicationRetryRequest(BaseModel):
    explicit_consent: bool
    music_usage_confirmed: bool

    @model_validator(mode="after")
    def validate_fresh_consent(self):
        if not self.explicit_consent or not self.music_usage_confirmed:
            raise ValueError("Uma nova confirmação explícita é obrigatória para tentar novamente.")
        return self


class PublicationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    created_at: datetime


class PublicationJobResponse(BaseModel):
    id: str
    video_project_id: str
    scheduled_slot_id: str
    connection_id: str
    publish_mode: str
    status: str
    caption: str
    privacy_level: str | None
    scheduled_for: datetime
    publish_id: str | None
    post_id: str | None
    attempts: int
    error_code: str | None
    error_message: str | None
    is_mock: bool
    created_at: datetime
    updated_at: datetime
    events: list[PublicationEventResponse] = Field(default_factory=list)
