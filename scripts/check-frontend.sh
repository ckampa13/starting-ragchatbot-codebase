#!/usr/bin/env bash
# Frontend quality check script
# Runs Prettier in check mode to verify formatting without modifying files.
# Exit code is non-zero if any file would be reformatted.
#
# Usage:
#   ./scripts/check-frontend.sh          # check only
#   ./scripts/check-frontend.sh --fix    # auto-format files

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v npx &>/dev/null; then
  echo "Error: npx not found. Install Node.js to run Prettier." >&2
  exit 1
fi

cd "$ROOT"

if [[ "${1:-}" == "--fix" ]]; then
  echo "Formatting frontend files..."
  npx prettier --write "frontend/**/*.{js,css,html}"
  echo "Done."
else
  echo "Checking frontend formatting..."
  npx prettier --check "frontend/**/*.{js,css,html}"
  echo "All files are correctly formatted."
fi
