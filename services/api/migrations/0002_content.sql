BEGIN;

CREATE TABLE content_niches (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    description TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    is_custom BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_niche_org_slug UNIQUE (organization_id, slug)
);
CREATE INDEX ix_niches_org_enabled ON content_niches (organization_id, enabled);

CREATE TABLE blocked_topics (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    term VARCHAR(160) NOT NULL,
    normalized_term VARCHAR(160) NOT NULL,
    kind VARCHAR(20) NOT NULL CHECK (kind IN ('keyword', 'topic', 'category')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_blocked_org_term_kind UNIQUE (organization_id, normalized_term, kind)
);
CREATE INDEX ix_blocked_org_active ON blocked_topics (organization_id, active);

CREATE TABLE ai_providers (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    capability VARCHAR(40) NOT NULL,
    provider_key VARCHAR(60) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    is_mock BOOLEAN NOT NULL DEFAULT TRUE,
    config_json TEXT NOT NULL DEFAULT '{}',
    secret_ref VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_provider_capability UNIQUE (organization_id, capability, provider_key)
);

CREATE TABLE content_ideas (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    niche_id VARCHAR(36) NOT NULL REFERENCES content_niches(id) ON DELETE RESTRICT,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    mode VARCHAR(30) NOT NULL DEFAULT 'manual',
    topic VARCHAR(200) NOT NULL,
    creative_angle TEXT NOT NULL,
    content_promise TEXT NOT NULL,
    hook TEXT NOT NULL,
    narrative_structure TEXT NOT NULL,
    key_information TEXT NOT NULL,
    call_to_action TEXT NOT NULL,
    visual_suggestion TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds BETWEEN 15 AND 180),
    target_audience VARCHAR(180) NOT NULL,
    objective VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'selected', 'rejected', 'archived')),
    risk_level VARCHAR(20) NOT NULL DEFAULT 'low'
        CHECK (risk_level IN ('low', 'medium', 'high', 'blocked')),
    provider_key VARCHAR(60),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_ideas_org_status_created ON content_ideas (organization_id, status, created_at DESC);
CREATE INDEX ix_ideas_org_niche ON content_ideas (organization_id, niche_id);

CREATE TABLE scripts (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    idea_id VARCHAR(36) NOT NULL REFERENCES content_ideas(id) ON DELETE CASCADE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL CHECK (version > 0),
    style VARCHAR(40) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    moderation_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    fact_check_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    provider_key VARCHAR(60),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_script_idea_version UNIQUE (idea_id, version)
);
CREATE INDEX ix_scripts_org_status ON scripts (organization_id, status);

CREATE TABLE sources (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title VARCHAR(300) NOT NULL,
    publisher VARCHAR(180) NOT NULL,
    published_at TIMESTAMPTZ,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    trust_score INTEGER NOT NULL CHECK (trust_score BETWEEN 0 AND 100),
    license_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_source_org_url UNIQUE (organization_id, url)
);

CREATE TABLE fact_checks (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    script_id VARCHAR(36) NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    source_id VARCHAR(36) REFERENCES sources(id) ON DELETE SET NULL,
    claim TEXT NOT NULL,
    verdict VARCHAR(30) NOT NULL,
    confidence INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    evidence TEXT NOT NULL,
    provider_key VARCHAR(60) NOT NULL,
    reviewed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_fact_checks_script ON fact_checks (script_id, created_at DESC);

CREATE TABLE script_sources (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    script_id VARCHAR(36) NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    source_id VARCHAR(36) NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_script_source UNIQUE (script_id, source_id)
);
CREATE INDEX ix_script_sources_script ON script_sources (script_id);

CREATE TABLE moderation_checks (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subject_type VARCHAR(40) NOT NULL,
    subject_id VARCHAR(36) NOT NULL,
    stage VARCHAR(30) NOT NULL,
    result VARCHAR(20) NOT NULL CHECK (result IN ('allow', 'review', 'block')),
    matched_rules_json TEXT NOT NULL DEFAULT '[]',
    policy_version VARCHAR(20) NOT NULL,
    provider_key VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_moderation_subject ON moderation_checks (subject_type, subject_id, created_at DESC);

CREATE TABLE content_events (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    subject_type VARCHAR(40) NOT NULL,
    subject_id VARCHAR(36) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_content_events_subject ON content_events (subject_type, subject_id, created_at);

COMMIT;
