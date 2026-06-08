# Deployment

Deployment is not implemented in this scaffold. This document records the intended deployment shape.

## Server Side

The control plane should run behind a reverse proxy such as Caddy or nginx. PostgreSQL is the source-of-truth database. Valkey is the intended cache/broker for Celery and related background work.

Expected future services:

- Django/DRF API and admin control plane.
- Celery workers for imports, rendering, publication, notifications, and maintenance tasks.
- PostgreSQL.
- Valkey.
- Go device gateway.
- Reverse proxy terminating TLS.

## Device Gateway

The gateway should expose a TLS endpoint for outbound edge appliance connections. It should authenticate devices, enforce revocation, and route notifications and reports. mTLS or device certificates are planned.

## Raspberry Pi Edge

The Pi runs:

- unprivileged `dhcp-agent` as a `systemd` service;
- privileged local-only `dhcp-apply-helper`;
- `dnsmasq`;
- managed config files under `/etc/dnsmasq.d/managed/`.

The Pi must not expose an inbound management API. The helper must have no network listener.

Packaging, installation, upgrades, systemd units, firewall guidance, and rollback behavior will be added in later PRs.
