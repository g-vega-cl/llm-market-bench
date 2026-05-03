# AGENTS.md

## Commands
- Test engine:   `./apps/engine/venv/bin/python3 -m pytest`
- Lint engine:   `ruff check apps/engine/`
- Build web:     `cd apps/web && pnpm run build`
- Typecheck web: `cd apps/web && pnpm run typecheck`
- Test web:      `cd apps/web && pnpm test`

## Principles
- Code is truth. Docs are hints. When they conflict, trust the code.
- Read the code before acting — don't assume.
- Small, verifiable changes. Test after each.

## Config
- Model names:   `packages/config/models.json`
- Env vars:      `apps/engine/.env.example`
- DB schema:     `supabase/migrations/`
- DB source of truth is the remote Supabase project (applied via `supabase db push --linked`)

## Docs
- Architecture index: `docs/Overview.md`
- Pipeline walkthrough: `docs/engine/data-flow.md`
