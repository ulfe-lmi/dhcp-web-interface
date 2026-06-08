#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

find_python() {
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi

  return 1
}

run_python_tests() {
  local python_bin

  if ! python_bin="$(find_python)"; then
    echo "python not found; skipping Python tests and JSON validation"
    return 0
  fi

  echo "Validating JSON schema syntax"
  "$python_bin" -m json.tool "$ROOT_DIR/schemas/config-artifact.schema.json" >/dev/null

  if "$python_bin" -m pytest --version >/dev/null 2>&1; then
    echo "Running Python tests"
    (cd "$ROOT_DIR/apps/server" && "$python_bin" -m pytest)
    return 0
  fi

  if "$python_bin" -m pip --version >/dev/null 2>&1 && "$python_bin" -m pip install --quiet --user pytest; then
    echo "Running Python tests with user-installed pytest"
    (cd "$ROOT_DIR/apps/server" && "$python_bin" -m pytest)
    return 0
  fi

  echo "pytest is not available and could not be installed; skipping Python tests"
}

run_go_tests() {
  if ! command -v go >/dev/null 2>&1; then
    echo "go not found; skipping Go tests"
    return 0
  fi

  for module in \
    "$ROOT_DIR/services/device-gateway" \
    "$ROOT_DIR/edge/agent" \
    "$ROOT_DIR/edge/apply-helper"; do
    echo "Running Go tests in ${module#$ROOT_DIR/}"
    (cd "$module" && go test ./...)
  done
}

run_node_checks() {
  local package_json="$ROOT_DIR/apps/web/package.json"

  if [[ ! -f "$package_json" ]]; then
    return 0
  fi

  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found; skipping frontend checks"
    return 0
  fi

  if node -e "const p=require('$package_json'); process.exit(p.scripts && p.scripts.test ? 0 : 1)" >/dev/null 2>&1; then
    echo "Running frontend test script"
    (cd "$ROOT_DIR/apps/web" && npm test)
  else
    echo "No frontend test script configured; skipping frontend checks"
  fi
}

run_python_tests
run_go_tests
run_node_checks

echo "All available scaffold checks completed"
