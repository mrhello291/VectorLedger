# Introducing VectorLedger: prove deleted RAG data is actually gone

Deleting a source document does not necessarily delete what a RAG system derived from it.

A single PDF can become rows in PostgreSQL, embeddings in a vector database, keyword-index entries, cached answers, graph nodes, and generated artifacts. When the source is deleted—or an employee loses access—each derived copy must change too. A timeout, missed event, or partially failed job can leave stale content retrievable long after the source system says it is gone.

VectorLedger is an open-source, self-hosted consistency controller for this problem. It does not parse documents or generate embeddings. It sits beside the ingestion pipeline and continuously reconciles the desired lifecycle state with what actually exists in downstream stores.

## The key distinction: verification

Most deletion jobs stop after a target API returns success. VectorLedger performs a fresh discovery scan and records the postcondition. A document is only marked verified deleted when every configured target is clean.

If Qdrant is unavailable, the receipt fails and the anti-entropy worker retries later. If an embedding was never registered in the lineage table but still carries `tenant_id` and `document_id`, metadata discovery can find it. If permissions change, stores that support ACL metadata are updated while unsafe caches are invalidated.

## What the first release includes

Version 0.1.0 includes a PostgreSQL control-plane ledger, connectors for PostgreSQL chunk tables, Qdrant, and Redis, periodic reconciliation, signed HMAC receipts, a REST API, a CLI, and a complete Docker Compose demonstration.

The demo deliberately creates one unregistered record in each target. VectorLedger receives only the source document identity, discovers all three records, removes them, scans again, and emits a signed receipt showing zero remaining records.

## Why open source?

The lineage table itself is not the hard or reusable part. Reliable connectors, idempotent mutation, partial-failure handling, orphan discovery, multi-tenant scoping, and independently testable postconditions are where teams repeatedly rebuild the same machinery.

An open connector contract also makes the guarantee inspectable. Operators should be able to see exactly how a store is searched and what “clean” means instead of trusting a proprietary success flag.

## What comes next

The next priorities are Azure AI Search, Elasticsearch/OpenSearch, complete pagination, durable multi-replica job leases, OpenTelemetry, retrieval-path probes, and KMS-backed asymmetric signatures.

VectorLedger is an MVP, not a compliance certificate. It cannot find opaque copies with no stable lineage metadata, content exported outside configured systems, backups, or memorized model weights. Those boundaries are documented because deletion proofs are only useful when their scope is explicit.

Try the five-minute demo, inspect the connector contract, and pick up a `good first issue` at [github.com/mrhello291/VectorLedger](https://github.com/mrhello291/VectorLedger).
