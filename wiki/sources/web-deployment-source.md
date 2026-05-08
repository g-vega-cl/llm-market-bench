---
tags: [source, web, deployment, netlify]
category: source
source: docs/web/tanstack-start-deploy-official.md
---

# Source: Web Deployment (Netlify)

Serverless deployment on Netlify for the TanStack Start app.

Key details:

- **Live URL**: https://benchify.netlify.app
- **Deploy**: `pnpm run build` then `npx netlify deploy --prod`
- **Plugin**: `@netlify/vite-plugin-tanstack-start` auto-configures — no `netlify.toml` needed
- **Env vars**: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (set in Netlify site settings)
