BEGIN;

CREATE TABLE voice_profiles (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    provider_key VARCHAR(60) NOT NULL,
    provider_voice_id VARCHAR(120) NOT NULL,
    gender_label VARCHAR(40),
    language VARCHAR(20) NOT NULL DEFAULT 'pt-BR',
    speaking_rate INTEGER NOT NULL DEFAULT 100 CHECK (speaking_rate BETWEEN 60 AND 160),
    pitch INTEGER NOT NULL DEFAULT 0 CHECK (pitch BETWEEN -20 AND 20),
    emotion VARCHAR(40) NOT NULL DEFAULT 'neutral',
    is_mock BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    consent_reference VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_voice_org_name UNIQUE (organization_id, name)
);
CREATE INDEX ix_voice_profiles_org ON voice_profiles (organization_id);

CREATE TABLE media_assets (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('image', 'video', 'audio', 'caption', 'render', 'manifest')),
    origin VARCHAR(30) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_key VARCHAR(500) NOT NULL UNIQUE,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256 VARCHAR(64) NOT NULL,
    duration_ms INTEGER,
    width INTEGER,
    height INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'ready',
    provider_key VARCHAR(60),
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_asset_org_sha256 UNIQUE (organization_id, sha256)
);
CREATE INDEX ix_assets_org_kind_status ON media_assets (organization_id, kind, status);

CREATE TABLE media_licenses (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    asset_id VARCHAR(36) NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    license_type VARCHAR(40) NOT NULL CHECK (
        license_type IN ('user_owned', 'licensed_stock', 'public_domain', 'explicit_permission', 'ai_generated')
    ),
    source_url TEXT,
    attribution TEXT,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    proof_storage_key VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'valid' CHECK (status IN ('valid', 'expired', 'revoked', 'pending')),
    reviewed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_license_asset UNIQUE (asset_id)
);
CREATE INDEX ix_licenses_org_status ON media_licenses (organization_id, status);

CREATE TABLE caption_tracks (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    script_id VARCHAR(36) NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    language VARCHAR(20) NOT NULL DEFAULT 'pt-BR',
    style VARCHAR(40) NOT NULL DEFAULT 'dynamic',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    safe_area_json TEXT NOT NULL DEFAULT '{"top":180,"right":80,"bottom":320,"left":80}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_caption_tracks_org ON caption_tracks (organization_id);
CREATE INDEX ix_caption_tracks_script ON caption_tracks (script_id);

CREATE TABLE caption_cues (
    id VARCHAR(36) PRIMARY KEY,
    track_id VARCHAR(36) NOT NULL REFERENCES caption_tracks(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    start_ms INTEGER NOT NULL CHECK (start_ms >= 0),
    end_ms INTEGER NOT NULL CHECK (end_ms > start_ms),
    text TEXT NOT NULL,
    highlight_words_json TEXT NOT NULL DEFAULT '[]',
    CONSTRAINT uq_caption_track_sequence UNIQUE (track_id, sequence)
);
CREATE INDEX ix_caption_track_time ON caption_cues (track_id, start_ms);

CREATE TABLE video_projects (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    script_id VARCHAR(36) NOT NULL REFERENCES scripts(id) ON DELETE RESTRICT,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    voice_profile_id VARCHAR(36) REFERENCES voice_profiles(id) ON DELETE SET NULL,
    narration_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE SET NULL,
    caption_track_id VARCHAR(36) REFERENCES caption_tracks(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'assembling', 'queued', 'rendering', 'preview_mock', 'review',
                   'approved', 'scheduled', 'published', 'failed', 'archived')
    ),
    width INTEGER NOT NULL DEFAULT 1080 CHECK (width > 0),
    height INTEGER NOT NULL DEFAULT 1920 CHECK (height > 0),
    fps INTEGER NOT NULL DEFAULT 30 CHECK (fps BETWEEN 1 AND 120),
    duration_ms INTEGER,
    template_key VARCHAR(80) NOT NULL DEFAULT 'dark-minimal-v1',
    preview_manifest_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_video_projects_org_status ON video_projects (organization_id, status);

CREATE TABLE video_scenes (
    id VARCHAR(36) PRIMARY KEY,
    video_project_id VARCHAR(36) NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
    media_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE SET NULL,
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    start_ms INTEGER NOT NULL CHECK (start_ms >= 0),
    end_ms INTEGER NOT NULL CHECK (end_ms > start_ms),
    trim_start_ms INTEGER NOT NULL DEFAULT 0 CHECK (trim_start_ms >= 0),
    text_overlay_json TEXT NOT NULL DEFAULT '{}',
    transition VARCHAR(40) NOT NULL DEFAULT 'cut',
    motion VARCHAR(40) NOT NULL DEFAULT 'none',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_scene_project_sequence UNIQUE (video_project_id, sequence)
);
CREATE INDEX ix_video_scenes_project ON video_scenes (video_project_id);

CREATE TABLE render_jobs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    video_project_id VARCHAR(36) NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
    requested_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    payload_hash VARCHAR(64) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'queued' CHECK (
        status IN ('queued', 'running', 'mock_ready', 'succeeded', 'failed', 'dispatch_failed', 'dead_letter')
    ),
    progress INTEGER NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    output_asset_id VARCHAR(36) REFERENCES media_assets(id) ON DELETE SET NULL,
    error_code VARCHAR(80),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_render_jobs_org ON render_jobs (organization_id);
CREATE INDEX ix_render_jobs_project ON render_jobs (video_project_id);
CREATE INDEX ix_render_jobs_status_created ON render_jobs (status, created_at);

COMMIT;
