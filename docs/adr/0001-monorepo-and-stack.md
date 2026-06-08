# ADR 0001: Monorepo and Baseline Stack

## Status

Accepted for scaffold.

## Context

The product spans a server control plane, web UI, device gateway, Raspberry Pi agent, privileged local helper, shared schemas, and product documentation. Early development needs strong shared contracts and small reviewable changes.

## Decision

Use a monorepo with separate top-level component boundaries:

- `apps/server` for Python/Django control plane code.
- `apps/web` for Next.js/React frontend code.
- `services/device-gateway` for the Go server-side gateway.
- `edge/agent` for the unprivileged Go Pi agent.
- `edge/apply-helper` for the privileged local-only Go helper.
- `schemas` for shared artifact and protocol contracts.
- `docs` for architecture, security, development, testing, deployment, and product planning.

The intended stack is Python, Django, Django REST Framework, PostgreSQL, Celery, Valkey, Go, Next.js/React, TypeScript, Tailwind CSS, shadcn/ui or equivalent components, AG Grid Community, `dnsmasq`, and `systemd`.

## Consequences

Shared schemas and docs live close to all implementations, making cross-component contracts easier to review. CI can grow incrementally by component. The repository needs clear ownership boundaries to avoid oversized PRs.

Dependencies are scoped to the component that owns them. Backend Python dependencies live under `apps/server`, frontend dependencies belong under `apps/web`, and Go dependencies belong to the relevant Go module. A root Python requirements file would be misleading for this monorepo.

The scaffold intentionally avoids installing Next.js or unrelated product dependencies before their first implementation PRs.

## Alternatives Considered

- Multiple repositories: rejected for the initial phase because protocol and schema contracts are still changing quickly.
- Full Django and Next.js bootstrap in the first PR: rejected because it would add too much generated structure before domain boundaries are reviewed.
- Single-language implementation: rejected because Go is a better fit for small static gateway and edge binaries, while Python/Django is a pragmatic fit for the control plane.
