# agents.md — Cloud-Managed DHCP/IPAM Appliance Product Specification

**Project codename:** Managed DHCP/IPAM Edge Appliance  
**Primary goal:** Build a professional, secure, sellable two-tier DHCP/IPAM management product where a cloud/server-side control plane is the source of truth and Raspberry Pi edge appliances reconcile local `dnsmasq` DHCP/DNS configuration from that source of truth.

This document is written for coding agents working inside a GitHub repository. It is intentionally detailed and prescriptive. Treat it as the project contract.

---

## 0. Non-negotiable product idea

We are **not** building:

- a web form that edits `/etc/dnsmasq.conf`;
- a remote SSH wrapper;
- a root daemon that accepts arbitrary TCP commands;
- a Raspberry Pi-hosted router-like admin page;
- a hobby script that rewrites DHCP reservations.

We are building:

> A professional DDI-lite control plane with authenticated management UI, optional public read-only IP table publication, immutable configuration versions, auditable deployments, and hardened Raspberry Pi edge agents that apply signed desired-state configuration to local `dnsmasq`.

The system must feel like a real SaaS/network appliance product. The Raspberry Pi is replaceable. The server is the source of truth. Every deployment is versioned, validated, auditable, and rollback-capable.

---

## 1. Architectural principles

### 1.1 Source of truth

The server-side database is the authoritative source of truth for:

- organizations/tenants;
- sites/networks;
- devices/appliances;
- DHCP subnets;
- address pools;
- static reservations;
- DNS host records;
- DHCP options;
- public read-only publication settings;
- config versions;
- deployments;
- audit events;
- lease reports from edge appliances.

The Raspberry Pi must not be treated as the source of truth. If a Pi dies, a new Pi can be enrolled and will receive the latest approved configuration.

### 1.2 Desired state, not remote commands

The cloud/server control plane publishes **desired state**. The Pi agent reconciles local state to desired state.

The server must not say:

```text
run this shell command
edit this file
restart this service using arbitrary command
```

The server may say:

```json
{
  "type": "config_available",
  "site_id": "site_...",
  "device_id": "dev_...",
  "version": 42,
  "artifact_url": "..."
}
```

The agent then downloads a signed config artifact, validates it, stages it, tests it, applies it atomically, and reports the result.

### 1.3 No inbound Pi access

The Pi appliance must not expose an inbound management API. It should make an outbound TLS connection to the server-side device gateway, ideally on TCP 443.

This allows deployment behind NAT, on customer LANs, and without router port-forwarding.

### 1.4 Least privilege on the Pi

The network-facing agent must not run as root.

Use two local components:

```text
dhcp-agent
  - unprivileged long-running daemon
  - has outbound network access
  - authenticates to control plane
  - receives config availability messages
  - downloads signed artifacts
  - validates artifact signature/hash
  - requests local application

dhcp-apply-helper
  - tiny privileged local helper
  - root-owned
  - no network access
  - writes only managed dnsmasq files
  - runs dnsmasq validation
  - reloads/restarts dnsmasq
  - performs rollback
```

The privileged helper must not accept arbitrary paths, arbitrary commands, arbitrary service names, or arbitrary file contents from a remote socket. It should apply only already-validated staged artifacts from a fixed local directory.

### 1.5 Public read-only view is a separate publication path

The product must support two user-visible access levels:

1. authenticated view/edit management UI;
2. optional no-login public read-only table view.

But the public view must be implemented as a **separate sanitized published snapshot**, not by exposing the normal admin API without authentication.

Correct model:

```text
/private/sites/{site_id}/reservations
  -> authenticated API
  -> full model
  -> permissions checked

/public/{public_slug}
  -> no login
  -> reads sanitized snapshot only
  -> no admin API
  -> no device API
  -> no live write paths
```

The public view must be disabled by default.

---

## 2. Recommended technology stack

Agents must prefer boring, maintainable, widely used, open-source components with commercially compatible licensing where possible.

### 2.1 Server-side stack

Recommended baseline:

```text
Operating system:
  Debian stable or Ubuntu Server LTS

Reverse proxy:
  Caddy
  Alternative: nginx

Backend:
  Python
  Django LTS
  Django REST Framework
  Celery

Database:
  PostgreSQL

Cache/broker:
  Valkey

Device gateway:
  Go service

Frontend:
  Next.js
  React
  TypeScript
  Tailwind CSS
  shadcn/ui
  AG Grid Community
  Apache ECharts

Packaging/deployment:
  Docker/OCI images for server components
  docker-compose for local development
  production deployment can later be Helm/systemd/docker compose

Observability:
  structured JSON logs
  Prometheus metrics
  Alertmanager alerts
  optional Grafana dashboards

Security/release tooling:
  Syft for SBOM
  Trivy for vulnerability/license scanning
  gitleaks for secret scanning
  ruff/mypy/eslint/tsc for code quality
```

### 2.2 Raspberry Pi stack

Recommended baseline:

```text
Operating system:
  Raspberry Pi OS Lite or Debian

Service manager:
  systemd

DHCP/DNS:
  dnsmasq

Agent:
  Go static binary

Privileged helper:
  Go static binary or tiny Rust/C helper
  Prefer Go for consistency unless there is a strong reason otherwise

Local firewall:
  nftables or ufw

Logs:
  journald
```

### 2.3 Licensing guardrails

Agents must not introduce dependencies with commercial licensing surprises without explicit approval.

Rules:

- Prefer MIT/BSD/Apache-2.0 style dependencies.
- GPL/LGPL system components such as `dnsmasq`, Linux packages, and systemd may be used as separate installed programs.
- Do not copy GPL code into proprietary project code.
- Do not modify and redistribute GPL components without planning source disclosure obligations.
- Do not use AG Grid Enterprise features unless the repository has an explicit paid license and approval.
- Do not introduce MinIO, Redis server, or other licensing-sensitive infrastructure casually.
- Add/update third-party notices and SBOM generation.
- Add a CI license check before release.

Every dependency PR must answer:

```text
Why is this dependency needed?
What is its license?
Is it used server-side, frontend, agent-side, or build-only?
Is there a simpler standard-library alternative?
Does it affect commercial distribution?
```

---

## 3. Repository layout

Agents should create or maintain a monorepo layout similar to this:

