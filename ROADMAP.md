# Roadmap

VectorLedger is intentionally focused on reconciliation and verification rather than ingestion.

## v0.2 — trustworthy controller foundations

- Durable PostgreSQL job leases for multi-replica workers
- Complete Qdrant pagination and rate-limit handling
- OpenTelemetry traces, metrics, and structured audit logs
- Retrieval-path probes in addition to metadata scans
- KMS-backed asymmetric receipt signatures

## Connector roadmap

- Azure AI Search and Microsoft Graph/SharePoint
- Elasticsearch/OpenSearch
- Milvus
- Pinecone
- S3 and object-store lifecycle watchers
- Neo4j knowledge-graph cleanup

## Ecosystem roadmap

- LangChain and LlamaIndex helper packages
- Helm chart and Kubernetes deployment guidance
- Published conformance suite for third-party connectors
- Receipt JSON Schema and external signature verification CLI

Roadmap items are proposals, not delivery commitments. Please open or join the corresponding issue before implementing a major item.
