# Security policy

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public issue containing credentials, exploitable deletion behavior, or tenant-isolation weaknesses.

## Deployment guidance

- Set `VL_API_KEY` and place the API behind your identity-aware proxy. The built-in key is a minimal safeguard, not a complete authorization system.
- Generate `VL_RECEIPT_SECRET` with a cryptographically secure secret manager and rotate it under a documented policy.
- Give each connector the least privilege it needs. Keep the ledger database separate from target stores in production.
- Use TLS for PostgreSQL, Qdrant, and Redis connections.
- Preserve both `tenant_id` and `document_id` on every derived record.
- Restrict connector table and collection configuration to operators.
- Monitor failed receipts and anti-entropy errors.

## Threat-model boundary

VectorLedger detects target records addressable by configured metadata. It cannot reliably discover copies that have no stable identifiers, opaque generated text that cannot be traced to a source, offline backups, model weights, or data exported outside configured systems.

The included HMAC receipt is tamper-evident for parties that do not possess the signing secret. For stronger non-repudiation, implement a KMS-backed asymmetric signer and independent timestamping.
