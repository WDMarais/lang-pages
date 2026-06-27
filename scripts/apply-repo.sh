#!/usr/bin/env bash
# Apply current repo state to a provisioned cn-pages box.
# Lightweight counterpart to setup.sh — skips apt/certbot, assumes those ran once.
#
#   git pull --ff-only && bash scripts/apply-repo.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="cn.wdmarais.dev"

echo "==> nginx config"
sudo cp "$REPO_ROOT/scripts/nginx.conf" "/etc/nginx/sites-available/$DOMAIN"
sudo ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
sudo rm -f /etc/nginx/sites-enabled/default

echo "==> permissions"
sudo chmod -R o+rX "$REPO_ROOT"

sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "done -- verify: curl -sI https://$DOMAIN/"
