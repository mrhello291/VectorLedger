# Connector contract

A connector implements three asynchronous operations:

```python
async def delete(document, artifacts) -> int: ...
async def apply_permissions(document, artifacts) -> int: ...
async def discover(document) -> list[dict]: ...
```

Requirements:

- Scope every query by both `tenant_id` and `document_id`.
- Make mutation calls safe to repeat.
- Treat timeouts and ambiguous responses as failures.
- Discover independently of registered artifact locations.
- Return only after the remote operation has completed when the target supports a wait option.
- Treat an empty `allowed_principals` value as deny-all. A connector or retrieval
  system where an empty ACL means public access must not enable scheduled deletion.

## Included adapters

### PostgreSQL

Deletes or updates a configured chunk table. Identifiers are validated and SQL values are parameterized. The expected default columns are `tenant_id`, `document_id`, and `allowed_principals`.

### Qdrant

Uses payload filters containing `tenant_id` and `document_id`. Deletion and payload updates request `wait=true`. Discovery uses the scroll endpoint.

### Redis

Discovers keys using `vl:{encoded_tenant_id}:{encoded_document_id}:*`. Use
`RedisConnector.namespace(tenant_id, document_id)` when constructing cache keys so
separators and glob characters cannot change reconciliation scope. Permission changes
invalidate caches instead of attempting to rewrite cached authorization decisions.

## Adding a connector

Implement the protocol in `src/vectorledger/connectors/base.py`, register it in `api._connectors`, add failure and idempotency tests, and document the metadata convention. Never claim verification based solely on a successful mutation response; always implement `discover`.
