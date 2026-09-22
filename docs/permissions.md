# Permission integration

VectorLedger is an ACL propagation and verification controller. It is not the identity
provider and it is not automatically placed in the application's retrieval path.

## Responsibility boundary

The source system—such as SharePoint, Microsoft Graph, S3 plus an identity directory,
or an internal document service—remains authoritative for access. A source adapter or
the existing ingestion pipeline translates that source ACL into stable principal IDs
and sends it to VectorLedger:

```json
{
  "document_id": "salary-policy",
  "version": 7,
  "source_uri": "sharepoint://policies/salary-policy.pdf",
  "allowed_principals": ["entra-user:8f3...", "entra-group:hr"]
}
```

VectorLedger stores the desired ACL, asks each connector to update matching derived
records, discovers those records again, and signs a receipt only when their ACL metadata
matches. Redis-style answer caches are invalidated rather than rewritten.

The RAG application's retriever must independently enforce the same stable principal
IDs when querying PostgreSQL, Qdrant, or another backend. VectorLedger does not make an
unfiltered query safe.

## Lifecycle operations

- `PUT /v1/documents/{id}/permissions` propagates a normal ACL change. Chunks and
  embeddings remain in place.
- Immediate deletion removes configured derived records now.
- Scheduled deletion writes an empty ACL (deny all), invalidates caches, and records a
  purge deadline. It is safe only when every retrieval path treats an empty ACL as
  inaccessible.
- `POST /v1/documents/{id}/restore` requires the current authoritative ACL. VectorLedger
  deliberately does not guess or reuse an old ACL that may now be stale.
- Restoring before the deadline reuses quarantined chunks. Restoring after hard deletion
  returns `reingestion_required: true` so the source pipeline can rebuild them.

## Principal mapping guidance

Use immutable IDs rather than display names or email addresses. Prefix IDs with their
authority and type, for example `entra-user:<object-id>` or
`okta-group:<group-id>`. The source adapter owns group expansion and identity changes;
the current MVP treats principal strings as opaque values.

For a complete guarantee, operators should combine storage-level ACL verification with
the planned retrieval-path probes described in issue #4.
