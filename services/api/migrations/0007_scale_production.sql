CREATE TABLE operational_errors (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE,
    service VARCHAR(60) NOT NULL,
    code VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'error',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    message_sanitized TEXT NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    request_id VARCHAR(64),
    occurrences INTEGER NOT NULL DEFAULT 1,
    corrective_action TEXT,
    resolved_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,
    CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    CHECK (status IN ('open', 'resolved'))
);
CREATE INDEX ix_operational_error_status_seen ON operational_errors (status, last_seen_at);
CREATE INDEX ix_operational_error_org_status ON operational_errors (organization_id, status);
CREATE INDEX ix_operational_error_fingerprint ON operational_errors (fingerprint);

CREATE TABLE cost_budgets (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    monthly_limit_cents INTEGER NOT NULL,
    warning_percent INTEGER NOT NULL DEFAULT 80,
    hard_stop_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    currency VARCHAR(3) NOT NULL DEFAULT 'BRL',
    updated_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cost_budget_org UNIQUE (organization_id),
    CHECK (monthly_limit_cents >= 0),
    CHECK (warning_percent BETWEEN 1 AND 100)
);

CREATE TABLE cost_ledger_entries (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(60) NOT NULL,
    category VARCHAR(40) NOT NULL,
    amount_micros BIGINT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit VARCHAR(30) NOT NULL DEFAULT 'operation',
    source_ref VARCHAR(160) NOT NULL,
    is_mock BOOLEAN NOT NULL DEFAULT FALSE,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cost_org_source UNIQUE (organization_id, source_ref),
    CHECK (amount_micros >= 0)
);
CREATE INDEX ix_cost_org_occurred ON cost_ledger_entries (organization_id, occurred_at);

CREATE TABLE backup_runs (
    id VARCHAR(36) PRIMARY KEY,
    environment VARCHAR(30) NOT NULL,
    kind VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL,
    storage_key TEXT,
    checksum_sha256 VARCHAR(64),
    size_bytes BIGINT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    error_code VARCHAR(100),
    CHECK (status IN ('started', 'completed', 'failed', 'verified'))
);
CREATE INDEX ix_backup_environment_started ON backup_runs (environment, started_at);

CREATE TABLE audit_checkpoints (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    from_at TIMESTAMPTZ NOT NULL,
    to_at TIMESTAMPTZ NOT NULL,
    entry_count INTEGER NOT NULL,
    digest_sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (entry_count >= 0)
);
CREATE INDEX ix_audit_checkpoint_org_created ON audit_checkpoints (organization_id, created_at);
