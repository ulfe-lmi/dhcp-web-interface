# Testing

The backend now includes Django model and validator tests for the initial IPAM/DHCP domain foundation, access-control and audit-event tests, read-only API tests, membership-management API tests, DHCP/IPAM CRUD API tests, and config version / deterministic renderer tests. Future implementation must continue adding tests at each component boundary.

Current backend checks:

```bash
cd apps/server
uv sync --extra dev --locked
uv run pytest
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
```

## Expected Layers

- Backend unit tests for validation, rendering decisions, permissions, and audit event creation.
- Access tests for membership uniqueness, role behavior, permission helpers, and append-only audit behavior.
- API tests for health, current-user, read-only organization/site visibility, and read-only method restrictions.
- Membership API tests for role boundaries, owner lockout prevention, cross-parent protection, safe serializers, and audit event creation.
- DHCP/IPAM API tests for subnet, pool, and reservation CRUD, RBAC boundaries, model validation through API writes, cross-parent protection, soft-disable behavior, and audit event creation.
- Config version and renderer tests for deterministic `dnsmasq` output, file hashes, artifact hashes, config version numbering, private rendered-files API access, RBAC, and audit event creation.
- API tests for authenticated reads, mutations, RBAC, tenant isolation, pagination, and public endpoint behavior.
- Frontend tests for critical flows, table behavior, import preview, deployment review, and public view rendering.
- Go unit tests for gateway message parsing, device identity checks, routing, heartbeats, and result reports.
- Agent tests for artifact download, hash verification, signature verification, target matching, retry/backoff, and lease parsing.
- Apply-helper tests for path restrictions, symlink rejection, file mode enforcement, `dnsmasq --test` invocation, atomic apply, restart failure, and rollback.
- Schema validation tests for config artifacts, device protocol messages, and public snapshots.
- Integration tests with fake `dnsmasq` fixtures and temporary directories.
- Security regression tests for public snapshot isolation, authorization, enrollment token reuse, and artifact tampering.

## CI Gates

CI runs backend Django tests from the committed uv lockfile, migration drift checks, migration application, Go placeholder tests, and JSON parsing for the artifact schema. Later CI should add linting, type checks, frontend tests, secret scanning, license scanning, SBOM generation, and vulnerability scanning.
