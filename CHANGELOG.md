# Changelog

All notable changes are documented here.

## 0.2.0 — 2026-09-22

- Add immediate and scheduled deletion modes.
- Quarantine scheduled deletions with empty ACLs before their purge deadline.
- Add document restoration with an explicit re-ingestion signal after hard deletion.
- Paginate Qdrant discovery beyond the first 256 points.
- Encode Redis cache namespace components to preserve tenant/document scope.
- Prevent artifact IDs from being reassigned across lineage.
- Expand the demo and permission-integration documentation.

## 0.1.0 — 2026-09-20

- Initial self-hosted reconciliation controller
- PostgreSQL control-plane ledger and migrations
- PostgreSQL, Qdrant, and Redis target connectors
- Idempotent deletion and permission propagation
- Metadata discovery for unregistered derived records
- HMAC-signed verification receipts
- Periodic anti-entropy reconciliation
- REST API, CLI, Docker Compose demo, tests, and CI
