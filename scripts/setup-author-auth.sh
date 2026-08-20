#!/usr/bin/env bash
# Provision a login for the /author/ contributor tool. Run once per contributor,
# and again to rotate a password. Must run as root (writes under /etc/nginx).
#
#   sudo bash scripts/setup-author-auth.sh alice     # add / update contributor 'alice'
#   sudo bash scripts/setup-author-auth.sh           # prompt for the username
#
# The credential file is a SECRET: it lives OUTSIDE the web root and is never
# committed. Recreating it on a fresh box is the cold-repro step for author auth
# (the rest of the box is reproduced by setup.sh; this holds passwords, so it can't
# live in git). Each contributor gets their OWN line, so nginx's $remote_user — and
# thus /var/log/nginx/author.log — attributes every request to a named person.
#
#   revoke a contributor:   sudo htpasswd -D /etc/nginx/.htpasswd-author <name>
#   list contributors:      cut -d: -f1 /etc/nginx/.htpasswd-author
set -euo pipefail

FILE=/etc/nginx/.htpasswd-author
USER_NAME="${1:-}"

if ! command -v htpasswd >/dev/null 2>&1; then
    echo "htpasswd not found — install it:  sudo apt-get install -y apache2-utils" >&2
    exit 1
fi
if [[ -z "$USER_NAME" ]]; then
    read -rp "contributor username: " USER_NAME
fi
if [[ -z "$USER_NAME" ]]; then
    echo "no username given" >&2; exit 1
fi

# -c (create) ONLY when the file does not yet exist — using it later would wipe every
# existing contributor. bcrypt (-B) so the stored hash isn't the weak default.
if [[ -f "$FILE" ]]; then
    htpasswd -B "$FILE" "$USER_NAME"
else
    htpasswd -B -c "$FILE" "$USER_NAME"
fi

echo ""
echo "done — '$USER_NAME' can now reach https://cn.wdmarais.dev/author/"
echo "(no nginx reload needed: auth_basic_user_file is read per request)"
echo "contributors now provisioned:"
cut -d: -f1 "$FILE" | sed 's/^/  /'
