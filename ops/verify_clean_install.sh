#!/usr/bin/env bash
# Clean-environment dependency verification (round-6 item 17).
#
# Creates a throwaway venv, installs backend/requirements.txt from scratch,
# runs `pip check` for conflicts, and verifies the backend app imports.
# Same steps as the `dependency-check` job in .github/workflows/ci-cd.yml.
#
# Usage: ops/verify_clean_install.sh [--keep-venv]
#   --keep-venv  leave $HOME/.tmp/ai-test-cleanvenv in place for inspection
# Exit non-zero if install, pip check, or the import check fails.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# NOTE: NOT /tmp — on this VM /tmp is a 512M tmpfs and the full install
# (pandas/scipy/scikit-learn/matplotlib/...) needs ~1GB. $HOME/.tmp lives
# on the main disk. CI runners have a roomy /tmp, so the workflow job
# keeps /tmp/cleanvenv.
VENV="$HOME/.tmp/ai-test-cleanvenv"
KEEP=false
[[ "${1:-}" == "--keep-venv" ]] && KEEP=true

echo "== clean venv: $VENV"
rm -rf "$VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip

echo "== pip install -r backend/requirements.txt"
"$VENV/bin/pip" install -r "$REPO_ROOT/backend/requirements.txt"

echo "== pip check"
"$VENV/bin/pip" check

echo "== import check: backend app boots to import"
cd "$REPO_ROOT/backend"
DATABASE_URL='mysql+asyncmy://test_user:test_password@localhost:3306/test_db' \
REDIS_URL='redis://localhost:6379/15' \
SECRET_KEY='test-secret-key-for-ci' \
"$VENV/bin/python" -c "from src.main import app; print('app imports OK:', type(app).__name__)"

echo "== clean install verification PASSED"
if [[ "$KEEP" == false ]]; then
  rm -rf "$VENV"
  echo "(throwaway venv removed)"
fi