```text
/
  agents.md
  README.md
  LICENSE
  NOTICE
  Makefile
  docker-compose.yml
  .env.example
  .gitignore
  .github/
    workflows/
      ci.yml
      security.yml

  docs/
    architecture.md
    security-model.md
    deployment-model.md
    public-view-model.md
    agent-protocol.md
    dnsmasq-rendering.md
    testing.md
    release-checklist.md
    operations.md
    threat-model.md
    api.md
    database.md

  backend/
    pyproject.toml
    manage.py
    config/
      settings/
        base.py
        local.py
        test.py
        production.py
      urls.py
      asgi.py
      wsgi.py
    apps/
      accounts/
      organizations/
      ipam/
      dhcp/
      dns/
      devices/
      deployments/
      public_views/
      audit/
      imports/
      api/
    tests/

  frontend/
    package.json
    pnpm-lock.yaml
    next.config.js
    tsconfig.json
    src/
      app/
      components/
      features/
        auth/
        dashboard/
        sites/
        reservations/
        public-view/
        devices/
        deployments/
        imports/
      lib/
      styles/
    tests/

  gateway/
    go.mod
    cmd/
      device-gateway/
    internal/
      auth/
      protocol/
      registry/
      transport/
      telemetry/
    tests/

  agent/
    go.mod
    cmd/
      dhcp-agent/
      dhcp-apply-helper/
    internal/
      config/
      protocol/
      artifact/
      apply/
      dnsmasq/
      systemd/
      leases/
      security/
    packaging/
      systemd/
        dhcp-agent.service
      debian/
    tests/

  shared/
    schemas/
      device-protocol/
      config-artifact/
      public-snapshot/
    testdata/
      dnsmasq/
      imports/
      artifacts/

  scripts/
    dev-up.sh
    dev-down.sh
    lint.sh
    test.sh
    security-scan.sh
    generate-sbom.sh
    build-agent-deb.sh
```

Agents may adapt exact names, but the conceptual separation must remain:

- backend business logic;
- frontend UI;
- device gateway;
- Pi agent/helper;
- shared schemas/test fixtures;
- docs.

---

## 4. Domain model

### 4.1 Tenancy and organization model

Required objects:

```text
Organization
  id
  name
  slug
  created_at
  updated_at

User
  id
  email
  display_name
  password/auth fields
  mfa fields
  is_active
  created_at
  updated_at

Membership
  organization_id
  user_id
  role
  created_at
  updated_at
```

Recommended roles:

```text
Owner
  full organization control

Admin
  manage users, sites, devices, settings

DHCP Editor
  create/edit DHCP/IPAM data
  submit deployment drafts

Viewer
  authenticated read-only access

Public Publisher
  enable/disable public read-only table
  configure visible public fields

Device Installer
  create enrollment tokens
  enroll/replace appliances

Auditor
  read-only access to audit/deployment history
```

Implement role-based access control. Do not rely only on frontend hiding.

### 4.2 Site and network model

Required objects:

```text
Site
  id
  organization_id
  name
  slug
  description
  timezone
  created_at
  updated_at

NetworkSegment / Subnet
  id
  site_id
  cidr
  name
  description
  gateway_ip
  default_dns_servers
  default_domain
  lease_time
  enabled
  created_at
  updated_at
```

Validation rules:

- CIDR must be valid IPv4 initially.
- IPv6 may be roadmap, but design model to not make it impossible.
- Gateway must belong to subnet if provided.
- DNS servers must be valid IP addresses.
- Lease time must be bounded and valid for dnsmasq rendering.
- Overlapping subnets within the same site must be rejected unless an explicit future VRF/VLAN model is introduced.

### 4.3 DHCP pool model

```text
DhcpPool
  id
  subnet_id
  start_ip
  end_ip
  lease_time_override
  tag
  enabled
  created_at
  updated_at
```

Validation:

- start/end must belong to subnet;
- start <= end;
- no pool overlaps with another pool in same subnet unless explicitly supported;
- pool must not include reserved gateway/broadcast/network address;
- pool should warn when overlapping static reservations.

### 4.4 Static reservation model

```text
DhcpReservation
  id
  site_id
  subnet_id
  mac_address
  ip_address
  hostname
  description
  owner
  location
  device_type
  tags
  enabled
  created_at
  updated_at
```

Validation:

- MAC address normalized to lowercase colon form: `aa:bb:cc:dd:ee:ff`.
- IP address must belong to subnet.
- Duplicate MAC address in same site must be rejected unless explicitly allowed by a future multi-interface model.
- Duplicate IP in same site must be rejected.
- Hostname must be valid and sanitized.
- Disabled reservations should remain in history but not render into active config.
- User-facing import should detect duplicates and present conflicts before saving.

### 4.5 DNS host record model

Initial product may derive DNS records from DHCP reservations.

Optional explicit model:

```text
DnsHostRecord
  id
  site_id
  hostname
  fqdn
  ip_address
  aliases
  ttl
  enabled
```

Validation:

- Hostnames/FQDNs must be valid.
- IP must be valid.
- Duplicate hostnames must be prevented in the same DNS zone unless explicitly supported.

### 4.6 DHCP options model

Represent common options structurally, not as arbitrary raw text.

```text
DhcpOption
  id
  site_id
  subnet_id nullable
  pool_id nullable
  reservation_id nullable
  option_code
  option_name
  value
  value_type
  tag
  enabled
```

Initial supported options:

- router/gateway;
- DNS servers;
- domain name;
- NTP servers;
- lease time;
- PXE/TFTP server;
- boot filename;
- vendor-specific option only if validated.

Avoid arbitrary raw dnsmasq options in MVP. If advanced raw options are added later, they must be separately gated, validated, audited, and clearly marked dangerous.

### 4.7 Device/appliance model

```text
Device
  id
  organization_id
  site_id nullable until assigned
  name
  serial
  device_public_key
  certificate_fingerprint
  status
  last_seen_at
  last_ip
  software_version
  agent_version
  current_config_version
  desired_config_version
  created_at
  updated_at
```

Statuses:

```text
pending_enrollment
online
offline
applying
healthy
degraded
failed
revoked
replaced
```

### 4.8 Enrollment token model

```text
EnrollmentToken
  id
  organization_id
  site_id nullable
  token_hash
  description
  expires_at
  used_at
  used_by_device_id
  created_by_user_id
  revoked_at
  created_at
```

Rules:

- token must be single-use;
- token must be time-limited;
- token stored hashed, not plaintext;
- token may be site-scoped;
- token use must create audit event;
- token must be revocable.

### 4.9 Config version model

```text
ConfigVersion
  id
  organization_id
  site_id
  version_number
  status
  created_by_user_id
  approved_by_user_id nullable
  source_kind
  change_summary
  validation_result
  artifact_hash
  artifact_signature
  created_at
  approved_at
```

Statuses:

```text
draft
validated
validation_failed
approved
deployed
superseded
rolled_back
archived
```

