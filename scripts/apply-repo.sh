#!/usr/bin/env bash
# Apply current repo state to a provisioned lang-pages box.
# Lightweight counterpart to setup.sh — skips apt/git-clone, assumes those ran once.
#
#   git pull --ff-only && bash scripts/apply-repo.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="cn.wdmarais.dev"
EMAIL="marais.wynand@gmail.com"

echo "==> nginx config"
sudo cp "$REPO_ROOT/scripts/nginx.conf" "/etc/nginx/sites-available/$DOMAIN"
sudo ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
sudo rm -f /etc/nginx/sites-enabled/default

echo "==> TLS (certbot re-applies to current config; no-op if cert still valid)"
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL"

echo "==> permissions"
sudo chmod -R o+rX "$REPO_ROOT"

echo "==> reload nginx"
sudo systemctl reload nginx

echo ""
echo "done -- verify: curl -sI https://$DOMAIN/"
