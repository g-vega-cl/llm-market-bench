# PostHog Error Tracking

> ⚠️ **Needs your attention**
> - Replace `POSTHOG_API_KEY` with a valid `phx_` personal API key with Error Tracking write access; the configured value was rejected by the uploader.
> - In Netlify production environment variables, add `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`, and `POSTHOG_HOST` for the build.
> - In Netlify build/runtime environment variables, confirm `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN` and `VITE_PUBLIC_POSTHOG_HOST` are present, then trigger a new production deploy.

## What you still need to do

1. Create a personal API key at https://us.posthog.com/source-maps-key, using the **Source map upload** preset. It needs Error Tracking write access.
2. In the Netlify site settings, add the key as the `POSTHOG_API_KEY` secret. Also add `POSTHOG_PROJECT_ID` with value `359142` and `POSTHOG_HOST` with the configured PostHog host. Confirm `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN` and `VITE_PUBLIC_POSTHOG_HOST` are configured for the production build and deployed runtime.
3. Trigger a new Netlify production deploy. The production path runs `pnpm build:web`; once the upload variables are present, that build uploads its source maps to PostHog.

## What is wired now

Uncaught server exceptions and unhandled promise rejections are captured by the server-side `posthog-node` client with exception autocapture enabled. The server client is initialized by `src/start.ts`. Browser-caught render errors are sent through the existing root error boundary in `src/routes/__root.tsx` and `src/components/ui/DefaultCatchBoundary.tsx`; browser initialization already has exception capture enabled. No duplicate global error listeners were added.

The PostHog SDK/runtime setup is in place, and the Vite Rollup integration is configured for Error Tracking source maps. The relevant source-map build files are `package.json` and `vite.config.ts`; the Netlify production configuration is documented in `netlify.toml`. Upload uses `POSTHOG_API_KEY`, `POSTHOG_PROJECT_ID`, and `POSTHOG_HOST`, while runtime initialization uses `VITE_PUBLIC_POSTHOG_PROJECT_TOKEN` and `VITE_PUBLIC_POSTHOG_HOST`.

Production builds use hidden source maps and are configured to upload them and delete local maps after a successful upload. The exact local verification command was `pnpm build`; the deploy build is `pnpm build:web`. `pnpm build` passed, including the client build, SSR build, and `tsc --noEmit`. Upload was skipped because the configured personal key was malformed: no release was created and 0 files were uploaded. Once the valid CI credential is present, every Netlify production build using `pnpm build:web` is set up to upload.

Release linking was not wired in this run. No release ID is currently resolved or passed to the app, so there is no deploy-specific release follow-up to verify. Local runs, tests, and pull-request builds remain unchanged.

## How to verify

Trigger an error and inspect https://us.posthog.com/project/359142/error_tracking. Uploaded symbol sets appear at https://us.posthog.com/project/359142/error_tracking/configuration. After the next production deploy with valid upload credentials, confirm the new symbol set appears there and that captured stack traces are readable.