### 4.10 Deployment model

```text
Deployment
  id
  site_id
  device_id
  config_version_id
  requested_by_user_id
  status
  started_at
  completed_at
  result_code
  result_message
  previous_config_version_id
  agent_report
```

Statuses:

```text
queued
notified
downloaded
staged
validating
applying
restarting
health_check
succeeded
failed
rolled_back
timeout
cancelled
```

### 4.11 Lease report model

```text
LeaseReport
  id
  device_id
  site_id
  observed_at
  raw_digest
  parsed_count
  created_at

LeaseObservation
  id
  lease_report_id
  mac_address
  ip_address
  hostname
  client_id
  lease_expiry
  state
```

Lease reporting is informational. It must not overwrite reservations automatically without user action.

### 4.12 Public read-only publication model

```text
PublishedSiteView
  id
  site_id
  public_slug
  enabled
  visible_columns
  allow_csv_export
  expose_mac_addresses
  expose_owner
  expose_location
  expose_description
  expose_lease_status
  last_published_config_version_id
  created_by_user_id
  updated_by_user_id
  created_at
  updated_at

PublishedReservationSnapshot
  id
  published_site_view_id
  config_version_id
  ip_address
  hostname
  label
  description
  location
  owner_public
  device_type
  mac_address_plain nullable
  mac_address_hash nullable
  lease_status nullable
  sort_key
```

Public snapshot must contain only sanitized data. The anonymous public endpoint must read only this snapshot.

---

## 5. Server backend requirements

### 5.1 Backend responsibilities

The backend must provide:

- authentication and authorization;
- organization/site/device management;
- IPAM/DHCP data CRUD;
- validation engine;
- config version creation;
- config rendering;
- config artifact signing;
- deployment creation and state tracking;
- public snapshot publication;
- import/export;
- audit logging;
- API for frontend;
- API for device gateway integration.

### 5.2 API principles

All mutation endpoints must:

- require authentication;
- verify organization membership;
- verify role/permission;
- validate request body;
- write audit event;
- be covered by tests.

All list/read endpoints must:

- restrict data to the user’s organization;
- avoid leaking cross-tenant identifiers;
- support pagination where relevant;
- support search/filtering for tables.

Public endpoints must:

- require no cookies;
- not call authenticated admin APIs;
- not expose internal IDs unless designed;
- use public slugs rather than sequential IDs;
- be rate-limited;
- be cacheable where possible.

### 5.3 Authentication

MVP:

- email/password login;
- password reset;
- session-based browser authentication;
- CSRF protection;
- secure cookies;
- optional TOTP MFA if feasible in first milestone.

Roadmap:

- OIDC login;
- Keycloak support;
- Microsoft Entra / Google Workspace integration;
- SAML only if demanded by customers.

### 5.4 Authorization

Implement backend permissions for every operation.

Example permission matrix:

```text
Operation                                Owner  Admin  Editor  Viewer  Publisher  Installer  Auditor
View private DHCP table                  yes    yes    yes     yes     yes        no         yes
Edit reservation                         yes    yes    yes     no      no         no         no
Create config draft                      yes    yes    yes     no      no         no         no
Approve deployment                       yes    yes    maybe   no      no         no         no
Rollback deployment                      yes    yes    no      no      no         no         no
Enable public view                       yes    yes    no      no      yes        no         no
Create enrollment token                  yes    yes    no      no      no         yes        no
View audit log                           yes    yes    no      no      no         no         yes
Manage users                             yes    yes    no      no      no         no         no
```

Do not rely on frontend enforcement.

### 5.5 Audit logging

Every meaningful action must generate an audit event:

```text
user.login
user.logout
user.failed_login
user.invited
membership.created
membership.updated
site.created
site.updated
subnet.created
subnet.updated
pool.created
reservation.created
reservation.updated
reservation.deleted_or_disabled
import.started
import.validated
import.committed
config.version.created
config.version.validated
config.version.approved
deployment.created
deployment.succeeded
deployment.failed
deployment.rolled_back
public_view.enabled
public_view.disabled
public_view.settings_changed
device.enrollment_token_created
device.enrolled
device.revoked
device.replaced
```

Audit event fields:

```text
id
organization_id
site_id nullable
actor_user_id nullable
actor_device_id nullable
event_type
target_type
target_id
ip_address
user_agent
before_json nullable
after_json nullable
metadata_json
created_at
```

Audit events should be append-only.

---

## 6. Frontend requirements

### 6.1 UI quality bar

The UI must look like a professional SaaS product, not like a router config page.

Use:

- clear navigation;
- good spacing;
- consistent typography;
- good empty states;
- loading states;
- error states;
- confirmation dialogs;
- destructive-action warnings;
- responsive layout;
- accessible forms;
- keyboard-friendly tables where feasible.

### 6.2 Required pages

MVP pages:

```text
/auth/login
/auth/forgot-password
/dashboard
/org/settings
/org/users
/sites
/sites/{siteId}
/sites/{siteId}/subnets
/sites/{siteId}/reservations
/sites/{siteId}/leases
/sites/{siteId}/devices
/sites/{siteId}/deployments
/sites/{siteId}/imports
/sites/{siteId}/public-view
/audit
/public/{slug}
```

### 6.3 Reservation table

The core table must support:

- search;
- sort;
- filter;
- inline edit or side-panel edit;
- add reservation;
- bulk paste/import;
- conflict indicators;
- validation warnings;
- disabled reservation display;
- CSV export;
- “convert observed lease to reservation” action;
- diff preview before deployment.

Columns:

```text
IP address
MAC address
Hostname
Description
Owner
Location
Device type
Subnet
Tags
Enabled
Last seen / lease status
Updated at
Updated by
```

MAC display should be normalized.

### 6.4 Import UI

Flow:

```text
Upload CSV/XLSX
  -> map columns
  -> parse preview
  -> normalize values
  -> show conflicts/errors/warnings
  -> allow user to download error report
  -> commit to draft only
  -> validation
  -> review diff
  -> approve/deploy
```

Never import and deploy in one unreviewed step.

### 6.5 Deployment UI

Deployment page must show:

- current approved version;
- currently deployed version per device;
- last heartbeat;
- pending deployment;
- deployment timeline;
- deployment result;
- rollback button;
- rendered config diff;
- validation output.

### 6.6 Public read-only UI

The public page must:

- be attractive and branded;
- show site/network title;
- show last updated timestamp;
- show “read-only public view” marker;
- support search/sort/filter;
- optionally support CSV export;
- expose only configured fields;
- not load authenticated app bundle if avoidable;
- not include admin routes or admin API calls.

Public view admin settings:

