# Deployment: Netlify (benchify)

The app is deployed serverlessly on Netlify.

**Live URL**: [https://benchify.netlify.app](https://benchify.netlify.app)

## Deploy

```bash
cd apps/web
pnpm run build
npx netlify deploy --prod --site 5d3df086-5934-4ea4-9758-36fe189e9af3
```

One-time setup (link project):
```bash
cd apps/web
npx netlify link
# Select the "benchify" project
```

## Configuration

Uses `@netlify/vite-plugin-tanstack-start` in `vite.config.ts`. No `netlify.toml` needed — the plugin auto-configures.

**Environment Variables** (set in Netlify site settings):
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

## Provisioning a new Netlify project

1. Install the plugin: `pnpm add -D @netlify/vite-plugin-tanstack-start`
2. Add to `vite.config.ts`: `import netlify from '@netlify/vite-plugin-tanstack-start'` + `netlify()` in plugins array
3. Deploy with `npx netlify deploy`

For other hosting platforms, see [TanStack Start Hosting Docs](https://tanstack.com/start/latest/docs/framework/react/hosting).
