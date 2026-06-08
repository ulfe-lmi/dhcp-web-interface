#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  cat <<'EOF'
uv is required for reproducible backend dependency installs.

Install uv with one of:
  curl -LsSf https://astral.sh/uv/install.sh | sh
  python -m pip install uv
  pipx install uv
EOF
  exit 1
fi

cd "$ROOT_DIR/apps/server"
uv sync --extra dev --locked