```text
Enable public read-only view: off by default
Public slug
Visible columns
Expose MAC addresses: off by default
Expose owner/contact: off by default
Expose lease status: off by default
Allow CSV export: off by default or configurable
Regenerate snapshot after approved deployment
Manual regenerate snapshot
Copy public URL
Disable public view
```

---

## 7. Device gateway requirements

### 7.1 Purpose

The gateway handles connected edge appliances. It should be a small Go service separate from the Django backend.

Responsibilities:

- accept outbound device connections;
- enforce device identity;
- maintain connection registry;
- send config-available notifications;
- accept device heartbeats;
- accept deployment result reports;
- accept lease reports;
- forward events to backend or write through an internal API.

It should not own business logic such as user permissions or IPAM validation.

### 7.2 Protocol

Allowed transports:

- HTTPS long-polling for simplest MVP;
- WebSocket over TLS;
- gRPC streaming over TLS.

Recommended MVP:

```text
WebSocket over TLS with mTLS or signed device token bootstrap,
falling back to HTTPS polling if WebSocket is difficult.
```

Messages must be structured JSON or protobuf. Prefer versioned schemas.

Example messages:

```json
{
  "schema": "device.v1.heartbeat",
  "device_id": "dev_123",
  "agent_version": "0.1.0",
  "current_config_version": 41,
  "uptime_seconds": 123456,
  "dnsmasq_status": "active",
  "timestamp": "2026-06-08T12:00:00Z"
}
```

```json
{
  "schema": "control.v1.config_available",
  "site_id": "site_123",
  "device_id": "dev_123",
  "version": 42,
  "artifact_url": "https://...",
  "artifact_sha256": "...",
  "expires_at": "2026-06-08T12:10:00Z"
}
```

```json
{
  "schema": "device.v1.deployment_result",
  "device_id": "dev_123",
  "deployment_id": "dep_123",
  "version": 42,
  "status": "succeeded",
  "previous_version": 41,
  "started_at": "2026-06-08T12:01:00Z",
  "completed_at": "2026-06-08T12:01:08Z",
  "message": "Applied and dnsmasq active"
}
```

### 7.3 Security

Device identity:

- bootstrap with one-time enrollment token;
- exchange token for device certificate or long-lived device credential;
- store credential securely on Pi;
- support revocation;
- rotate credentials eventually.

Gateway must reject:

- unknown devices;
- revoked devices;
- expired credentials;
- devices claiming another organization/site;
- replayed deployment result messages;
- unsupported protocol versions if not backward-compatible.

### 7.4 Tests

Gateway tests:

- device enrollment happy path;
- rejected invalid token;
- rejected reused token;
- rejected revoked device;
- heartbeat updates last_seen;
- config notification goes only to correct device;
- deployment result accepted only for matching device/deployment;
- malformed messages rejected;
- concurrent devices do not leak state;
- reconnect behavior.

---

## 8. Raspberry Pi agent requirements

### 8.1 Agent responsibilities

The unprivileged `dhcp-agent` must:

- start under systemd;
- read local configuration;
- connect outbound to device gateway;
- authenticate as enrolled device;
- send heartbeat;
- receive config notification;
- download artifact;
- verify artifact hash;
- verify artifact signature;
- verify artifact target matches this device/site;
- stage artifact under `/var/lib/dhcp-agent/staged/{version}`;
- ask helper to apply;
- report apply result;
- report lease observations periodically;
- handle network outages gracefully;
- retry with backoff;
- never delete last known good config.

### 8.2 Local config

Example `/etc/dhcp-agent/agent.toml`:

```toml
server_url = "https://control.example.com"
device_id = "dev_123"
site_id = "site_123"
credential_path = "/var/lib/dhcp-agent/device.crt"
private_key_path = "/var/lib/dhcp-agent/device.key"
state_dir = "/var/lib/dhcp-agent"
log_level = "info"
heartbeat_interval_seconds = 30
lease_report_interval_seconds = 300
```

Permissions:

```text
/etc/dhcp-agent/agent.toml
  owner root
  group dhcp-agent
  mode 0640

/var/lib/dhcp-agent/device.key
  owner root or dhcp-agent depending implementation
  mode 0600
```

### 8.3 Apply helper responsibilities

`dhcp-apply-helper` runs with root privileges and must be tiny.

Allowed operations:

```text
apply --version N --staged-path /var/lib/dhcp-agent/staged/N
rollback --to-version N
status
```

The helper must enforce:

- staged path must be under `/var/lib/dhcp-agent/staged/`;
- version must be numeric/expected;
- artifact manifest must be present;
- target managed path fixed to `/etc/dnsmasq.d/managed/`;
- no symlink traversal;
- no path traversal;
- no arbitrary command execution;
- no arbitrary file ownership/mode from artifact;
- no writes outside approved paths.

### 8.4 Atomic application

Apply flow:

```text
1. Verify staged manifest.
2. Copy rendered dnsmasq files into temp directory:
   /etc/dnsmasq.d/.managed-new-{version}
3. Set ownership root:root.
4. Set modes 0644.
5. Run dnsmasq validation against candidate config.
6. Move current managed directory to backup:
   /etc/dnsmasq.d/.managed-prev-{previous_version}
7. Atomically move candidate to:
   /etc/dnsmasq.d/managed
8. Reload or restart dnsmasq.
9. Verify dnsmasq active.
10. Write local current version state.
11. Return success.
```

On failure:

```text
- restore previous managed directory if swap happened;
- restart/reload dnsmasq;
- verify previous state active;
- return failure with safe diagnostic.
```

Do not leave dnsmasq stopped unless there is no possible previous working config.

### 8.5 dnsmasq rendering and validation

The server renders dnsmasq files. The agent validates syntax before applying.

Managed files:

```text
/etc/dnsmasq.d/managed/10-ranges.conf
/etc/dnsmasq.d/managed/20-options.conf
/etc/dnsmasq.d/managed/30-reservations.conf
/etc/dnsmasq.d/managed/40-hosts.conf
```

Do not rewrite unrelated files.

Agent should prefer `dnsmasq --test` validation. If the exact command needs environment-specific adjustment, implement it behind a function and test it.

### 8.6 Lease reporting

Agent should parse dnsmasq leases file:

```text
/var/lib/misc/dnsmasq.leases
```

Report sanitized lease observations to the server.

Lease report must not block DHCP serving or config application.

### 8.7 Agent tests

Unit tests:

- artifact hash verification;
- signature verification;
- manifest target mismatch rejected;
- path traversal in artifact rejected;
- symlink in artifact rejected;
- invalid version rejected;
- protocol message parsing;
- retry/backoff logic;
- lease parser.

