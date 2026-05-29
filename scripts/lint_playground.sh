#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAYGROUND_APP="$ROOT/docs/assets/playground/app.py"
FIX=0

if [[ "${1:-}" == "--fix" ]]; then
  FIX=1
  shift
fi

if (($# != 0)); then
  echo "usage: scripts/lint_playground.sh [--fix]" >&2
  exit 2
fi

python "$ROOT/scripts/build_playground_assets.py"

# Keep this wrapper instead of calling t-linter directly from tox.
# t-linter has hung under tox in this repository, while running it
# through a plain shell script has been stable.
t-linter check --error-on-issues "$PLAYGROUND_APP"

if ((FIX)); then
  t-linter format "$PLAYGROUND_APP"
else
  t-linter format --check "$PLAYGROUND_APP"
fi
