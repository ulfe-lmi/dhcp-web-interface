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

## Audit

Future implementation must audit meaningful actions, including login events, membership changes, site and reservation changes, imports, config version creation and approval, deployments, rollback, public view changes, enrollment token creation, device enrollment, revocation, and replacement.

## Rollback

The apply helper must eventually provide atomic application and rollback. It must not leave `dnsmasq` stopped when a previous known-good configuration can be restored.

This scaffold does not implement these controls yet; it establishes the contract future code must satisfy.