Integration tests using temporary directories:

- apply valid config;
- reject invalid config;
- rollback on validation failure;
- rollback on restart failure;
- preserve previous good config;
- no writes outside temp managed directory;
- helper rejects arbitrary path.

Packaging tests:

- systemd unit exists;
- binary paths correct;
- config directory permissions documented;
- package install script does not start broken service without config.

---

## 9. Config artifact specification

### 9.1 Artifact format

A config artifact is a tar or zip bundle containing:

```text
manifest.json
dnsmasq/
  10-ranges.conf
  20-options.conf
  30-reservations.conf
  40-hosts.conf
sha256sums.txt
signature
```

### 9.2 Manifest

Example:

```json
{
  "schema": "config-artifact.v1",
  "organization_id": "org_123",
  "site_id": "site_123",
  "config_version": 42,
  "created_at": "2026-06-08T12:00:00Z",
  "renderer_version": "0.1.0",
  "target": {
    "backend": "dnsmasq",
    "min_agent_version": "0.1.0"
  },
  "files": [
    {
      "path": "dnsmasq/10-ranges.conf",
      "sha256": "..."
    },
    {
      "path": "dnsmasq/20-options.conf",
      "sha256": "..."
    },
    {
      "path": "dnsmasq/30-reservations.conf",
      "sha256": "..."
    },
    {
      "path": "dnsmasq/40-hosts.conf",
      "sha256": "..."
    }
  ]
}
```

### 9.3 Artifact validation rules

Server:

- generate deterministic config from structured DB state;
- compute hashes;
- sign manifest or full artifact;
- store immutable artifact;
- never mutate artifact for same version.

Agent:

- verify signature;
- verify all file hashes;
- reject unexpected files;
- reject absolute paths;
- reject `..`;
- reject symlinks/hardlinks if using tar;
- reject artifact for wrong site/device if target-specific;
- reject version older than current unless rollback explicitly requested.

---

## 10. dnsmasq config rendering rules

### 10.1 General

Generated config must be deterministic. Same database state must produce byte-for-byte identical config, except for expected generated comments/timestamps. Prefer avoiding timestamps inside rendered files to improve diffs.

Include generated header:

```text
# Generated by Managed DHCP/IPAM Control Plane.
# Do not edit manually.
# Site: <site-name>
# Config version: <version>
```

### 10.2 DHCP ranges

Example:

```text
dhcp-range=set:main,192.168.10.100,192.168.10.199,255.255.255.0,12h
```

Rendering must:

- sort by subnet, then start IP;
- include tags if used;
- avoid duplicate ranges;
- validate lease time.

### 10.3 DHCP options

Example:

```text
dhcp-option=option:router,192.168.10.1
dhcp-option=option:dns-server,192.168.10.1,8.8.8.8
dhcp-option=option:domain-name,example.local
```

Rendering must:

- render only validated known options in MVP;
- escape/sanitize values;
- reject unsupported arbitrary raw options unless advanced mode exists.

### 10.4 Reservations

Example:

```text
dhcp-host=aa:bb:cc:dd:ee:ff,192.168.10.42,printer-lab-1,infinite
```

Rendering must:

- sort by IP address;
- normalize MAC;
- sanitize hostname;
- skip disabled reservations;
- reject duplicate IP/MAC before rendering.

### 10.5 DNS hosts

Option A: render address records:

```text
address=/printer-lab-1.example.local/192.168.10.42
```

Option B: generate hosts file and configure dnsmasq to read it.

Pick one implementation and document it. Prefer structured hosts file if cleaner.

---

## 11. Public read-only view security model

### 11.1 Public view is opt-in

Default:

```text
public view disabled
```

When enabling public view, UI must show warning:

```text
This will publish selected DHCP/IP table fields without login.
Only selected columns will be visible. Do not expose MAC addresses,
owner names, or sensitive device names unless you intend them to be public.
```

### 11.2 Separate snapshot

Public endpoints must query only `PublishedReservationSnapshot` or equivalent.

They must not join live private tables on every request unless carefully sanitized through a dedicated read-only service layer.

### 11.3 Column-level controls

Configurable fields:

```text
IP address
hostname
label/description
location
device type
owner/contact
MAC address
lease status
last updated
```

Dangerous fields default off:

```text
MAC address
owner/contact
lease status
last seen
comments/internal notes
```

### 11.4 Public API restrictions

Public endpoint must:

- never require session cookies;
- never set admin session cookies;
- use rate limiting;
- use cache headers;
- expose no internal organization/user IDs;
- expose no device credentials/tokens;
- expose no rendered dnsmasq files;
- expose no deployment logs;
- expose no audit log.

### 11.5 Tests

Public view tests:

- disabled public view returns 404;
- enabled public view returns sanitized snapshot;
- hidden columns not present in HTML or JSON;
- MAC hidden by default;
- public endpoint cannot access private API;
- public slug collision handled;
- unauthenticated edit attempts fail;
- public CSV respects visible columns.

---

## 12. Import/export requirements

### 12.1 Supported import formats

MVP:

- CSV;
- XLSX.

Use a preview/commit workflow.

### 12.2 Import mapping

Import UI should allow mapping columns:

```text
IP address
MAC address
hostname
description
owner
location
device type
subnet
enabled
tags
```

### 12.3 Import validation

Detect:

- invalid IP;
- invalid MAC;
- IP outside subnet;
- duplicate IP in file;
- duplicate MAC in file;
- duplicate IP against existing data;
- duplicate MAC against existing data;
- invalid hostname;
- missing required fields;
- ambiguous subnet;
- unsafe public fields.

### 12.4 Import result

Import should produce:

```text
rows parsed
rows valid
rows with warnings
rows rejected
changes to create
changes to update
changes to disable
conflict report
```

Only after confirmation should changes be written.

Then changes create a config draft, not immediate deployment.

### 12.5 Tests

- valid CSV import;
- valid XLSX import;
- invalid IP rejected;
- invalid MAC rejected;
- duplicates detected;
- update existing reservation;
- import cannot bypass permissions;
- import creates audit events;
- import does not deploy automatically.

---

## 13. Testing strategy

Testing is mandatory. Agents must not implement large features without tests.

### 13.1 Test pyramid

Required layers:

```text
Unit tests
  backend validators/renderers
  frontend pure components/utilities
  gateway protocol parsing
  agent artifact/apply logic

Integration tests
  backend API with database
  config rendering from DB state
  public snapshot generation
  gateway/backend interaction
  agent helper using temp directories

End-to-end tests
  browser user flow:
    login
    create site
    create subnet
    add reservations
    validate config
    deploy
    view deployment result
    enable public view
    verify public table

Security tests
  authz boundaries
  public/private separation
  path traversal artifacts
  invalid tokens
  revoked devices
```

