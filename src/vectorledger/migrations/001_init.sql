CREATE TABLE IF NOT EXISTS vl_documents (
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    version BIGINT NOT NULL CHECK (version > 0),
    source_uri TEXT NOT NULL,
    content_hash TEXT,
    desired_state TEXT NOT NULL CHECK (desired_state IN ('active', 'deleted')),
    allowed_principals TEXT[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, document_id)
);

CREATE TABLE IF NOT EXISTS vl_artifacts (
    artifact_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    document_version BIGINT NOT NULL,
    target TEXT NOT NULL,
    locator JSONB NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('present', 'deleted', 'error')),
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES vl_documents (tenant_id, document_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS vl_artifacts_document_idx
    ON vl_artifacts (tenant_id, document_id, target);

CREATE TABLE IF NOT EXISTS vl_receipts (
    receipt_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    signature TEXT NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (tenant_id, document_id)
        REFERENCES vl_documents (tenant_id, document_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS vl_receipts_document_idx
    ON vl_receipts (tenant_id, document_id, checked_at DESC);
