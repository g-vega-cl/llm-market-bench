---
tags: [deployment, docker, web, nginx, self-hosted, cloudflare]
category: entity
---

# Self-Hosted Web Deployment

The TanStack Start dashboard in `apps/web` ships two ways: the Netlify build (`apps/web/netlify.toml`) and a self-hosted Docker stack that runs the same SSR server on the primary workstation and the secondary MiniPC edge node. The self-hosted path lets the public site be served from the same machines that host the archive database, the free LLM proxy, and the trading daemons, behind the existing Cloudflare Tunnel.

## Stack

| Piece | Path | Role |
| :--- | :--- | :--- |
| Image | `docker/archive/Dockerfile.web` | Multi-stage build of the SSR server |
| Front door | `docker/archive/nginx.web.conf` | Nginx reverse proxy: health, SSE, PostHog stealth routes, immutable asset caching |
| Primary services | `docker/archive/docker-compose.yml` (`web-app`, `web-proxy`) | Runs on the workstation |
| Edge services | `docker/archive/docker-compose.secondary.yml` (`web-app`, `web-proxy`) | Runs on the MiniPC |
| Deployer | `docker/archive/deploy_web.sh` | Build, sync, restart, and smoke-check both hosts |
| Build-context filter | `.dockerignore` (repo root) | Keeps secrets, docs, and caches out of the image |

## Image (`docker/archive/Dockerfile.web`)

Four stages on `node:24-slim` with `corepack`-activated `pnpm@10.15.0`:

1. **`base`** — sets `PNPM_HOME` / `PATH`, enables corepack, `WORKDIR /app`.
2. **`prod-deps`** — copies the workspace manifests plus the `package.json` files of `apps/web`, `packages/config`, `packages/database`, and `packages/ui-design-system`, then `pnpm install --frozen-lockfile --prod --ignore-scripts --filter web...` so only production dependencies reach the runtime image.
3. **`builder`** — full `pnpm install --frozen-lockfile --filter web...`, copies the four workspace packages and `apps/web`, creates an empty `.git` directory (build tooling that probes for a repository root does not fail inside the image context), bakes the public `VITE_*` build args, and runs `pnpm build:web`. The stage then asserts the stylesheet referenced by the server router chunk actually exists in the client bundle:
   ```sh
   CSS_ASSET="$(grep -oE '/assets/app-[A-Za-z0-9_-]+\.css' apps/web/dist/server/assets/router-*.js | head -n 1)"
   test -n "$CSS_ASSET" && test -f "apps/web/dist/client${CSS_ASSET}"
   ```
   A build that emits a server chunk pointing at a missing CSS asset fails here instead of shipping an unstyled page.
4. **`runtime`** — copies production `node_modules`, `apps/web/dist`, and `apps/web/public`, sets `NODE_ENV=production`, `HOST=0.0.0.0`, `PORT=3000`, exposes `3000`, adds a `HEALTHCHECK` that fetches `http://127.0.0.1:3000/` every 15s (5s timeout, 10s start period, 3 retries), and starts `./node_modules/.bin/srvx --prod -s ../client dist/server/server.js`.

### Build args (public client values)

`VITE_ARCHIVE_DB_URL` (default `https://benchify-archive-db.clvg.uk`), `VITE_ARCHIVE_DB_ANON_KEY`, `VITE_SUPABASE_AUTH_URL`, `VITE_SUPABASE_AUTH_ANON_KEY`, `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN`, `VITE_PUBLIC_POSTHOG_HOST`, and `VITE_TURNSTILE_SITE_KEY` are passed as Docker build args and re-exported as `ENV` before `pnpm build:web`, because Vite inlines `VITE_*` values into the client bundle at build time. Only anon-tier/public values belong here — see [[concepts/env-based-secrets]].

`apps/web/package.json`'s `start` script runs the locally installed `srvx` binary (`srvx --prod -s ../client dist/server/server.js`) instead of `pnpx srvx`, and `srvx` is a direct dependency, so the runtime container never needs a network install at start.

## Compose Services

Both compose files declare the same pair:

- **`web-app`** — built from `Dockerfile.web` with context `../..`; container names `market-bench-web-app` (primary) and `market-bench-web-app-secondary` (MiniPC); `restart: unless-stopped`; `depends_on: archive-proxy`; `env_file: ../../apps/web/.env`; `ARCHIVE_DB_URL=http://archive-proxy:80` so server-side reads go over the Docker network instead of the public tunnel; `expose: 3000`; 512M memory limit.
- **`web-proxy`** — `nginx:alpine`, container names `market-bench-web-proxy` / `market-bench-web-proxy-secondary`, `depends_on: web-app` and `archive-proxy`, publishing `${WEB_BIND_ADDRESS:-0.0.0.0}:3005:80`, and mounting `docker/archive/nginx.web.conf` read-only.

## Nginx Front Door (`docker/archive/nginx.web.conf`)

