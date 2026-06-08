# Development

This repository is a monorepo scaffold. Keep changes small and respect the component boundaries.

## Layout

- `apps/server`: future Python/Django control plane.
- `apps/web`: future Next.js/React frontend.
- `services/device-gateway`: future Go device gateway.
- `edge/agent`: future unprivileged Go Pi agent.
- `edge/apply-helper`: future privileged local-only Go helper.
- `schemas`: shared JSON Schemas and protocol contracts.
- `docs`: architecture, security, testing, deployment, product scope, and ADRs.

## Local Tooling

The scaffold expects Python 3.11+, Go 1.22+, Bash, and optionally Node.js 20+ for future frontend work.

Use:

```bash
scripts/check.sh
scripts/format.sh
```

## Boundaries

Python code belongs to the server/control plane. Go code belongs to gateway and edge binaries. Frontend code belongs to `apps/web`. Shared protocol and artifact contracts belong to `schemas`.

Do not add product logic to placeholders in this scaffold PR. Future PRs should introduce one product capability at a time with tests.

## Branch and PR Workflow

Work on feature branches from fresh `main`. Do not commit directly to `main`. Each PR should explain scope, security impact, tests run, and follow-up work.

## Small PR Policy

Prefer narrow PRs that can be reviewed independently:

- schema-only changes;
- backend model and validation slices;
- one protocol message family;
- one apply-helper safety check;
- one UI workflow surface;
- one CI/security gate.

Future agents should read `AGENTS.md`, relevant docs, and nearby code before editing.
