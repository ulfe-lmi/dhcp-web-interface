# Server Control Plane

Python/Django backend foundation for the future control plane.

Currently implemented:

- minimal Django project wiring;
- `ipam` app with organizations, sites, IPv4 subnets, DHCP pools, and static DHCP reservations;
- `access` app with organization memberships, site memberships, permission helpers, and append-only audit events;
- `api` app with DRF routing under `/api/v1/` for health, current user, read-only organization/site endpoints, membership-management endpoints, and DHCP/IPAM CRUD endpoints;
- validator functions for MAC addresses, IPv4 addresses/CIDRs, subnet membership, and hostnames;
- initial migrations and Django model tests.

Planned responsibilities not implemented yet:

- authentication UI, SSO/OIDC, MFA, and production authentication flows;
- DNS records and devices;
- config versioning;
- deterministic `dnsmasq` rendering;
- signed config artifact generation;
- deployment and rollback records;
- public snapshot publication;
- automatic audit logging for all mutations.

## Access App

The `access` app provides foundational role labels and helper functions for future APIs and UI flows:

- organization roles: owner, admin, viewer, auditor;
- site roles: site admin, DHCP editor, viewer, public publisher, device installer;
- permission helpers for viewing sites, editing DHCP data, managing sites, publishing public views, installing devices, and viewing audit events;
- audit event records with model-level append-only guards.

Future API chunks should call these permission helpers rather than duplicating role checks inline.

## API

The first DRF API foundation exists under `/api/v1/`.

Current endpoints:

- `GET /api/v1/health/`
- `GET /api/v1/me/`
- `GET /api/v1/organizations/`
- `GET /api/v1/organizations/{id}/`
- `GET /api/v1/organizations/{id}/memberships/`
- `POST /api/v1/organizations/{id}/memberships/`
- `PATCH /api/v1/organizations/{id}/memberships/{membership_id}/`
- `DELETE /api/v1/organizations/{id}/memberships/{membership_id}/`
- `GET /api/v1/sites/`
- `GET /api/v1/sites/{id}/`
- `GET /api/v1/sites/{id}/memberships/`
- `POST /api/v1/sites/{id}/memberships/`
- `PATCH /api/v1/sites/{id}/memberships/{membership_id}/`
- `DELETE /api/v1/sites/{id}/memberships/{membership_id}/`
- `GET /api/v1/sites/{site_id}/subnets/`
- `POST /api/v1/sites/{site_id}/subnets/`
- `GET /api/v1/sites/{site_id}/subnets/{subnet_id}/`
- `PATCH /api/v1/sites/{site_id}/subnets/{subnet_id}/`
- `DELETE /api/v1/sites/{site_id}/subnets/{subnet_id}/`
- `GET /api/v1/subnets/{subnet_id}/pools/`
- `POST /api/v1/subnets/{subnet_id}/pools/`
- `GET /api/v1/subnets/{subnet_id}/pools/{pool_id}/`
- `PATCH /api/v1/subnets/{subnet_id}/pools/{pool_id}/`
- `DELETE /api/v1/subnets/{subnet_id}/pools/{pool_id}/`
- `GET /api/v1/subnets/{subnet_id}/reservations/`
- `POST /api/v1/subnets/{subnet_id}/reservations/`
- `GET /api/v1/subnets/{subnet_id}/reservations/{reservation_id}/`
- `PATCH /api/v1/subnets/{subnet_id}/reservations/{reservation_id}/`
- `DELETE /api/v1/subnets/{subnet_id}/reservations/{reservation_id}/`

Organization membership mutations are limited to superusers and organization owners. Organization admins can list memberships only in the current policy. Site membership mutations are limited to superusers, organization owners, organization admins, and site admins; site admins cannot create, update, or delete `site_admin` memberships. Successful membership mutations write `AuditEvent` records.

## DHCP/IPAM API

The DHCP/IPAM API manages IPv4 subnets, DHCP pools, and DHCP reservations for authenticated users with site visibility or DHCP edit permission.

- Users who can view a site can read subnets, pools, and reservations for that site.
- Organization owners/admins, site admins, and DHCP editors can create and update DHCP/IPAM data.
- `DELETE` on DHCP pools and reservations disables the object by setting `enabled=false`; disabled records remain visible in authenticated lists.
- `DELETE` on IPv4 subnets is allowed only when the subnet has no pools or reservations.
- Successful DHCP/IPAM mutations write `AuditEvent` records.

These endpoints are the backend API layer a later graphical interface will use. API writes do not render `dnsmasq` config, create config versions, trigger deployments, notify devices, or apply anything on a Raspberry Pi.

There is no public no-login DHCP/IPAM table endpoint or production SSO/OIDC/MFA flow yet.

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

This is domain, access, read API, membership-management API, and DHCP/IPAM CRUD API foundation only. There are no UI flows, device communication paths, config rendering, deployments, public endpoints, or Pi apply logic in this PR.
