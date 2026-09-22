# Contributing

Thanks for helping make RAG data lifecycle operations verifiable.

## Start here

1. Choose a [`good first issue`](https://github.com/mrhello291/VectorLedger/labels/good%20first%20issue) or open an issue describing the failure mode.
2. Comment on the issue before starting larger changes so effort is not duplicated.
3. Create a focused branch and keep unrelated formatting out of the change.
4. Add tests for success, retry, partial failure, tenant isolation, and post-operation discovery.
5. Run `make test` and `make lint`.
6. Open a pull request explaining the consistency guarantee and its limits.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make test
make lint
```

For the full integration demo:

```bash
docker compose up --build -d
docker compose --profile demo run --rm demo
docker compose down -v
```

## Connector acceptance criteria

Connectors must scope every operation by tenant and document, be idempotent, and verify actual state after mutation.

- Never treat an accepted delete request as proof of deletion.
- Cover records absent from the lineage registry but discoverable by metadata.
- Document pagination, rate limits, consistency delays, and permission semantics.
- Treat an empty ACL as deny-all. Never interpret a missing or empty ACL as public access.
- Do not log document content, credentials, or unrestricted source URIs.

See the [permission integration guide](docs/permissions.md) before changing ACL
propagation. Storage metadata is only one half of access control: the RAG retriever must
also filter every query using the same immutable principal IDs.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
