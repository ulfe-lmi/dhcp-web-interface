# Server Control Plane

Python/Django backend foundation for the future control plane.

Implemented in this chunk:

- minimal Django project wiring;
- `ipam` app with organizations, sites, IPv4 subnets, DHCP pools, and static DHCP reservations;
- validator functions for MAC addresses, IPv4 addresses/CIDRs, subnet membership, and hostnames;
- initial migration and Django model tests.

Planned responsibilities not implemented yet:

- authentication and authorization;
- DNS records and devices;
- config versioning;
- deterministic `dnsmasq` rendering;
- signed config artifact generation;
- deployment and rollback records;
- REST APIs;
- public snapshot publication;
- audit logging.

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

This is domain model only. There are no APIs, UI flows, device communication paths, config rendering, deployments, public endpoints, or Pi apply logic in this PR.
