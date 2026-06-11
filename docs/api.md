# API Overview

The backend API is served by Django REST Framework under `/api/v1/`.

## Current Endpoints

- `GET /api/v1/health/`
- `GET /api/v1/me/`
- `GET /api/v1/organizations/`
- `GET /api/v1/organizations/{id}/`
- `GET /api/v1/sites/`
- `GET /api/v1/sites/{id}/`
- `GET /api/v1/organizations/{organization_id}/memberships/`
- `POST /api/v1/organizations/{organization_id}/memberships/`
- `PATCH /api/v1/organizations/{organization_id}/memberships/{membership_id}/`
- `DELETE /api/v1/organizations/{organization_id}/memberships/{membership_id}/`
- `GET /api/v1/sites/{site_id}/memberships/`
- `POST /api/v1/sites/{site_id}/memberships/`
- `PATCH /api/v1/sites/{site_id}/memberships/{membership_id}/`
- `DELETE /api/v1/sites/{site_id}/memberships/{membership_id}/`
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
- `GET /api/v1/sites/{site_id}/config-versions/`
- `POST /api/v1/sites/{site_id}/config-versions/`
- `GET /api/v1/sites/{site_id}/config-versions/{config_version_id}/`
- `GET /api/v1/sites/{site_id}/config-versions/{config_version_id}/rendered-files/`

## DHCP/IPAM Behavior

Authenticated users who can view a site can read subnets, pools, and reservations for that site. Organization owners/admins, site admins, and DHCP editors can mutate DHCP/IPAM data for that site.

`DELETE` disables DHCP pools and reservations by setting `enabled=false`. IPv4 subnet deletion is allowed only when the subnet has no pools or reservations.

Successful DHCP/IPAM mutations write `AuditEvent` records. API writes do not render `dnsmasq` config, create config versions, trigger deployments, notify devices, or apply changes on edge appliances.

There is no public no-login DHCP/IPAM table endpoint yet. Future public viewing must use a separate sanitized published snapshot.

## Config Version Behavior

Authenticated users who can view a site can list config versions, inspect config version metadata, and retrieve rendered config previews for that site. Organization owners/admins, site admins, and DHCP editors can create config versions.

Creating a config version renders deterministic private `dnsmasq` files from structured DHCP/IPAM data, stores those files on the `ConfigVersion`, computes file hashes and an artifact hash, and writes a `config_version.created` audit event.

Clients cannot choose `version_number`, `status`, `rendered_files`, hashes, signature, site, creator, or approver. Config version creation does not deploy, notify devices, write files, call `dnsmasq`, or sign artifacts.
