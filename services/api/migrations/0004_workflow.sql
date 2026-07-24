BEGIN;

ALTER TABLE video_projects DROP CONSTRAINT IF EXISTS video_projects_status_check;
ALTER TABLE video_projects ADD CONSTRAINT video_projects_status_check CHECK (
    status IN ('draft', 'assembling', 'queued', 'rendering', 'preview_mock', 'review',
               'changes_requested', 'rejected', 'approved', 'scheduled', 'published',
               'failed', 'archived')
);

CREATE TABLE approval_requests (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    video_project_id VARCHAR(36) NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
    requested_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    decided_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    status VARCHAR(30) NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'approved', 'rejected', 'changes_requested', 'cancelled')
    ),
    request_note TEXT,
    decision_note TEXT,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_approval_project_version UNIQUE (video_project_id, version)
);
CREATE INDEX ix_approval_org_status_created
    ON approval_requests (organization_id, status, created_at DESC);
CREATE INDEX ix_approval_project_version
    ON approval_requests (video_project_id, version DESC);

CREATE TABLE approval_events (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    approval_request_id VARCHAR(36) NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    actor_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    event_type VARCHAR(40) NOT NULL,
    note TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_approval_events_request_created
    ON approval_events (approval_request_id, created_at);

CREATE TABLE scheduled_slots (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    video_project_id VARCHAR(36) NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
    approval_request_id VARCHAR(36) NOT NULL REFERENCES approval_requests(id) ON DELETE RESTRICT,
    created_by VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    scheduled_for TIMESTAMPTZ NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'America/Sao_Paulo',
    status VARCHAR(20) NOT NULL DEFAULT 'reserved' CHECK (
        status IN ('reserved', 'ready', 'cancelled')
    ),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_schedule_org_time ON scheduled_slots (organization_id, scheduled_for);
CREATE INDEX ix_schedule_project_status ON scheduled_slots (video_project_id, status);

CREATE TABLE notifications (
    id VARCHAR(36) PRIMARY KEY,
    organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    recipient_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(40) NOT NULL,
    title VARCHAR(160) NOT NULL,
    message TEXT NOT NULL,
    entity_type VARCHAR(40),
    entity_id VARCHAR(36),
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_notifications_recipient_read
    ON notifications (recipient_id, read_at, created_at DESC);
CREATE INDEX ix_notifications_org ON notifications (organization_id);

COMMIT;
