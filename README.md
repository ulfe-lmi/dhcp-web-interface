# Managed DHCP/IPAM Edge Appliance

Managed DHCP/IPAM Edge Appliance is a cloud-managed DDI-lite product concept for administering DHCP/IPAM/DNS state from a server-side control plane while Raspberry Pi edge appliances reconcile signed desired-state configuration to local `dnsmasq`. The server is the source of truth; the Pi is replaceable infrastructure that connects outbound, validates artifacts, applies only approved configuration, and reports status.

Current status: **Backend domain and access foundations exist for organizations, sites, IPv4 subnets, DHCP pools, static reservations, memberships, permission helpers, and audit events; no production DHCP rendering, APIs, UI, deployment, public view, or edge apply logic implemented yet.**

## Architecture Overview

The product is split into clear trust and responsibility boundaries:

- `apps/server`: future Python/Django control plane, API, validation engine, config versioning, artifact signing, deployment records, audit log, and public snapshot publication.
- `apps/web`: future Next.js/React management UI and separate public read-only table view.
- `services/device-gateway`: future Go gateway for outbound edge appliance connections, heartbeats, deployment notifications, and reports.
- `edge/agent`: future unprivileged Raspberry Pi agent that connects outbound to the gateway, downloads signed artifacts, validates them, stages them, and asks the local helper to apply.
- `edge/apply-helper`: future tiny privileged local helper with no network surface. It will write only managed `dnsmasq` files, validate with `dnsmasq --test`, reload/restart `dnsmasq`, and roll back on failure.
- `schemas`: shared protocol and artifact schemas.

The Pi must not expose an inbound management API, and the network-facing agent must not run as root.

## Repository Layout

```text
.
├── AGENTS.md
├── README.md
├── docs/
├── apps/
│   ├── server/
│   └── web/
├── services/
│   └── device-gateway/
├── edge/
│   ├── agent/
│   └── apply-helper/
├── schemas/
├── scripts/
└── .github/workflows/
```

## Intended Stack

- Server/control plane: Python, Django, Django REST Framework, PostgreSQL, Celery, Valkey, Caddy or equivalent reverse proxy.
- Web frontend: Next.js or React, TypeScript, Tailwind CSS, shadcn/ui or equivalent components, AG Grid Community for spreadsheet-like DHCP/IPAM tables.
- Device communication: Go device gateway, outbound Pi connections over HTTPS/WebSocket or gRPC over TLS, planned mTLS/device certificates.
- Edge appliance: Go `dhcp-agent`, tiny privileged `dhcp-apply-helper`, `dnsmasq`, `systemd`, managed files under `/etc/dnsmasq.d/managed/`.
- Security and quality: OWASP ASVS-oriented web controls, RBAC, audit log, signed config artifacts, immutable deployment history, CI checks, SBOM and vulnerability scanning in later release work.

## Development Prerequisites

For this scaffold:

- Python 3.11+
- Go 1.22+
- Bash
- Optional Node.js 20+ for future frontend work

Future product milestones will add Django, DRF, PostgreSQL, Valkey, frontend tooling, and containerized local development.

## Run Checks

```bash
scripts/check.sh
```

Format supported scaffold code:

```bash
scripts/format.sh
```

## Security Model Summary

The server publishes desired state, never arbitrary remote shell commands. Edge devices connect outbound only. The unprivileged `dhcp-agent` handles network communication, artifact validation, and staging. The privileged `dhcp-apply-helper` must remain local-only, with no network listener, no arbitrary command execution, and no arbitrary file paths.

Config artifacts must be signed, immutable per version, validated before apply, and rollback-capable. Every meaningful user, device, deployment, and public publication action must be auditable in later implementation.

## Public Read-Only View Warning

The public no-login view must be opt-in and disabled by default. It must read from a sanitized published snapshot, not from authenticated admin APIs with edit controls hidden. Sensitive columns such as MAC addresses, owner/contact data, lease state, and internal notes must default to hidden.

## Roadmap

1. Bootstrap scaffold, docs, placeholder tests, and CI.
2. Backend domain model and validation foundation.
3. Config renderer and signed artifact schema.
4. Public read-only sanitized snapshot.
5. Device gateway protocol skeleton.
6. Raspberry Pi agent skeleton.
7. Apply helper and `dnsmasq --test` validation.
8. Deployment lifecycle and rollback tracking.
9. UI editor for sites, subnets, reservations, devices, and deployments.
10. Import/export workflow.
11. Observability and security hardening.
12. Packaging and release process.

This repository is not yet functional production software.
