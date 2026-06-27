#!/usr/bin/env bash
# One-time provisioning for a fresh Ubuntu box.
# Run as ubuntu (passwordless sudo assumed, as on EC2 default AMIs).
# Requires DNS A record for cn.wdmarais.dev → this instance's IP before running.
#
# After this runs, two things manage the server automatically:
#   - certbot.timer (systemd): renews TLS certs before expiry — installed by certbot, no action needed
#   - deploy updates: git pull --ff-only && bash scripts/apply-repo.sh

set -euo pipefail

DOMAIN="cn.wdmarais.dev"
REPO_URL="https://github.com/WDMarais/cn-pages.git"
REPO_DIR="/var/www/cn-pages"
EMAIL="marais.wynand@gmail.com"

echo "==> packages"
sudo apt-get update -qq
sudo apt-get install -y nginx certbot python3-certbot-nginx git

echo "==> repo"
if [[ ! -d "$REPO_DIR/.git" ]]; then
    sudo git clone "$REPO_URL" "$REPO_DIR"
fi
sudo chown -R ubuntu:ubuntu "$REPO_DIR"
sudo chmod -R o+rX "$REPO_DIR"

echo "==> nginx"
sudo cp "$REPO_DIR/scripts/nginx.conf" "/etc/nginx/sites-available/$DOMAIN"
sudo ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl enable --now nginx

echo "==> TLS (certbot installs certbot.timer for automatic renewal)"
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL"
sudo systemctl reload nginx

echo ""
echo "done -- https://$DOMAIN/ should be live"
echo "deploy future updates: git pull --ff-only && bash scripts/apply-repo.sh"