### 13.2 Backend tests

Use pytest or Django test framework. Prefer pytest-django if repo standard allows.

Test categories:

```text
accounts/
  test_login.py
  test_permissions.py
  test_mfa.py if implemented

ipam/
  test_ip_validation.py
  test_mac_validation.py
  test_subnet_overlap.py
  test_reservation_conflicts.py

dhcp/
  test_dnsmasq_rendering.py
  test_dhcp_options.py
  test_config_versioning.py

devices/
  test_enrollment.py
  test_device_status.py
  test_revocation.py

deployments/
  test_create_deployment.py
  test_deployment_state_machine.py
  test_rollback_model.py

public_views/
  test_public_snapshot.py
  test_public_endpoint.py
  test_public_column_visibility.py

imports/
  test_csv_import.py
  test_xlsx_import.py
  test_import_conflicts.py

audit/
  test_audit_events.py
```

### 13.3 Frontend tests

Required:

- TypeScript typecheck;
- lint;
- component tests for critical table/forms;
- Playwright end-to-end tests.

Critical E2E flows:

```text
admin login
create site/subnet
add reservation
bulk import preview
validation error shown
config diff shown
deploy action visible only to permitted role
viewer cannot edit
public view disabled gives 404
public view enabled displays sanitized table
```

### 13.4 Gateway tests

Required:

- Go unit tests;
- race tests where feasible;
- integration tests with mock backend;
- protocol compatibility tests.

Run:

```text
go test ./...
go test -race ./...
```

### 13.5 Agent tests

Required:

- Go unit tests;
- artifact extraction tests;
- path traversal tests;
- local helper integration tests with temp directories;
- fake dnsmasq validator command;
- rollback tests.

Do not require real root privileges for normal CI tests. Use abstractions/mocks and temp dirs.

Separate optional hardware tests may run on a real Raspberry Pi.

### 13.6 CI gates

Every PR must pass:

```text
backend:
  formatting
  lint
  type checks where configured
  tests
  migrations check

frontend:
  npm/pnpm install from lockfile
  lint
  typecheck
  tests
  production build

gateway:
  gofmt
  go vet
  go test ./...

agent:
  gofmt
  go vet
  go test ./...

security:
  secret scan
  dependency vulnerability scan
  license scan
  SBOM generation
```

### 13.7 Acceptance criteria per feature

Every feature PR must include:

- implementation;
- tests;
- docs update if user/admin/operator behavior changes;
- migration if DB changed;
- audit event if state-changing;
- security review note if public/device/auth-related;
- screenshot or UI evidence for frontend-heavy changes where feasible.

---

## 14. Work in chunks: implementation roadmap

Agents must work in small, reviewable chunks. Do not attempt the entire product in one PR.

### Milestone 0 — Repository bootstrap

Goal: create buildable skeleton.

Deliverables:

- monorepo structure;
- backend Django project;
- frontend Next.js project;
- Go gateway skeleton;
- Go agent skeleton;
- docker-compose for local dev;
- Makefile;
- CI workflow;
- docs skeleton;
- `.env.example`.

Tests/checks:

- backend test placeholder passes;
- frontend build passes;
- Go tests pass;
- CI green.

Acceptance:

- `make dev` or documented equivalent starts local stack;
- `make test` runs all test suites or clearly documented subset.

### Milestone 1 — Accounts, organizations, RBAC

Goal: authenticated product shell.

Deliverables:

- user model/auth;
- organization model;
- membership/roles;
- login/logout;
- invite or create user flow;
- backend permissions;
- basic admin dashboard.

Tests:

- login success/failure;
- role enforcement;
- cross-organization isolation;
- unauthenticated access rejected.

Acceptance:

- admin can log in;
- viewer cannot access edit endpoints;
- org A cannot see org B.

### Milestone 2 — IPAM/DHCP data model

Goal: manage structured network data.

Deliverables:

- sites;
- subnets;
- DHCP pools;
- reservations;
- validation;
- CRUD APIs;
- frontend pages/forms/table.

Tests:

- IP/MAC validation;
- duplicate detection;
- subnet membership;
- permission checks;
- frontend form validation.

Acceptance:

- admin/editor can create a site, subnet, pool, reservation;
- invalid data is rejected with useful errors;
- viewer can see but not edit.

### Milestone 3 — dnsmasq renderer and config versions

Goal: convert DB state to deterministic config.

Deliverables:

- renderer service;
- generated managed dnsmasq files;
- config version model;
- draft/validate/approve states;
- config diff view;
- artifact manifest/hash/signing placeholder or real signing.

Tests:

- deterministic rendering;
- sorted output;
- duplicate rejection;
- option rendering;
- config version immutability;
- artifact hash generation.

Acceptance:

- user can create validated config version from site data;
- UI can show diff before approval.

### Milestone 4 — Public read-only view

Goal: optional no-login professional table.

Deliverables:

- public view settings;
- sanitized snapshot generation;
- public page;
- public JSON endpoint;
- visible column controls;
- warning UI;
- optional CSV export.

Tests:

- disabled returns 404;
- hidden columns absent;
- MAC hidden by default;
- unauthenticated public access works only to public snapshot;
- private APIs still require login.

Acceptance:

- admin can enable public view;
- unauthenticated user sees only configured fields;
- disabling removes public access.

### Milestone 5 — Device enrollment model

Goal: represent Pi appliances and enrollment.

Deliverables:

- device model;
- enrollment token model;
- token creation/revocation;
- enrollment API;
- device status page;
- audit events.

Tests:

- single-use token;
- expired token rejected;
- revoked token rejected;
- token hash storage;
- device created on enrollment.

Acceptance:

- installer can create token;
- agent can enroll using token;
- device appears in UI.

### Milestone 6 — Device gateway MVP

Goal: allow devices to connect and send heartbeats.

Deliverables:

- Go gateway service;
- device authentication integration;
- heartbeat protocol;
- backend status update;
- connection registry.

Tests:

- valid device heartbeat;
- invalid auth rejected;
- revoked device rejected;
- last_seen updated;
- concurrent device connections.

Acceptance:

- mock agent can connect and update online status.

### Milestone 7 — Agent artifact download and validation

Goal: agent can retrieve and validate config artifacts.

Deliverables:

- agent config file;
- outbound connection/client;
- config-available handling;
- artifact download;
- hash/signature verification;
- staging directory;
- result report.

Tests:

