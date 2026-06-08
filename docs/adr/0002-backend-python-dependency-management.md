# ADR 0002: Backend Python Dependency Management

## Status

Accepted.

## Context

This repository is a monorepo with Python, Go, and future Node components. A root `requirements.txt` would make the repository look like a single Python application and would blur component ownership. Backend dependency changes also need reproducible installs for CI and future agent work.

## Decision

- `apps/server/pyproject.toml` is the human-maintained backend dependency manifest.
- `apps/server/uv.lock` is the committed reproducible backend lockfile.
- CI installs backend dependencies with `uv sync --extra dev --locked`.
- Future backend dependency changes must update both `pyproject.toml` and `uv.lock`.
- There is no root `requirements.txt`.

## Consequences

Backend installs are reproducible and scoped to the backend component. Future agents need `uv` available for locked installs and must not leave ad hoc `pip install` changes undocumented. Frontend dependencies belong in `apps/web/package.json` and a future frontend lockfile. Go dependencies belong in each component's `go.mod` and `go.sum`.
