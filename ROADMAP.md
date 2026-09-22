# Roadmap

VectorLedger is intentionally focused on reconciliation and verification rather than ingestion.

## Shipped in v0.2

- Immediate hard deletion and reversible scheduled quarantine
- Restoration with an explicit re-ingestion signal
- Complete Qdrant discovery pagination
- ACL trust-boundary and source-integration documentation

## v0.3 — trustworthy controller foundations

- [Durable PostgreSQL job leases for multi-replica workers](https://github.com/mrhello291/VectorLedger/issues/9)
- [Bounded, batched anti-entropy reconciliation](https://github.com/mrhello291/VectorLedger/issues/13)
- [Connector rate-limit handling and retry backoff](https://github.com/mrhello291/VectorLedger/issues/15)
- [Versioned schema migrations with advisory locking](https://github.com/mrhello291/VectorLedger/issues/22)
- [OpenTelemetry traces, metrics, and structured audit logs](https://github.com/mrhello291/VectorLedger/issues/8)
- [Retrieval-path probes](https://github.com/mrhello291/VectorLedger/issues/4) and [reference ACL enforcement middleware](https://github.com/mrhello291/VectorLedger/issues/21)
- [KMS-backed asymmetric receipt signatures](https://github.com/mrhello291/VectorLedger/issues/2)
- [Tenant-aware authentication and authorization](https://github.com/mrhello291/VectorLedger/issues/14)
- [Principal mapping and group-resolution contract](https://github.com/mrhello291/VectorLedger/issues/20)
- [Strict equal-version event idempotency](https://github.com/mrhello291/VectorLedger/issues/17)
- [Pending-reingestion availability state](https://github.com/mrhello291/VectorLedger/issues/19)

## Connector roadmap

- [Azure AI Search](https://github.com/mrhello291/VectorLedger/issues/3) and [Microsoft Graph/SharePoint](https://github.com/mrhello291/VectorLedger/issues/16)
- [Elasticsearch/OpenSearch](https://github.com/mrhello291/VectorLedger/issues/7)
- Milvus
- Pinecone
- [S3 and object-store lifecycle watchers](https://github.com/mrhello291/VectorLedger/issues/6)
- Neo4j knowledge-graph cleanup

## Ecosystem roadmap

- LangChain and LlamaIndex helper packages
- [Helm chart and Kubernetes deployment guidance](https://github.com/mrhello291/VectorLedger/issues/10)
- [Published conformance suite for third-party connectors](https://github.com/mrhello291/VectorLedger/issues/18)
- [Receipt JSON Schema and external signature verification CLI](https://github.com/mrhello291/VectorLedger/issues/5)

Roadmap items are proposals, not delivery commitments. Please open or join the corresponding issue before implementing a major item.