- valid artifact accepted;
- invalid hash rejected;
- wrong site rejected;
- path traversal rejected;
- network retry behavior.

Acceptance:

- mock gateway can instruct agent to download artifact;
- agent stages valid artifact and reports status.

### Milestone 8 — Pi apply helper and dnsmasq integration

Goal: apply config locally safely.

Deliverables:

- root helper;
- managed dnsmasq directory logic;
- staging/apply/rollback;
- dnsmasq validation command wrapper;
- systemd service files;
- local state tracking.

Tests:

- apply valid candidate;
- reject invalid candidate;
- rollback after failure;
- no writes outside allowed paths;
- helper rejects malicious paths.

Acceptance:

- on test Pi or simulated environment, valid config applies and service reloads/restarts.

### Milestone 9 — Deployments end-to-end

Goal: control plane can deploy approved version to device.

Deliverables:

- deployment model;
- deployment API;
- gateway notification;
- agent apply;
- result reporting;
- UI deployment timeline;
- rollback request.

Tests:

- deploy success;
- deploy failure;
- timeout;
- rollback;
- device offline queue behavior;
- permissions.

Acceptance:

- user edits reservation, approves version, deploys to Pi, sees success.

### Milestone 10 — Lease reporting

Goal: observe active DHCP leases.

Deliverables:

- agent lease parser;
- lease report upload;
- backend storage;
- UI leases page;
- convert lease to reservation.

Tests:

- parse dnsmasq lease file;
- upload report;
- permission checks;
- convert lease flow;
- lease report does not overwrite reservations automatically.

Acceptance:

- UI shows observed leases from Pi;
- admin can convert lease to reservation draft.

### Milestone 11 — Import/export

Goal: replace manual Excel workflow.

Deliverables:

- CSV import;
- XLSX import;
- mapping UI;
- preview/conflict report;
- commit to draft;
- CSV export;
- optional public CSV export.

Tests:

- valid CSV/XLSX import;
- invalid rows;
- duplicate conflicts;
- permission checks;
- audit events.

Acceptance:

- existing Excel table can be imported safely with preview.

### Milestone 12 — Production hardening

Goal: product can be piloted.

Deliverables:

- deployment docs;
- backup/restore docs;
- security docs;
- SBOM;
- vulnerability scan;
- license report;
- structured logs;
- Prometheus metrics;
- alert rules;
- release checklist.

Tests/checks:

- CI green;
- dependency scans acceptable;
- backup/restore tested;
- basic load test;
- threat model reviewed.

Acceptance:

- documented pilot deployment can be installed by an operator.

---

## 15. Security invariants

Agents must preserve these invariants in all changes:

1. The Pi must initiate outbound connections only.
2. The network-facing Pi agent must not run as root.
3. The privileged helper must not have network access.
4. The server must never send arbitrary shell commands to devices.
5. Config artifacts must be immutable once published.
6. Config artifacts must be hashed and signed before production deployment.
7. The agent must verify artifact integrity before applying.
8. The agent must reject path traversal/symlink artifacts.
9. The agent must preserve last known good configuration.
10. The agent must rollback on failed apply if possible.
11. Public no-login view must read only sanitized snapshot data.
12. Public view must be disabled by default.
13. Backend authorization must be enforced server-side.
14. Cross-tenant data access must be impossible by construction and tested.
15. Every mutation must be auditable.
16. Enrollment tokens must be single-use, expiring, hashed at rest, and revocable.
17. Device credentials must be revocable.
18. Rendered dnsmasq config must come from structured validated data, not arbitrary user text in MVP.
19. Excel/CSV import must preview and validate before commit.
20. Import must not deploy automatically.

---

## 16. Threat model summary

### 16.1 Threats

Consider at least:

- attacker guesses public URL;
- attacker abuses public view to enumerate devices;
- authenticated viewer tries edit API directly;
- editor from one organization tries access another organization;
- stolen enrollment token;
- reused enrollment token;
- stolen device credential;
- malicious config artifact;
- path traversal in artifact;
- symlink attack in artifact;
- dnsmasq invalid config causes DHCP outage;
- failed restart leaves DHCP down;
- compromised Pi tries to impersonate another site;
- replayed deployment result;
- malicious Excel import;
- dependency vulnerability;
- leaked secrets in repo;
- admin accidentally publishes MAC addresses.

### 16.2 Required mitigations

- random/non-enumerable public slugs;
- optional public view warning and column controls;
- rate limiting public endpoints;
- strict backend RBAC;
- tenant scoping in every query;
- token hashing/expiry/single-use;
- certificate/device credential revocation;
- signed artifacts;
- artifact extraction hardening;
- dnsmasq validation before apply;
- rollback;
- audit logging;
- import preview;
- CI secret scanning;
- dependency scanning;
- SBOM generation.

---

## 17. Operational requirements

### 17.1 Backups

Must support:

- PostgreSQL backup;
- config artifact backup;
- restore procedure;
- test restore procedure.

Document:

```text
backup frequency
retention
restore command
restore validation
```

### 17.2 Logs

Use structured logs.

Required server log fields:

```text
timestamp
level
request_id
user_id nullable
organization_id nullable
site_id nullable
event
message
```

Required agent log fields:

```text
timestamp
level
device_id
site_id
event
version nullable
message
```

Never log:

- plaintext enrollment tokens;
- private keys;
- passwords;
- full secrets;
- unnecessary MAC addresses in public logs unless appropriate.

### 17.3 Metrics

Server metrics:

- request count/latency;
- API errors;
- auth failures;
- deployment success/failure;
- connected devices;
- offline devices;
- config validation failures.

Agent metrics/status:

- last heartbeat;
- current config version;
- last apply result;
- dnsmasq status;
- lease count;
- uptime;
- software version.

### 17.4 Alerts

Minimum alerts:

- device offline too long;
- deployment failed;
- config validation failed repeatedly;
- public view enabled with MAC addresses exposed;
- backup failed;
- certificate/credential near expiry if implemented.

---

## 18. Documentation requirements

Docs must be kept current.

Required docs:

```text
README.md
  what product is
  local dev quickstart
  architecture summary

docs/architecture.md
  components and data flow

docs/security-model.md
  auth, RBAC, device identity, public view risks

docs/deployment-model.md
  config versions, deployments, rollback

docs/public-view-model.md
  anonymous read-only publication design

docs/agent-protocol.md
  device messages and versioning

docs/dnsmasq-rendering.md
  generated file rules

docs/testing.md
  how to run all tests

docs/operations.md
  production deployment, backups, restore

docs/release-checklist.md
  release gates, SBOM, scans

docs/threat-model.md
  threats and mitigations

docs/api.md
  API overview or generated OpenAPI link

docs/database.md
  domain model overview
```

