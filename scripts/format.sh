#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v go >/dev/null 2>&1; then
  for module in \
    "$ROOT_DIR/services/device-gateway" \
    "$ROOT_DIR/edge/agent" \
    "$ROOT_DIR/edge/apply-helper"; do
    echo "Formatting Go module ${module#$ROOT_DIR/}"
    (cd "$module" && gofmt -w ./cmd)
  done
else
  echo "go not found; skipping Go formatting"
fi

echo "No Python formatter configured yet; skipping Python formatting"

if command -v npm >/dev/null 2>&1 && [[ -f "$ROOT_DIR/apps/web/package.json" ]]; then
  if node -e "const p=require('$ROOT_DIR/apps/web/package.json'); process.exit(p.scripts && p.scripts.format ? 0 : 1)" >/dev/null 2>&1; then
    echo "Running frontend format script"
    (cd "$ROOT_DIR/apps/web" && npm run format)
  else
    echo "No frontend format script configured; skipping frontend formatting"
  fi
else
  echo "npm not found or frontend package missing; skipping frontend formatting"
fi
