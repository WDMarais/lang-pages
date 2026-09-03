# Deploy & cold-reproducibility

How this site is provisioned, deployed, and — the point of this doc — how to stand it
up again from nothing on a fresh box. Two machines are involved, and keeping them
separate is what makes the story simple:

- **The server** (`cn.wdmarais.dev`, an EC2 Ubuntu box) is a *dumb static host*. It
  runs nginx and nothing else — **zero Python, no Node, no build step**. It serves the
  committed files in `/var/www/lang-pages` byte-for-byte. A deploy is a `git pull`.
- **The authoring machine** (a developer laptop) runs the build. It turns
  `data/symbols/*.json` + `data/words.json` into the generated pages/graph/audio, which
  are committed *alongside* their source. Because the outputs are in git, the server
  never needs the toolchain that produced them.

This split is the reproducibility lever: the thing that's hard to reproduce (a build
toolchain) never touches production, and the thing in production (static files + nginx)
is trivial to reproduce.

---

## 1. The server — cold repro on a fresh EC2 box

**Prerequisite:** a DNS A record for `cn.wdmarais.dev` pointing at the instance's IP
*before* you run setup (certbot needs it to resolve for the ACME challenge).

Everything else is one script:

```bash
git clone https://github.com/WDMarais/lang-pages.git   # or fetch scripts/ any way
sudo bash lang-pages/scripts/setup.sh
```

`scripts/setup.sh` does, in order:

1. **apt packages** — `nginx certbot python3-certbot-nginx git apache2-utils`.
   (`apache2-utils` is only there for `htpasswd`; see §3. `python3-certbot-nginx` is
   certbot's plugin, not part of the site build.)
2. **clone** the repo into `/var/www/lang-pages`, `chown` to `ubuntu`, world-readable.
3. **nginx** — copy `scripts/nginx.conf` to `sites-available/cn.wdmarais.dev`, symlink
   it enabled, drop the default vhost, `nginx -t`, enable+start.
4. **TLS** — `certbot --nginx` obtains the cert and *rewrites the vhost in place* to add
   the `listen 443 ssl` block. Certbot also installs `certbot.timer`, which renews
   automatically thereafter — no cron of ours, no action needed.

After it finishes, `https://cn.wdmarais.dev/` is live.

### Deploying an update

The server build-step is a pull:

```bash
cd /var/www/lang-pages
git pull --ff-only
bash scripts/apply-repo.sh          # re-copies nginx.conf, re-runs certbot (no-op if valid), reloads
python3 scripts/check-deploy.py     # byte-hash + cache-policy verification
```

`apply-repo.sh` is the lightweight counterpart to `setup.sh`: it assumes apt + clone
already happened and only re-applies config. `check-deploy.py` is the gate — it confirms
the served bytes match the committed bytes and the cache headers are what nginx.conf
declares.

### What is deliberately NOT on the server

No Python build dependencies, no `edge-tts`, no Node. If you find yourself installing
those on the box, something has gone wrong — the generated outputs are committed
precisely so the server never runs the build.

### The one dev page that ships (inert): `tools/preview/`

`tools/preview/` is a **local authoring aid** — a hot-load gallery: drop an `.svg`/`.png`
into `tools/preview/assets/` (gitignored) and it renders live, reloading on change, while
you iterate on an illustration. It works by scraping the dev server's directory listing,
which `python3 -m http.server` autoindexes.

It is committed, so nginx does serve it — but **it's inert in production by construction**:
nginx has no `autoindex`, so the live-discovery request 403s and the page falls back to the
committed exhibit in `tools/preview/showcase/` (the lesson vignettes). So the prod URL is a
small static gallery, runs nothing server-side, and exposes no data — an easter egg, not a
tool. Nothing to exclude from deploy; nothing to lock down.

---

## 2. The authoring machine — the build toolchain

The build itself is **pure Python-3.12 standard library**. Every import under `data/`
and `shared/hanzi-data/` resolves to either the stdlib or a *local* module
(`paths`, `phonetics`, `symbols_io`, …). There is **no third-party Python package in the
build path** — which is why there's no `requirements.txt`, no `pyproject.toml`, and
nothing to `pip install` to run `python3 data/build.py`. That's a feature, not an
omission (see §4).

What the authoring machine *does* need is a handful of **standalone CLI tools**, none of
which the build imports as a library:

| Tool | Role | Needed for | Install |
|------|------|-----------|---------|
| **Python 3.12** | runs the build | everything | system / `uv python install 3.12` |
| **edge-tts** | TTS CLI, invoked as a subprocess by `data/gen-audio.py` | audio banks only — `build.py --no-audio` skips it and the data build is still complete | `uv tool install edge-tts` |
| **ruff** | Python linter | `scripts/hooks/pre-commit` | `uv tool install ruff` |
| **Node + eslint** | JS linter | pre-commit (JS side) | `npm install` (eslint is a devDependency) |
| **uv** | installs the above cleanly | convenience | [astral.sh/uv](https://astral.sh/uv) |
| **playwright** *(optional)* | headless page verification | ad-hoc QA only — lives in a gitignored `.venv/`, not part of the build | `python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium` |

One command wires up the lint side and activates the committed git hooks:

```bash
bash scripts/dev-setup.sh   # npm install + ruff + git config core.hooksPath scripts/hooks
```

`edge-tts` isn't installed by `dev-setup.sh` (audio is a rare, heavy step); install it
with `uv tool install edge-tts` when you need to regenerate the audio banks.

### Pinned versions (captured 2026-08-20)

These are the versions this repo is known-good against. The build is stdlib-only so it
isn't sensitive to them, but they're the reference for the tools:

- Python **3.12.3**
- edge-tts **7.2.8**
- ruff **0.15.22**
- uv **0.11.11**
- eslint **9.39.5**
- Node **24.17.0**

Server-side, nginx and certbot come from Ubuntu apt (whatever the distro ships is fine —
neither has a version this site depends on).

---

## 3. Author-tool auth — the one secret that isn't in git

The `/author/` contributor tool (see `author/index.html`) is gated by nginx Basic Auth.
The credential file is a **secret**: it lives at `/etc/nginx/.htpasswd-author`, *outside*
the web root, and is **never committed**. So it's the one piece `setup.sh` can't carry —
it has to be recreated per box:

```bash
sudo bash scripts/setup-author-auth.sh alice   # add / rotate contributor 'alice'
```

This uses `htpasswd -B` (bcrypt), one credential line per contributor, so nginx's
`$remote_user` — and therefore `/var/log/nginx/author.log` — attributes every request to
a named person. nginx reads the file per-request, so no reload is needed after adding a
contributor. Revoke with `sudo htpasswd -D /etc/nginx/.htpasswd-author alice`.

The tool itself is **export-only**: it emits a JSON blob the contributor emails to the
maintainer. It has no write path to the box, so this gate controls *who reaches the
form*, not what it can do — the maintainer reviews and commits everything by hand.

### Cold-repro checklist for auth

On a fresh box, after `setup.sh`:

1. `sudo bash scripts/setup-author-auth.sh <name>` — once per contributor. The passwords
   are gone with the old box; they're regenerated, not restored.
2. That's it — `nginx.conf` (which carries the `location /author/` block) is already
   applied by `setup.sh`/`apply-repo.sh`.

---

## 4. Why no `pyproject.toml` / `uv.lock`

The question naturally comes up (uv, lockfiles, reproducible envs). The honest answer for
*this* repo: **there's nothing to lock.** A lockfile pins a dependency graph; the build's
dependency graph is empty (stdlib only). Adding a `pyproject.toml` with the standalone
tools listed as deps would misrepresent them — `edge-tts` and `ruff` aren't imported by
the build, they're CLI tools invoked (or not) at the edges. Pinning them by *documented
version* (§2) is the accurate manifest.

If the build ever grows a real third-party runtime dependency, that's the moment to add a
`pyproject.toml` + `uv.lock` and `uv sync` into `dev-setup.sh`. Until then, this document
is the dependency manifest.