Any PR changing behavior must update docs.

---

## 19. Coding standards

### 19.1 General

- Prefer small, reviewable PRs.
- Keep business logic out of views/controllers where possible.
- Add tests before or with implementation.
- Use explicit validation functions.
- Use typed structures/schemas for protocol messages.
- Avoid global mutable state.
- Avoid “magic strings” spread across code; centralize enums/constants.
- Avoid broad exception catches that hide failure.
- Return actionable error messages to UI, but do not leak secrets.

### 19.2 Backend

- Use migrations for schema changes.
- Use service functions for config rendering/deployment state transitions.
- Use serializers/schemas for API input/output.
- Use transaction blocks for multi-row state transitions.
- Use select-for-update or equivalent for deployment/version race conditions where needed.
- Use pagination for large tables.
- Add database constraints for uniqueness where possible, not only application checks.

Important constraints:

```text
unique organization slug
unique site slug within organization
unique subnet CIDR within site unless future VRF model
unique reservation IP within site/subnet
unique reservation MAC within site unless explicitly allowed
unique config version number per site
unique public slug
```

### 19.3 Frontend

- TypeScript strict mode where feasible.
- Do not duplicate critical validation only in frontend; backend is authority.
- Use generated API types if possible.
- Handle loading/error/empty states.
- Keep public view code separate from admin app code where practical.
- Do not expose admin-only data to public route bundles.

### 19.4 Go services

- Use context cancellation correctly.
- Use structured logging.
- Avoid shelling out except in the local helper where explicitly required.
- Validate all external input.
- Use `gofmt`, `go vet`, and tests.
- Use race detector in CI where feasible.
- Keep protocol schemas versioned.

---

## 20. Definition of done

A feature is done only when:

- code implemented;
- tests added;
- docs updated;
- CI passes;
- security implications considered;
- migrations included if needed;
- API schema updated if API changed;
- audit event added if state-changing;
- UI handles error/loading/empty state;
- permissions checked server-side;
- public/private separation preserved;
- no obvious license issue introduced.

A release is done only when:

- all tests pass;
- e2e smoke tests pass;
- SBOM generated;
- dependency scan reviewed;
- license scan reviewed;
- release notes written;
- database migrations tested;
- backup/restore procedure verified;
- Pi agent package install tested;
- rollback tested;
- known limitations documented.

---

## 21. Explicit anti-requirements

Agents must not implement these unless a future human decision explicitly changes the product direction:

- no SSH command execution as the deployment mechanism;
- no inbound open management port on Pi;
- no root network daemon on Pi;
- no arbitrary remote shell;
- no arbitrary raw dnsmasq editor as the main UI;
- no public admin API;
- no unauthenticated write endpoint;
- no Excel import that deploys immediately;
- no storing plaintext enrollment tokens;
- no accepting invalid config and “hoping dnsmasq works”;
- no deleting previous good config before new config is proven;
- no commercial-license UI grid feature without license;
- no large dependency added without license/security check.

---

## 22. MVP success scenario

The MVP should support this real-world scenario:

1. Administrator installs server stack.
2. Administrator creates organization and first site.
3. Administrator imports existing Excel DHCP/IP table.
4. System validates table and shows conflicts.
5. Administrator fixes conflicts.
6. System creates config draft.
7. Administrator reviews dnsmasq diff.
8. Administrator approves config version.
9. Installer flashes Raspberry Pi and installs agent.
10. Installer enrolls Pi with single-use token.
11. Pi connects outbound to server.
12. Admin deploys approved config.
13. Agent downloads signed artifact.
14. Agent validates artifact.
15. Agent applies dnsmasq config.
16. Agent restarts/reloads dnsmasq.
17. Agent reports success.
18. UI shows deployed version and healthy device.
19. Agent reports leases.
20. Admin enables public read-only view with only safe columns.
21. Unauthenticated users can view the professional public DHCP/IP table.
22. Later, if Pi dies, installer replaces Pi, enrolls it, and it receives latest approved config.

---

## 23. Suggested initial issues for GitHub

Create issues roughly in this order:

1. Bootstrap monorepo structure and CI.
2. Add backend Django project with PostgreSQL.
3. Add frontend Next.js shell.
4. Add Go gateway skeleton.
5. Add Go agent skeleton.
6. Implement accounts/organizations/RBAC.
7. Implement site/subnet/pool/reservation models.
8. Implement validation engine.
9. Implement reservation table UI.
10. Implement dnsmasq renderer.
11. Implement config versions.
12. Implement artifact manifest/hash/signing.
13. Implement public read-only snapshots.
14. Implement public page UI.
15. Implement enrollment tokens.
16. Implement device model/status page.
17. Implement gateway heartbeat.
18. Implement agent enrollment.
19. Implement artifact download/verify.
20. Implement apply helper with temp-dir tests.
21. Implement deployment state machine.
22. Implement end-to-end deployment flow.
23. Implement lease reporting.
24. Implement CSV/XLSX import preview.
25. Implement audit log UI.
26. Add observability/metrics.
27. Add SBOM and security scan.
28. Write production deployment docs.
29. Run pilot release checklist.

---

## 24. Agent behavior rules

When working as a coding agent:

- Read this file before planning.
- Identify the milestone/chunk being implemented.
- Keep changes scoped.
- Do not silently change architecture.
- Do not weaken security invariants.
- Add tests in the same PR.
- Run relevant tests before reporting completion.
- Report exact commands run and results.
- Report files changed.
- Report migrations created.
- Report known limitations.
- If a decision is ambiguous, choose the safer/more conservative path and document it.
- If blocked by missing credentials, services, or hardware, implement testable mocks/simulations and document the remaining manual/hardware validation.

---

## 25. Short product positioning

The product is:

> A secure cloud-managed DHCP/IPAM appliance system for small and medium networks, using replaceable Raspberry Pi edge appliances running dnsmasq, controlled by a professional web-based source-of-truth platform with validation, audit, rollback, public read-only table publication, and zero-touch appliance replacement.

It is not:

> A router admin page.

It is:

> Lightweight DDI management with a hardened edge reconciler.

---

## 26. Final reminders

The value of this product is not simply “editing DHCP from the web.”

The value is:

- safe structured editing;
- replacing Excel as source of truth;
- avoiding manual Pi login;
- no inbound customer firewall holes;
- professional UI;
- public read-only view when desired;
- validation before outage;
- auditable history;
- rollback;
- easy Pi replacement;
- security model that survives scrutiny.

Build toward that.
