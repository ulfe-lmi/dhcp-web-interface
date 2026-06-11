# Scope and Roadmap

## 1. Bootstrap Scaffold

Create repository structure, docs, placeholder code, scripts, and CI. No production DHCP logic.

## 2. Backend Domain Model and Validation

Foundation implemented for organizations, sites, IPv4 subnets, DHCP pools, and static DHCP reservations with model-level validation and tests. Future backend chunks still need devices, config versions, deployments, public publication settings, and broader validation.

## 3. Access, RBAC, and Audit Foundation

Foundation implemented for organization memberships, site memberships, permission helper functions, and append-only audit events. Future chunks still need API enforcement, automatic audit logging for mutations, and authentication flows.

## 4. Backend Dependency Hygiene

Foundation implemented for backend Python dependency management with `apps/server/pyproject.toml`, committed `apps/server/uv.lock`, and uv-based CI/check workflows.

## 5. Read-Only Backend API Foundation

Foundation implemented for Django REST Framework routing under `/api/v1/`, health and current-user endpoints, and permission-scoped read-only organization and site endpoints.

## 6. Membership-Management API Foundation

Foundation implemented for authenticated organization and site membership-management endpoints with conservative RBAC, last-owner protection, cross-parent protections, safe serializers, and audit events for successful membership mutations. Future chunks still need authentication flows and broader automatic audit logging.

## 7. DHCP/IPAM CRUD API Foundation

Foundation implemented for authenticated IPv4 subnet, DHCP pool, and DHCP reservation management APIs. Authorized editors can create, update, and disable reservations with IP address, MAC address, hostname, and description. Viewers can read visible DHCP/IPAM data but cannot mutate it. Mutations use existing model validation, enforce cross-parent protections, and write audit events. Future chunks still need config versions, rendering, deployments, imports, and frontend workflows.

## 8. Config Renderer and Artifact Schema

Render deterministic `dnsmasq` files from structured state. Produce immutable signed artifacts with hashes and schema validation.

## 9. Public Read-Only Snapshot

Implement opt-in public publication backed by sanitized snapshots with column controls and no admin API exposure.

## 10. Device Gateway Protocol Skeleton

Define versioned device messages, authentication boundaries, heartbeats, config notifications, deployment results, and lease report ingress.

## 11. Pi Agent Skeleton

Implement outbound connection, local config loading, device authentication, artifact download, verification, staging, heartbeat, and report loop.

## 12. Apply Helper and dnsmasq Validation

Implement the local-only privileged helper with strict path controls, no arbitrary commands, `dnsmasq --test`, atomic apply, restart/reload, and rollback.

## 13. Deployment Lifecycle

Track deployment requests, state transitions, result reporting, timeouts, rollback records, and audit events.

## 14. UI Editor

Build authenticated management UI for sites, subnets, reservations, devices, deployments, public view settings, and audit.

## 15. Import/Export

Add CSV/XLSX import preview, mapping, conflict detection, error report download, draft commit, validation, diff review, and export.

## 16. Observability and Security Hardening

Add structured logs, metrics, alerting, secret scanning, vulnerability scanning, license scanning, SBOM generation, and threat-model regression checks.

## 17. Packaging and Release

Add server images, deployment manifests, Pi packages, systemd units, upgrade strategy, release checklist, and production operations docs.
