CREATE TABLE trend_sources (
  id VARCHAR(36) PRIMARY KEY,
  organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name VARCHAR(120) NOT NULL,
  connector_type VARCHAR(30) NOT NULL,
  endpoint_url TEXT,
  terms_url TEXT NOT NULL,
  authorized_at TIMESTAMPTZ NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_trend_source_org_name UNIQUE (organization_id, name)
);
CREATE INDEX ix_trend_sources_organization_id ON trend_sources (organization_id);

CREATE TABLE trends (
  id VARCHAR(36) PRIMARY KEY,
  organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  source_id VARCHAR(36) NOT NULL REFERENCES trend_sources(id) ON DELETE RESTRICT,
  topic VARCHAR(200) NOT NULL,
  category VARCHAR(100) NOT NULL,
  relevance_reason TEXT NOT NULL,
  growth_percent DOUBLE PRECISION NOT NULL,
  interest_volume INTEGER NOT NULL,
  competition VARCHAR(20) NOT NULL,
  retention_score INTEGER NOT NULL,
  share_score INTEGER NOT NULL,
  sensitivity_risk VARCHAR(20) NOT NULL,
  saturation_risk VARCHAR(20) NOT NULL,
  suggested_approach TEXT NOT NULL,
  likely_audience VARCHAR(180) NOT NULL,
  valid_until TIMESTAMPTZ NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_trends_org_captured ON trends (organization_id, captured_at);
CREATE INDEX ix_trends_source_topic ON trends (source_id, topic);

CREATE TABLE content_series (
  id VARCHAR(36) PRIMARY KEY,
  organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  niche_id VARCHAR(36) REFERENCES content_niches(id) ON DELETE SET NULL,
  created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  name VARCHAR(140) NOT NULL,
  description TEXT NOT NULL,
  cadence VARCHAR(40) NOT NULL,
  target_episode_count INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_content_series_org_name UNIQUE (organization_id, name)
);
CREATE INDEX ix_content_series_org_status ON content_series (organization_id, status);
