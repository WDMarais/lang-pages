#!/usr/bin/env bash
# Verify the live site serves exactly what the given git ref contains.
#
# nginx serves /var/www/lang-pages — a plain git clone — so a deploy is just a
# pull. When that pull is skipped, drift is not always loud: a file added since
# the last pull 404s, but a file *modified* since then still returns 200 with
# stale bytes. The silent case is the one this catches.
#
# Compares content hashes, not sizes: the CN clips collide on size often enough
# that a size check is no check at all (heng2/na4 are both 10656 bytes).
#
#   bash scripts/check-deploy.sh                        # audio banks + page data
#   bash scripts/check-deploy.sh 'audio/cn/*.mp3'       # any git pathspec
#   HOST=localhost:8765 bash scripts/check-deploy.sh    # point at the dev server
#
# Exits non-zero if anything drifted, so it can gate a deploy.

set -euo pipefail

HOST="${HOST:-cn.wdmarais.dev}"
REF="${REF:-origin/main}"
JOBS="${JOBS:-24}"

# Default: the assets a stale clone actually breaks — the content-keyed audio
# banks and the generated card/page JSON. Override by passing patterns.
# These are matched as bash globs against the ref's paths (so `*` spans `/`),
# not as git pathspecs — git ls-tree does not glob.
if [ "$#" -gt 0 ]; then
  PATTERNS=("$@")
else
  PATTERNS=('audio/*.mp3' '*.json')
fi

case "$HOST" in
  localhost*|127.0.0.1*) SCHEME=http ;;
  *)                     SCHEME=https ;;
esac

cd "$(cd "$(dirname "$0")/.." && pwd)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# Expected blob hash per tracked path, straight out of the ref's tree.
# core.quotePath=false is load-bearing: git otherwise renders non-ASCII paths
# as C-quoted octal ("data/symbols/\345\207\272.json"), which no bash glob below
# matches — silently dropping every CJK-named file (symbols, hanzi-data: >500 of
# them, over half the tree). That is the exact silent-coverage gap this verifier
# exists to prevent, so it must not have one itself.
git -c core.quotePath=false ls-tree -r --format='%(objectname) %(path)' "$REF" |
  while read -r hash path; do
    for p in "${PATTERNS[@]}"; do
      # shellcheck disable=SC2053
      if [[ $path == $p ]]; then echo "$hash $path"; break; fi
    done
  done > "$WORK/expected"

total=$(wc -l < "$WORK/expected")
if [ "$total" -eq 0 ]; then
  echo "no tracked files match: ${PATTERNS[*]}" >&2
  exit 2
fi

echo "==> checking $total files on $HOST against $REF"

probe() {
  want="${1%% *}"
  path="${1#* }"
  body="$(mktemp)"
  code=$(curl -sS -m 30 -o "$body" -w '%{http_code}' "$SCHEME://$HOST/$path" || echo 000)
  if [ "$code" != "200" ]; then
    echo "MISSING  $path  (HTTP $code)"
  elif [ "$(git hash-object "$body")" != "$want" ]; then
    echo "STALE    $path  (200, but content differs from $REF)"
  fi
  rm -f "$body"
}
export -f probe
export SCHEME HOST REF

# shellcheck disable=SC2016
xargs -a "$WORK/expected" -P "$JOBS" -d '\n' -I{} bash -c 'probe "$@"' _ {} > "$WORK/drift"

drifted=$(wc -l < "$WORK/drift")
if [ "$drifted" -eq 0 ]; then
  echo "==> ok: all $total files match $REF"
  exit 0
fi

sort "$WORK/drift"
echo ""
echo "==> $drifted of $total files drifted -- the box needs:"
echo "    cd /var/www/lang-pages && git pull --ff-only"
exit 1
