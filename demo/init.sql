CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    body TEXT NOT NULL,
    allowed_principals TEXT[] NOT NULL DEFAULT '{}'
);
