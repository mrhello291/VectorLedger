# VectorLedger launch copy

## Hacker News

**Title:** Show HN: VectorLedger – prove deleted RAG data is gone from every store

**Text:**

I built VectorLedger, an open-source consistency controller for RAG data lifecycle changes.

Deleting a PDF from SharePoint or S3 does not guarantee that its chunks, embeddings, cached answers, and graph nodes disappeared. VectorLedger records desired state, propagates idempotent tombstones/ACL changes, scans the actual stores, retries partial failures, and emits a signed receipt only after the postcondition is verified.

The Docker demo deliberately leaves unregistered data in PostgreSQL, Qdrant, and Redis, then discovers and removes it by stable document metadata.

It is an early MVP and I would especially value feedback on the connector contract and what “proof of deletion” should mean across eventually consistent systems.

Repository: https://github.com/mrhello291/VectorLedger

## Reddit / r/LocalLLaMA

**Title:** Open-source RAG cleanup controller: verify deleted documents are gone from vectors, chunks, and caches

**Text:**

I kept seeing the same lifecycle gap in RAG stacks: source deletion succeeds, but derived chunks or cached answers survive elsewhere.

VectorLedger is a self-hosted reconciliation layer—not another ingestion framework. It currently supports PostgreSQL, Qdrant, and Redis, with idempotent retries, orphan discovery, permission propagation, and signed verification receipts.

The demo intentionally skips lineage registration for three records and still finds and removes them using tenant/document metadata. I am looking for feedback and connector contributors, particularly for Elasticsearch, Milvus, Azure AI Search, and retrieval-path verification.

https://github.com/mrhello291/VectorLedger

## LinkedIn

Deleting a source document is not the same as deleting its RAG footprint.

A single file may leave chunks in PostgreSQL, embeddings in a vector database, cached answers in Redis, and derived graph data. One missed event can keep deleted or revoked content retrievable.

I have open-sourced VectorLedger: a self-hosted consistency controller that propagates lifecycle changes, retries partial failures, independently scans downstream stores, and issues a signed receipt only after deletion is verified.

The first release includes PostgreSQL, Qdrant, Redis, an API/CLI, tests, and a Docker demo that deliberately discovers unregistered stale records.

Feedback and contributors are welcome: https://github.com/mrhello291/VectorLedger

#RAG #OpenSource #DataGovernance #VectorDatabase #Security

## Short community message

I released VectorLedger, an open-source reconciliation and deletion-verification layer for RAG stores. The demo creates unregistered records in PostgreSQL, Qdrant, and Redis, then proves their removal after a source tombstone. I would value feedback on the connector contract and help with additional vector/search backends: https://github.com/mrhello291/VectorLedger
