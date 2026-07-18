#!/usr/bin/env bash
# Developer-machine setup — installs the lint toolchain and activates the
# committed git hooks. This is NOT the server: production provisioning lives in
# scripts/setup.sh (nginx/certbot). Nothing here runs on the VPS.
#
# Run once after cloning:  bash scripts/dev-setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> ESLint (npm devDependencies)"
npm install

echo "==> ruff"
if command -v ruff >/dev/null 2>&1; then
  echo "    ruff already on PATH — skipping"
elif command -v uv >/dev/null 2>&1; then
  uv tool install ruff
elif command -v pipx >/dev/null 2>&1; then
  pipx install ruff
else
  pip install --user ruff
fi

echo "==> git hooks"
git config core.hooksPath scripts/hooks

echo ""
echo "done — pre-commit lint active:"
echo "  JS:     eslint (braces-always)   ·  npm run lint / lint:fix"
echo "  Python: ruff check               ·  ruff check --fix ."
