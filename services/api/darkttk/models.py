from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_string() -> str:
    return str(uuid4())


class UserStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    ANALYST = "analyst"
    VIEWER = "viewer"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    SELECTED = "selected"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class AssetKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CAPTION = "caption"
    RENDER = "render"
    DOCUMENT = "document"


class AssetStatus(StrEnum):
    UPLOADING = "uploading"
    READY = "ready"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    CANCELLED = "cancelled"


class ScheduleStatus(StrEnum):
    RESERVED = "reserved"
    READY = "ready"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TikTokConnectionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class PublicationStatus(StrEnum):
    QUEUED = "queued"
    INITIALIZING = "initializing"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    INBOX_DELIVERED = "inbox_delivered"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"
    MOCK_COMPLETE = "mock_complete"


class RecommendationStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=OrganizationStatus.ACTIVE.value
    )

    memberships: Mapped[list[OrganizationMember]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(TimestampMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_member_org_user"),
        Index("ix_members_org_role", "organization_id", "role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))

    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_user_active", "user_id", "revoked_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_jti: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class PasswordRecoveryToken(Base):
    __tablename__ = "password_recovery_tokens"
    __table_args__ = (
        Index("ix_password_recovery_user_created", "user_id", "created_at"),
        Index("ix_password_recovery_hash", "token_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class MfaCredential(TimestampMixin, Base):
    __tablename__ = "mfa_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_mfa_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    secret_ciphertext: Mapped[str] = mapped_column(Text)
    recovery_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_step: Mapped[int | None] = mapped_column(BigInteger)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"
    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_setting_org_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(100))
    value_json: Mapped[str] = mapped_column(Text)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)


class ContentNiche(TimestampMixin, Base):
    __tablename__ = "content_niches"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_niche_org_slug"),
        Index("ix_niches_org_enabled", "organization_id", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)


class BlockedTopic(TimestampMixin, Base):
    __tablename__ = "blocked_topics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "normalized_term", "kind", name="uq_blocked_org_term_kind"
        ),
        Index("ix_blocked_org_active", "organization_id", "active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    term: Mapped[str] = mapped_column(String(160))
    normalized_term: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class AiProvider(TimestampMixin, Base):
    __tablename__ = "ai_providers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "capability", "provider_key", name="uq_provider_capability"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    capability: Mapped[str] = mapped_column(String(40))
    provider_key: Mapped[str] = mapped_column(String(60))
    display_name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    secret_ref: Mapped[str | None] = mapped_column(String(255))


class ContentIdea(TimestampMixin, Base):
    __tablename__ = "content_ideas"
    __table_args__ = (
        Index("ix_ideas_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_ideas_org_niche", "organization_id", "niche_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    niche_id: Mapped[str] = mapped_column(
        ForeignKey("content_niches.id", ondelete="RESTRICT"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    mode: Mapped[str] = mapped_column(String(30), default="manual")
    topic: Mapped[str] = mapped_column(String(200))
    creative_angle: Mapped[str] = mapped_column(Text)
    content_promise: Mapped[str] = mapped_column(Text)
    hook: Mapped[str] = mapped_column(Text)
    narrative_structure: Mapped[str] = mapped_column(Text)
    key_information: Mapped[str] = mapped_column(Text)
    call_to_action: Mapped[str] = mapped_column(Text)
    visual_suggestion: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    target_audience: Mapped[str] = mapped_column(String(180))
    objective: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default=ContentStatus.DRAFT.value)
    risk_level: Mapped[str] = mapped_column(String(20), default=RiskLevel.LOW.value)
    provider_key: Mapped[str | None] = mapped_column(String(60))


class Script(TimestampMixin, Base):
    __tablename__ = "scripts"
    __table_args__ = (
        UniqueConstraint("idea_id", "version", name="uq_script_idea_version"),
        Index("ix_scripts_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    idea_id: Mapped[str] = mapped_column(
        ForeignKey("content_ideas.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer)
    style: Mapped[str] = mapped_column(String(40))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    moderation_status: Mapped[str] = mapped_column(
        String(20), default=ReviewStatus.PENDING.value
    )
    fact_check_status: Mapped[str] = mapped_column(
        String(20), default=ReviewStatus.PENDING.value
    )
    provider_key: Mapped[str | None] = mapped_column(String(60))


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("organization_id", "url", name="uq_source_org_url"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(300))
    publisher: Mapped[str] = mapped_column(String(180))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    trust_score: Mapped[int] = mapped_column(Integer)
    license_note: Mapped[str | None] = mapped_column(Text)


class ScriptSource(Base):
    __tablename__ = "script_sources"
    __table_args__ = (
        UniqueConstraint("script_id", "source_id", name="uq_script_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    script_id: Mapped[str] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class FactCheck(Base):
    __tablename__ = "fact_checks"
    __table_args__ = (
        Index("ix_fact_checks_script", "script_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    script_id: Mapped[str] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL")
    )
    claim: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[int] = mapped_column(Integer)
    evidence: Mapped[str] = mapped_column(Text)
    provider_key: Mapped[str] = mapped_column(String(60))
    reviewed_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ModerationCheck(Base):
    __tablename__ = "moderation_checks"
    __table_args__ = (
        Index("ix_moderation_subject", "subject_type", "subject_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    subject_type: Mapped[str] = mapped_column(String(40))
    subject_id: Mapped[str] = mapped_column(String(36))
    stage: Mapped[str] = mapped_column(String(30))
    result: Mapped[str] = mapped_column(String(20))
    matched_rules_json: Mapped[str] = mapped_column(Text, default="[]")
    policy_version: Mapped[str] = mapped_column(String(20), default="2026-07")
    provider_key: Mapped[str] = mapped_column(String(60), default="darkttk-policy")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ContentEvent(Base):
    __tablename__ = "content_events"
    __table_args__ = (
        Index("ix_content_events_subject", "subject_type", "subject_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    subject_type: Mapped[str] = mapped_column(String(40))
    subject_id: Mapped[str] = mapped_column(String(36))
    event_type: Mapped[str] = mapped_column(String(80))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class VoiceProfile(TimestampMixin, Base):
    __tablename__ = "voice_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_voice_org_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(100))
    provider_key: Mapped[str] = mapped_column(String(60))
    provider_voice_id: Mapped[str] = mapped_column(String(120))
    gender_label: Mapped[str | None] = mapped_column(String(40))
    language: Mapped[str] = mapped_column(String(20), default="pt-BR")
    speaking_rate: Mapped[int] = mapped_column(Integer, default=100)
    pitch: Mapped[int] = mapped_column(Integer, default=0)
    emotion: Mapped[str] = mapped_column(String(40), default="neutral")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_reference: Mapped[str | None] = mapped_column(String(255))


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "sha256", name="uq_asset_org_sha256"),
        Index("ix_assets_org_kind_status", "organization_id", "kind", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(20))
    origin: Mapped[str] = mapped_column(String(30))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=AssetStatus.READY.value)
    provider_key: Mapped[str | None] = mapped_column(String(60))
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)


class MediaLicense(TimestampMixin, Base):
    __tablename__ = "media_licenses"
    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_license_asset"),
        Index("ix_licenses_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"), index=True
    )
    license_type: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proof_storage_key: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="valid")
    reviewed_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class CaptionTrack(TimestampMixin, Base):
    __tablename__ = "caption_tracks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    script_id: Mapped[str] = mapped_column(
        ForeignKey("scripts.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    language: Mapped[str] = mapped_column(String(20), default="pt-BR")
    style: Mapped[str] = mapped_column(String(40), default="dynamic")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    safe_area_json: Mapped[str] = mapped_column(
        Text, default='{"top":180,"right":80,"bottom":320,"left":80}'
    )


class CaptionCue(Base):
    __tablename__ = "caption_cues"
    __table_args__ = (
        UniqueConstraint("track_id", "sequence", name="uq_caption_track_sequence"),
        Index("ix_caption_track_time", "track_id", "start_ms"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    track_id: Mapped[str] = mapped_column(
        ForeignKey("caption_tracks.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    highlight_words_json: Mapped[str] = mapped_column(Text, default="[]")


class VideoProject(TimestampMixin, Base):
    __tablename__ = "video_projects"
    __table_args__ = (
        Index("ix_video_projects_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    script_id: Mapped[str] = mapped_column(
        ForeignKey("scripts.id", ondelete="RESTRICT"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    voice_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("voice_profiles.id", ondelete="SET NULL")
    )
    narration_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    caption_track_id: Mapped[str | None] = mapped_column(
        ForeignKey("caption_tracks.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    width: Mapped[int] = mapped_column(Integer, default=1080)
    height: Mapped[int] = mapped_column(Integer, default=1920)
    fps: Mapped[int] = mapped_column(Integer, default=30)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    template_key: Mapped[str] = mapped_column(String(80), default="dark-minimal-v1")
    preview_manifest_json: Mapped[str | None] = mapped_column(Text)


class VideoScene(TimestampMixin, Base):
    __tablename__ = "video_scenes"
    __table_args__ = (
        UniqueConstraint("video_project_id", "sequence", name="uq_scene_project_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    video_project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), index=True
    )
    media_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    trim_start_ms: Mapped[int] = mapped_column(Integer, default=0)
    text_overlay_json: Mapped[str] = mapped_column(Text, default="{}")
    transition: Mapped[str] = mapped_column(String(40), default="cut")
    motion: Mapped[str] = mapped_column(String(40), default="none")


class RenderJob(TimestampMixin, Base):
    __tablename__ = "render_jobs"
    __table_args__ = (
        Index("ix_render_jobs_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    video_project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), index=True
    )
    requested_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    output_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL")
    )
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_approval_project_version", "video_project_id", "version"),
        UniqueConstraint("video_project_id", "version", name="uq_approval_project_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    video_project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), index=True
    )
    requested_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(30), default=ApprovalStatus.PENDING.value
    )
    request_note: Mapped[str | None] = mapped_column(Text)
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalEvent(Base):
    __tablename__ = "approval_events"
    __table_args__ = (
        Index("ix_approval_events_request_created", "approval_request_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    approval_request_id: Mapped[str] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    event_type: Mapped[str] = mapped_column(String(40))
    note: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ScheduledSlot(TimestampMixin, Base):
    __tablename__ = "scheduled_slots"
    __table_args__ = (
        Index("ix_schedule_org_time", "organization_id", "scheduled_for"),
        Index("ix_schedule_project_status", "video_project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    video_project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), index=True
    )
    approval_request_id: Mapped[str] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="RESTRICT")
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    status: Mapped[str] = mapped_column(
        String(20), default=ScheduleStatus.RESERVED.value
    )
    note: Mapped[str | None] = mapped_column(Text)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_read", "recipient_id", "read_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    recipient_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TikTokOAuthState(Base):
    __tablename__ = "tiktok_oauth_states"
    __table_args__ = (Index("ix_tiktok_oauth_expiry", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    redirect_after: Mapped[str] = mapped_column(String(255), default="/")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TikTokConnection(TimestampMixin, Base):
    __tablename__ = "tiktok_connections"
    __table_args__ = (
        UniqueConstraint("organization_id", "open_id", name="uq_tiktok_org_open_id"),
        Index("ix_tiktok_connections_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    connected_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    open_id: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str | None] = mapped_column(String(160))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    access_token_ciphertext: Mapped[str] = mapped_column(Text)
    refresh_token_ciphertext: Mapped[str] = mapped_column(Text)
    scopes_json: Mapped[str] = mapped_column(Text, default="[]")
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), default=TikTokConnectionStatus.ACTIVE.value
    )
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    creator_info_json: Mapped[str | None] = mapped_column(Text)
    creator_info_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_error_code: Mapped[str | None] = mapped_column(String(100))


class PublicationJob(TimestampMixin, Base):
    __tablename__ = "publication_jobs"
    __table_args__ = (
        Index("ix_publication_org_status", "organization_id", "status"),
        Index("ix_publication_due", "status", "scheduled_for"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    video_project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="CASCADE"), index=True
    )
    scheduled_slot_id: Mapped[str] = mapped_column(
        ForeignKey("scheduled_slots.id", ondelete="RESTRICT"), index=True
    )
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("tiktok_connections.id", ondelete="RESTRICT"), index=True
    )
    requested_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    output_asset_id: Mapped[str] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    publish_mode: Mapped[str] = mapped_column(String(30), default="direct_post")
    caption: Mapped[str] = mapped_column(Text, default="")
    privacy_level: Mapped[str | None] = mapped_column(String(50))
    disable_comment: Mapped[bool] = mapped_column(Boolean, default=True)
    disable_duet: Mapped[bool] = mapped_column(Boolean, default=True)
    disable_stitch: Mapped[bool] = mapped_column(Boolean, default=True)
    brand_content_toggle: Mapped[bool] = mapped_column(Boolean, default=False)
    brand_organic_toggle: Mapped[bool] = mapped_column(Boolean, default=False)
    is_aigc: Mapped[bool] = mapped_column(Boolean, default=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(30), default=PublicationStatus.QUEUED.value
    )
    publish_id: Mapped[str | None] = mapped_column(String(128))
    post_id: Mapped[str | None] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    provider_log_id: Mapped[str | None] = mapped_column(String(128))
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)


class PublicationEvent(Base):
    __tablename__ = "publication_events"
    __table_args__ = (
        Index("ix_publication_events_job_created", "publication_job_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    publication_job_id: Mapped[str] = mapped_column(
        ForeignKey("publication_jobs.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(60))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TikTokWebhookReceipt(Base):
    __tablename__ = "tiktok_webhook_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    delivery_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    open_id: Mapped[str | None] = mapped_column(String(128))
    payload_json: Mapped[str] = mapped_column(Text)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class PublicationMetricSnapshot(Base):
    __tablename__ = "publication_metric_snapshots"
    __table_args__ = (
        Index("ix_metric_org_collected", "organization_id", "collected_at"),
        Index("ix_metric_job_collected", "publication_job_id", "collected_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    publication_job_id: Mapped[str] = mapped_column(
        ForeignKey("publication_jobs.id", ondelete="CASCADE"), index=True
    )
    provider_video_id: Mapped[str] = mapped_column(String(128))
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default="display_api")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class AccountMetricSnapshot(Base):
    __tablename__ = "account_metric_snapshots"
    __table_args__ = (
        Index("ix_account_metric_connection_collected", "connection_id", "collected_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("tiktok_connections.id", ondelete="CASCADE"), index=True
    )
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    video_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(40), default="display_api")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class RetentionObservation(Base):
    __tablename__ = "retention_observations"
    __table_args__ = (
        Index("ix_retention_job_collected", "publication_job_id", "collected_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    publication_job_id: Mapped[str] = mapped_column(
        ForeignKey("publication_jobs.id", ondelete="CASCADE"), index=True
    )
    imported_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    source: Mapped[str] = mapped_column(String(50))
    average_watch_time_seconds: Mapped[float | None] = mapped_column(Float)
    completion_rate: Mapped[float | None] = mapped_column(Float)
    watched_full_rate: Mapped[float | None] = mapped_column(Float)
    saved_count: Mapped[int | None] = mapped_column(Integer)
    curve_json: Mapped[str] = mapped_column(Text, default="[]")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class AnalyticsRecommendation(TimestampMixin, Base):
    __tablename__ = "analytics_recommendations"
    __table_args__ = (
        UniqueConstraint("organization_id", "evidence_hash", name="uq_recommendation_evidence"),
        Index("ix_recommendation_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(180))
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    evidence_hash: Mapped[str] = mapped_column(String(64))
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(
        String(20), default=RecommendationStatus.OPEN.value
    )
    decided_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContentExperiment(TimestampMixin, Base):
    __tablename__ = "content_experiments"
    __table_args__ = (
        Index("ix_experiment_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(160))
    hypothesis: Mapped[str] = mapped_column(Text)
    variable: Mapped[str] = mapped_column(String(40))
    primary_metric: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(
        String(20), default=ExperimentStatus.DRAFT.value
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"
    __table_args__ = (
        UniqueConstraint("experiment_id", "label", name="uq_experiment_variant_label"),
        UniqueConstraint("experiment_id", "video_project_id", name="uq_experiment_variant_project"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    experiment_id: Mapped[str] = mapped_column(
        ForeignKey("content_experiments.id", ondelete="CASCADE"), index=True
    )
    video_project_id: Mapped[str] = mapped_column(
        ForeignKey("video_projects.id", ondelete="RESTRICT"), index=True
    )
    label: Mapped[str] = mapped_column(String(20))
    variable_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class OperationalError(Base):
    __tablename__ = "operational_errors"
    __table_args__ = (
        Index("ix_operational_error_status_seen", "status", "last_seen_at"),
        Index("ix_operational_error_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    service: Mapped[str] = mapped_column(String(60))
    code: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20), default="error")
    status: Mapped[str] = mapped_column(String(20), default="open")
    message_sanitized: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    request_id: Mapped[str | None] = mapped_column(String(64))
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    corrective_action: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CostBudget(TimestampMixin, Base):
    __tablename__ = "cost_budgets"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_cost_budget_org"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    monthly_limit_cents: Mapped[int] = mapped_column(Integer)
    warning_percent: Mapped[int] = mapped_column(Integer, default=80)
    hard_stop_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    updated_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class CostLedgerEntry(Base):
    __tablename__ = "cost_ledger_entries"
    __table_args__ = (
        Index("ix_cost_org_occurred", "organization_id", "occurred_at"),
        UniqueConstraint("organization_id", "source_ref", name="uq_cost_org_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(40))
    amount_micros: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit: Mapped[str] = mapped_column(String(30), default="operation")
    source_ref: Mapped[str] = mapped_column(String(160))
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class BackupRun(Base):
    __tablename__ = "backup_runs"
    __table_args__ = (Index("ix_backup_environment_started", "environment", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    environment: Mapped[str] = mapped_column(String(30))
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    storage_key: Mapped[str | None] = mapped_column(Text)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))


class AuditCheckpoint(Base):
    __tablename__ = "audit_checkpoints"
    __table_args__ = (Index("ix_audit_checkpoint_org_created", "organization_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    from_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    to_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_count: Mapped[int] = mapped_column(Integer)
    digest_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TrendSource(TimestampMixin, Base):
    __tablename__ = "trend_sources"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_trend_source_org_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    connector_type: Mapped[str] = mapped_column(String(30))
    endpoint_url: Mapped[str | None] = mapped_column(Text)
    terms_url: Mapped[str] = mapped_column(Text)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class TrendSignal(TimestampMixin, Base):
    __tablename__ = "trends"
    __table_args__ = (
        Index("ix_trends_org_captured", "organization_id", "captured_at"),
        Index("ix_trends_source_topic", "source_id", "topic"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("trend_sources.id", ondelete="RESTRICT"), index=True
    )
    topic: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    relevance_reason: Mapped[str] = mapped_column(Text)
    growth_percent: Mapped[float] = mapped_column(Float)
    interest_volume: Mapped[int] = mapped_column(Integer)
    competition: Mapped[str] = mapped_column(String(20))
    retention_score: Mapped[int] = mapped_column(Integer)
    share_score: Mapped[int] = mapped_column(Integer)
    sensitivity_risk: Mapped[str] = mapped_column(String(20))
    saturation_risk: Mapped[str] = mapped_column(String(20))
    suggested_approach: Mapped[str] = mapped_column(Text)
    likely_audience: Mapped[str] = mapped_column(String(180))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ContentSeries(TimestampMixin, Base):
    __tablename__ = "content_series"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_content_series_org_name"),
        Index("ix_content_series_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    niche_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_niches.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str] = mapped_column(Text)
    cadence: Mapped[str] = mapped_column(String(40))
    target_episode_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="active")
