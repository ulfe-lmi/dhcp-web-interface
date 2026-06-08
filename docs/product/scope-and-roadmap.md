# Scope and Roadmap

## 1. Bootstrap Scaffold

Create repository structure, docs, placeholder code, scripts, and CI. No production DHCP logic.

## 2. Backend Domain Model and Validation

Foundation implemented for organizations, sites, IPv4 subnets, DHCP pools, and static DHCP reservations with model-level validation and tests. Future backend chunks still need users, roles, devices, config versions, deployments, public publication settings, audit events, and broader validation.

## 3. Config Renderer and Artifact Schema

Render deterministic `dnsmasq` files from structured state. Produce immutable signed artifacts with hashes and schema validation.

## 4. Public Read-Only Snapshot

Implement opt-in public publication backed by sanitized snapshots with column controls and no admin API exposure.

## 5. Device Gateway Protocol Skeleton

Define versioned device messages, authentication boundaries, heartbeats, config notifications, deployment results, and lease report ingress.

## 6. Pi Agent Skeleton

Implement outbound connection, local config loading, device authentication, artifact download, verification, staging, heartbeat, and report loop.

## 7. Apply Helper and dnsmasq Validation

Implement the local-only privileged helper with strict path controls, no arbitrary commands, `dnsmasq --test`, atomic apply, restart/reload, and rollback.

## 8. Deployment Lifecycle

Track deployment requests, state transitions, result reporting, timeouts, rollback records, and audit events.

## 9. UI Editor

Build authenticated management UI for sites, subnets, reservations, devices, deployments, public view settings, and audit.

## 10. Import/Export

Add CSV/XLSX import preview, mapping, conflict detection, error report download, draft commit, validation, diff review, and export.

## 11. Observability and Security Hardening

Add structured logs, metrics, alerting, secret scanning, vulnerability scanning, license scanning, SBOM generation, and threat-model regression checks.

## 12. Packaging and Release

Add server images, deployment manifests, Pi packages, systemd units, upgrade strategy, release checklist, and production operations docs.
