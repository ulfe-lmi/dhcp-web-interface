# Security Model

This document records the non-negotiable security invariants for future implementation.

## Edge Invariants

- The Raspberry Pi must not expose an inbound management API.
- The network-facing `dhcp-agent` must not run as root.
- The privileged `dhcp-apply-helper` must be local-only and have no network listener.
- The helper must not accept arbitrary shell commands, arbitrary service names, arbitrary file paths, or arbitrary ownership/mode instructions.
- The helper may write only managed `dnsmasq` files under approved paths such as `/etc/dnsmasq.d/managed/`.

## Desired State Only

The server publishes desired state as signed config artifacts and structured notifications. It must never instruct an appliance to run arbitrary commands or edit arbitrary files.

## Signed Artifacts

Config artifacts must be immutable by version, include file hashes, and be signed by the control plane. The agent must verify the artifact hash, manifest, signature, target site/device, and version before staging.

## Least Privilege

The agent performs network communication and validation as an unprivileged process. The helper performs only the narrow privileged apply operation after local validation. Credentials must be stored with restrictive file permissions.

## Public View

Public read-only views are disabled by default. When enabled, they must be backed by sanitized published snapshots. Anonymous endpoints must not expose admin APIs, internal IDs, device credentials, deployment logs, audit records, rendered config files, or hidden columns.

## RBAC Foundation

The backend now has organization and site membership role foundations. Organization roles separate owners/admins from viewers and auditors. Site roles separate site admins, DHCP editors, viewers, public publishers, and device installers. Permission helpers enforce authenticated viewer versus editor/admin behavior for future API chunks.

Anonymous public viewing is still future work. It must remain separate from authenticated admin APIs and must use sanitized published snapshots.

## API Security

Authenticated read API endpoints use membership and RBAC visibility rules. Inaccessible organization and site detail endpoints return 404 to avoid object-existence leakage. The health endpoint is anonymous but intentionally minimal. There is no public no-login DHCP/IPAM table endpoint yet.

## Audit

The backend now has append-only audit event records at the model layer. Future implementation must audit meaningful actions, including login events, membership changes, site and reservation changes, imports, config version creation and approval, deployments, rollback, public view changes, enrollment token creation, device enrollment, revocation, and replacement.

## Rollback

The apply helper must eventually provide atomic application and rollback. It must not leave `dnsmasq` stopped when a previous known-good configuration can be restored.

This scaffold does not implement these controls yet; it establishes the contract future code must satisfy.
