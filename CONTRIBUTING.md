# Contributing

1. Open an issue describing the failure mode or connector behavior.
2. Create a focused branch.
3. Add tests for success, retry, partial failure, and post-operation discovery.
4. Run `make test` and `make lint`.
5. Open a pull request explaining the consistency guarantee and its limits.

Connectors must scope every operation by tenant and document, be idempotent, and verify actual state after mutation.
