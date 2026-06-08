# Server Control Plane

Python/Django backend foundation for the future control plane.

Currently implemented:

- minimal Django project wiring;
- `ipam` app with organizations, sites, IPv4 subnets, DHCP pools, and static DHCP reservations;
- `access` app with organization memberships, site memberships, permission helpers, and append-only audit events;
- validator functions for MAC addresses, IPv4 addresses/CIDRs, subnet membership, and hostnames;
- initial migrations and Django model tests.

Planned responsibilities not implemented yet:

- authentication UI and API authentication flows;
- DNS records and devices;
- config versioning;
- deterministic `dnsmasq` rendering;
- signed config artifact generation;
- deployment and rollback records;
- REST APIs;
- public snapshot publication;
- automatic audit logging for all mutations.

## Access App

The `access` app provides foundational role labels and helper functions for future APIs and UI flows:

- organization roles: owner, admin, viewer, auditor;
- site roles: site admin, DHCP editor, viewer, public publisher, device installer;
- permission helpers for viewing sites, editing DHCP data, managing sites, publishing public views, installing devices, and viewing audit events;
- audit event records with model-level append-only guards.

There are no API endpoints yet. Future API chunks should call these permission helpers rather than duplicating role checks inline.

## Dependency Management

Backend dependency intent lives in `pyproject.toml`. Exact resolved versions live in the committed `uv.lock` lockfile. Use uv for reproducible installs and checks.

Do not add a root `requirements.txt`; this repository is a monorepo, and dependencies stay with the component that owns them.

```bash
uv sync --extra dev --locked
```

If uv is missing, install it with one of:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
python -m pip install uv
pipx install uv
```

## Run Tests

```bash
uv run pytest
```

## Run Migration Checks

```bash
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
```

This is domain and access foundation only. There are no APIs, UI flows, device communication paths, config rendering, deployments, public endpoints, or Pi apply logic in this PR.
