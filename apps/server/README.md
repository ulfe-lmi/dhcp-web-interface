# Server Control Plane

Python/Django backend foundation for the future control plane.

Implemented in this chunk:

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

## Install Development Dependencies

```bash
python -m pip install -e ".[dev]"
```

If your system Python is externally managed, create and activate a virtual environment first:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## Run Migration Checks

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
```

This is domain and access foundation only. There are no APIs, UI flows, device communication paths, config rendering, deployments, public endpoints, or Pi apply logic in this PR.
