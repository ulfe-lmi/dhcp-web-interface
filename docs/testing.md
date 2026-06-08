# Testing

This scaffold includes placeholder tests only. Future implementation must add tests at each component boundary.

## Expected Layers

- Backend unit tests for validation, rendering decisions, permissions, and audit event creation.
- API tests for authenticated reads, mutations, RBAC, tenant isolation, pagination, and public endpoint behavior.
- Frontend tests for critical flows, table behavior, import preview, deployment review, and public view rendering.
- Go unit tests for gateway message parsing, device identity checks, routing, heartbeats, and result reports.
- Agent tests for artifact download, hash verification, signature verification, target matching, retry/backoff, and lease parsing.
- Apply-helper tests for path restrictions, symlink rejection, file mode enforcement, `dnsmasq --test` invocation, atomic apply, restart failure, and rollback.
- Schema validation tests for config artifacts, device protocol messages, and public snapshots.
- Integration tests with fake `dnsmasq` fixtures and temporary directories.
- Security regression tests for public snapshot isolation, authorization, enrollment token reuse, and artifact tampering.

## CI Gates

The initial CI runs Python placeholder tests, Go tests, and JSON parsing for the artifact schema. Later CI should add linting, type checks, frontend tests, secret scanning, license scanning, SBOM generation, and vulnerability scanning.
