# Testing

The backend now includes Django model and validator tests for the initial IPAM/DHCP domain foundation. Future implementation must continue adding tests at each component boundary.

Current backend checks:

```bash
cd apps/server
python -m pip install -e ".[dev]"
pytest
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
```

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

CI runs backend Django tests, migration drift checks, migration application, Go placeholder tests, and JSON parsing for the artifact schema. Later CI should add linting, type checks, frontend tests, secret scanning, license scanning, SBOM generation, and vulnerability scanning.
