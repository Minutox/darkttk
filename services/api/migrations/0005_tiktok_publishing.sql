BEGIN;

ALTER TABLE scheduled_slots DROP CONSTRAINT IF EXISTS scheduled_slots_status_check;
ALTER TABLE scheduled_slots ADD CONSTRAINT scheduled_slots_status_check CHECK (
    status IN ('reserved', 'ready', 'publishing', 'published', 'failed', 'cancelled')
);

CREATE TABLE tiktok_oauth_states (
    id VARCHAR(36) PRIMARY KEY,
    state_hash VARCHAR(64) NOT NULL UNIQUE,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    redirect_after VARCHAR(255) NOT NULL DEFAULT '/',
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_tiktok_oauth_expiry ON tiktok_oauth_states (expires_at);

CREATE TABLE tiktok_connections (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    connected_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    open_id VARCHAR(128) NOT NULL,
    display_name VARCHAR(160),
    avatar_url TEXT,
    access_token_ciphertext TEXT NOT NULL,
    refresh_token_ciphertext TEXT NOT NULL,
    scopes_json TEXT NOT NULL DEFAULT '[]',
    access_expires_at TIMESTAMPTZ NOT NULL,
    refresh_expires_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'expired', 'revoked', 'error')),
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    creator_info_json TEXT,
    creator_info_fetched_at TIMESTAMPTZ,
    last_error_code VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tiktok_org_open_id UNIQUE (organization_id, open_id)
);
CREATE INDEX ix_tiktok_connections_org_status ON tiktok_connections (organization_id, status);

CREATE TABLE publication_jobs (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    video_project_id VARCHAR(36) NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
    scheduled_slot_id VARCHAR(36) NOT NULL REFERENCES scheduled_slots(id) ON DELETE RESTRICT,
    connection_id VARCHAR(36) NOT NULL REFERENCES tiktok_connections(id) ON DELETE RESTRICT,
    requested_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    output_asset_id VARCHAR(36) NOT NULL REFERENCES media_assets(id) ON DELETE RESTRICT,
    idempotency_key VARCHAR(160) NOT NULL UNIQUE,
    payload_hash VARCHAR(64) NOT NULL,
    publish_mode VARCHAR(30) NOT NULL DEFAULT 'direct_post'
        CHECK (publish_mode IN ('direct_post', 'inbox_upload')),
    caption TEXT NOT NULL DEFAULT '',
    privacy_level VARCHAR(50),
    disable_comment BOOLEAN NOT NULL DEFAULT TRUE,
    disable_duet BOOLEAN NOT NULL DEFAULT TRUE,
    disable_stitch BOOLEAN NOT NULL DEFAULT TRUE,
    brand_content_toggle BOOLEAN NOT NULL DEFAULT FALSE,
    brand_organic_toggle BOOLEAN NOT NULL DEFAULT FALSE,
    is_aigc BOOLEAN NOT NULL DEFAULT FALSE,
    consented_at TIMESTAMPTZ NOT NULL,
    scheduled_for TIMESTAMPTZ NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'queued' CHECK (
        status IN ('queued', 'initializing', 'uploading', 'processing', 'inbox_delivered',
                   'published', 'failed', 'dead_letter', 'cancelled', 'mock_complete')
    ),
    publish_id VARCHAR(128),
    post_id VARCHAR(128),
    attempts INTEGER NOT NULL DEFAULT 0,
    provider_log_id VARCHAR(128),
    error_code VARCHAR(120),
    error_message TEXT,
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_publication_org_status ON publication_jobs (organization_id, status);
CREATE INDEX ix_publication_due ON publication_jobs (status, scheduled_for);

CREATE TABLE publication_events (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    publication_job_id VARCHAR(36) NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    event_type VARCHAR(60) NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_publication_events_job_created
    ON publication_events (publication_job_id, created_at);

CREATE TABLE tiktok_webhook_receipts (
    id VARCHAR(36) PRIMARY KEY,
    delivery_hash VARCHAR(64) NOT NULL UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    open_id VARCHAR(128),
    payload_json TEXT NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
