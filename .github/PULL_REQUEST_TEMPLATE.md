## What changed

<!-- Explain the user-visible behavior and failure mode addressed. -->

## Consistency guarantee

<!-- State the desired-state/actual-state postcondition and any remaining limits. -->

## Verification

- [ ] Tests cover success and idempotent retry.
- [ ] Connector changes cover partial failure and post-operation discovery.
- [ ] Tenant and document scope are enforced together.
- [ ] Empty ACLs are deny-all and retrieval-path assumptions are documented.
- [ ] Schema or API changes include upgrade and compatibility notes.
- [ ] Documentation is updated.
- [ ] `make test` and `make lint` pass.