- **Header buffers** — `proxy_buffer_size 128k`, `proxy_buffers 4 256k`, `proxy_busy_buffers_size 256k`, `large_client_header_buffers 4 32k`, because Supabase SSR auth cookies plus TanStack Start headers exceed Nginx's 4k/8k defaults.
- **`/health`** — returns `200 OK` for Docker and tunnel monitoring.
- **`/api/tape/`** — streams the intraday tape SSE from `archive-proxy:80` with `proxy_buffering off`, `proxy_cache off`, `chunked_transfer_encoding off`, and `proxy_read_timeout 3600s`, resolved dynamically through Docker's embedded DNS (`resolver 127.0.0.11 valid=10s`). See [[entities/live-agent-trader]].
- **PostHog stealth proxy** — `/p/static/` and `/p/array/` rewrite to `us-assets.i.posthog.com`, `/p/` rewrites to `us.i.posthog.com`, each with `proxy_ssl_server_name on` and a pinned `Host` header; `/p/static/` additionally forces `Cache-Control: public, max-age=31536000, immutable` and `X-Content-Type-Options: nosniff`. This mirrors the Netlify redirects.
- **`/assets/`** — proxies to `web-app:3000` and replaces the upstream `Cache-Control` with `public, max-age=31536000, immutable` plus `nosniff`, matching the hashed-chunk policy in `apps/web/netlify.toml` and `apps/web/public/_headers` (see [[concepts/chunk-reload-recovery]]).
- **`/`** — SSR, server functions, and static public files to `web-app:3000` with `proxy_buffering off` and `proxy_read_timeout 120s`.
- **Scheme preservation** — a `map $http_x_forwarded_proto $forwarded_proto` falls back to `$scheme` when the header is absent, so Cloudflare Tunnel's HTTPS scheme survives while plain-HTTP localhost still works.

## Deployer (`docker/archive/deploy_web.sh`)

```sh
./docker/archive/deploy_web.sh [--skip-tests] [--local-only] [--remote-only] [target-host]
```

`target-host` defaults to `cv-minipc@minipc`. The script requires `apps/web/.env` (and sources `docker/archive/.env` when present) with `set -a`, so `VITE_*` build args and compose variables are exported without printing secrets.

1. **[1/4] Local checks** — `pnpm biome check apps/web packages/ui-design-system packages/database`, `pnpm --filter web typecheck`, and `pnpm --filter web test --maxWorkers=2`; skipped with `--skip-tests`.
2. **[2/4] Primary** — `docker compose -f docker-compose.yml up -d --build web-app web-proxy`; skipped with `--remote-only`.
3. **[3/4] Sync** — verifies SSH, creates the remote directory tree, rsyncs the workspace manifests plus `.gitignore` / `.dockerignore`, `Dockerfile.web` / `nginx.web.conf` / `docker-compose.secondary.yml`, `apps/web` (excluding `node_modules`, `dist`, `coverage`, `.netlify`, `.tanstack`, `.scratch`), `packages/config`, `packages/database`, `packages/ui-design-system`, and `docker/archive/.env`; skipped with `--local-only`.
4. **[4/4] Remote** — sources the remote env files, rebuilds and starts `web-app` + `web-proxy`, and prints `docker compose ps`.

**Smoke check** — after each host, `smoke_check` polls `http://localhost:3005/health` up to six times (2s apart), then requires the `/` HTML to contain `Benchify`, to link an `/assets/app-*.css` asset, and for that asset to return 200. A failure prints a warning and returns non-zero, which aborts the run under `set -euo pipefail`.

## Build Context (`.dockerignore`)

The repo-root `.dockerignore` excludes `.git`, `.github`, `.husky`, `.scratch`, the agent directories (`.agents`, `.claude`, `.gemini`, `.hermes`, `.pi`, `.qwen`), caches (`.ruff_cache`, `.pytest_cache`, `.vscode`), `**/node_modules`, `**/.venv`, `**/__pycache__`, `**/.netlify`, `**/.tanstack`, `**/dist`, `**/coverage`, every `**/.env` / `**/.env.*` except `**/.env.example`, `*.db` / `*.sqlite*`, `data/`, `experiments/`, `git-history/`, `knowledge-db/`, `raw/`, `research/`, and `wiki/`. The image therefore never receives local secrets, audit databases, or documentation trees.

## CDN Cache Headers

`apps/web/src/lib/showcase-cache.ts` sets `cloudflare-cdn-cache-control` alongside `netlify-cdn-cache-control` for the pinned `/recipes-demo` showcase (`public, s-maxage=259200`), and deletes both when no pin exists (`cache-control: no-store`) or the response is not cacheable. The self-hosted deployment sits behind Cloudflare Tunnel, so the Cloudflare header is what keeps the showcase edge-cached there while Netlify keeps using its own header.

## Related

- [[entities/web-app]] — the TanStack Start application this stack serves
- [[entities/secondary-minipc-edge]] — the MiniPC edge node that runs the secondary `web-app` / `web-proxy` pair
- [[concepts/hybrid-database-archival]] — the archive stack the web app reads through `archive-proxy`
- [[concepts/env-based-secrets]] — build-time `VITE_*` handling and secret hygiene
- [[concepts/performance-auditing-strategy]] — Lighthouse CI, including the manual `workflow_dispatch` audit
- [[concepts/chunk-reload-recovery]] — immutable hashed-asset caching policy
- [[entities/live-agent-trader]] — the tape SSE stream proxied at `/api/tape/`
