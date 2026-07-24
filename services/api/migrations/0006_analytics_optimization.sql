CREATE TABLE publication_metric_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    publication_job_id VARCHAR(36) NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    provider_video_id VARCHAR(128) NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 0,
    like_count INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    share_count INTEGER NOT NULL DEFAULT 0,
    source VARCHAR(40) NOT NULL DEFAULT 'display_api',
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_metric_org_collected ON publication_metric_snapshots (organization_id, collected_at);
CREATE INDEX ix_metric_job_collected ON publication_metric_snapshots (publication_job_id, collected_at);

CREATE TABLE account_metric_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    connection_id VARCHAR(36) NOT NULL REFERENCES tiktok_connections(id) ON DELETE CASCADE,
    follower_count INTEGER NOT NULL DEFAULT 0,
    following_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    video_count INTEGER NOT NULL DEFAULT 0,
    source VARCHAR(40) NOT NULL DEFAULT 'display_api',
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_account_metric_connection_collected ON account_metric_snapshots (connection_id, collected_at);

CREATE TABLE retention_observations (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    publication_job_id VARCHAR(36) NOT NULL REFERENCES publication_jobs(id) ON DELETE CASCADE,
    imported_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    source VARCHAR(50) NOT NULL,
    average_watch_time_seconds DOUBLE PRECISION,
    completion_rate DOUBLE PRECISION,
    watched_full_rate DOUBLE PRECISION,
    saved_count INTEGER,
    curve_json TEXT NOT NULL DEFAULT '[]',
    collected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (completion_rate IS NULL OR completion_rate BETWEEN 0 AND 1),
    CHECK (watched_full_rate IS NULL OR watched_full_rate BETWEEN 0 AND 1)
);
CREATE INDEX ix_retention_job_collected ON retention_observations (publication_job_id, collected_at);

CREATE TABLE analytics_recommendations (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL,
    title VARCHAR(180) NOT NULL,
    rationale TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    evidence_hash VARCHAR(64) NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    decided_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_recommendation_evidence UNIQUE (organization_id, evidence_hash),
    CHECK (confidence BETWEEN 0 AND 100),
    CHECK (status IN ('open', 'accepted', 'dismissed'))
);
CREATE INDEX ix_recommendation_org_status ON analytics_recommendations (organization_id, status);

CREATE TABLE content_experiments (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name VARCHAR(160) NOT NULL,
    hypothesis TEXT NOT NULL,
    variable VARCHAR(40) NOT NULL,
    primary_metric VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('draft', 'running', 'completed', 'cancelled'))
);
CREATE INDEX ix_experiment_org_status ON content_experiments (organization_id, status);

CREATE TABLE experiment_variants (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    experiment_id VARCHAR(36) NOT NULL REFERENCES content_experiments(id) ON DELETE CASCADE,
    video_project_id VARCHAR(36) NOT NULL REFERENCES video_projects(id) ON DELETE RESTRICT,
    label VARCHAR(20) NOT NULL,
    variable_value TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_experiment_variant_label UNIQUE (experiment_id, label),
    CONSTRAINT uq_experiment_variant_project UNIQUE (experiment_id, video_project_id)
);
