# Architecture

This repository is the scaffold for a two-tier DHCP/IPAM appliance product. The server-side control plane is the source of truth. Raspberry Pi edge appliances are replaceable reconcilers that apply signed desired-state artifacts to local `dnsmasq`.

## Control Plane

The future control plane lives under `apps/server`. It will own organizations, users, sites, subnets, address pools, reservations, DNS records, devices, config versions, deployments, lease reports, public publication settings, and audit events.

PostgreSQL is the authoritative data store. The Pi must never be treated as the source of truth.

The initial backend foundation now includes Django models and validation for organizations, sites, IPv4 subnets, DHCP pools, and static DHCP reservations under `managed_dhcp_server.ipam`. It also includes authenticated API endpoints for current user, organizations, sites, membership management, DHCP/IPAM CRUD, config version creation, and private rendered config preview under `/api/v1/`. Deployments, public snapshots, and device communication do not exist yet.

## Web UI

The future web UI lives under `apps/web`. It will provide authenticated management workflows for DHCP/IPAM editing, imports, deployment review, device status, audit history, and organization settings.

Authorization must be enforced by the backend, not only by hidden frontend controls.

## Public Read-Only Published Snapshot

The public no-login view must be a separate publication path. It reads only sanitized published snapshots, not live private reservation tables and not authenticated admin APIs.

Public publication is disabled by default. Dangerous fields such as MAC addresses, owner/contact data, lease state, internal notes, and comments must default to hidden.

## Device Gateway

The future device gateway lives under `services/device-gateway`. It is a Go service responsible for outbound edge connections, device identity enforcement, heartbeats, config availability notifications, deployment result reports, and lease report ingestion or forwarding.

The gateway does not own business authorization or IPAM validation.

## Pi Agent

The future Pi agent lives under `edge/agent`. It must run unprivileged, connect outbound to the gateway, authenticate as an enrolled device, download signed config artifacts, validate hashes and signatures, stage artifacts, and ask the local helper to apply.

The Pi exposes no inbound management API.

## Apply Helper

The future apply helper lives under `edge/apply-helper`. It is the only privileged local component. It must have no network listener and must not accept arbitrary remote commands, arbitrary service names, or arbitrary file paths.

Expected managed path:

```text
/etc/dnsmasq.d/managed/
```

Expected validation before apply:

```text
dnsmasq --test
```

## Config Artifact Lifecycle

1. Backend validates structured DHCP/IPAM state.
2. Backend creates an immutable config version.
3. Backend renders deterministic `dnsmasq` files into private stored preview data.
4. Backend computes file hashes and an artifact hash.
5. Later work will sign artifacts, notify devices, download/stage/apply on agents, and record deployment results.

Current implementation stops at config version, rendered files, manifest, and hash. It does not sign artifacts, notify devices, write `dnsmasq` files, or deploy anything.

## Deployment Lifecycle

Deployments are expected to move through queued, notified, downloaded, staged, validating, applying, health-check, succeeded, failed, or rolled-back states. Deployment records must be immutable and auditable.

Rollback support is required in later implementation. This scaffold does not implement deployment logic.
