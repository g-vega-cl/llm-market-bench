import netlify from '@netlify/vite-plugin-tanstack-start';
import posthog from '@posthog/rollup-plugin';
import tailwindcss from '@tailwindcss/vite';
import { tanstackStart } from '@tanstack/react-start/plugin/vite';
import viteReact from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import tsConfigPaths from 'vite-tsconfig-paths';

export default defineConfig(({ mode }) => {
    // Populate process.env for Node.js SSR / TanStack Start server functions.
    // Non-VITE_ variables remain strictly server-side and are NEVER exposed to client bundles.
    const env = loadEnv(mode, process.cwd(), '');
    for (const [key, val] of Object.entries(env)) {
        if (process.env[key] === undefined) {
            process.env[key] = val;
        }
    }

    const posthogApiKey = process.env.POSTHOG_API_KEY;
    const posthogProjectId = process.env.POSTHOG_PROJECT_ID;
    const posthogUploadEnabled = Boolean(posthogApiKey?.startsWith('phx_') && posthogProjectId);

    if (posthogApiKey && !posthogApiKey.startsWith('phx_')) {
        console.warn(
            'PostHog source map upload skipped: POSTHOG_API_KEY must be a personal API key.',
        );
    }

    return {
        server: {
            port: 3005,
            proxy: {
                '/p/static': {
                    target: 'https://us-assets.i.posthog.com',
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/p\/static/, '/static'),
                    secure: false,
                },
                '/p/array': {
                    target: 'https://us-assets.i.posthog.com',
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/p\/array/, '/array'),
                    secure: false,
                },
                '/p': {
                    target: 'https://us.i.posthog.com',
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/p/, ''),
                    secure: false,
                },
                '/api/tape': {
                    target:
                        env.VITE_ARCHIVE_DB_URL ||
                        process.env.ARCHIVE_DB_URL ||
                        'https://benchify-archive-db.clvg.uk',
                    changeOrigin: true,
                    secure: false,
                },
            },
        },
        resolve: {
            alias: {
                'react-dom/client': 'react-dom/profiling',
            },
        },
        build: {
            sourcemap: 'hidden' as const,
            rollupOptions: {
                output: {
                    manualChunks(id) {
                        if (id.includes('node_modules/d3') || id.includes('node_modules/d3-')) {
                            return 'vendor-d3';
                        }
                    },
                },
            },
        },
        plugins: [
            posthog({
                personalApiKey: posthogApiKey ?? '',
                projectId: posthogProjectId,
                host: process.env.POSTHOG_HOST,
                sourcemaps: {
                    enabled: posthogUploadEnabled,
                    deleteAfterUpload: true,
                },
            }),
            tailwindcss(),
            tsConfigPaths({
                projects: ['./tsconfig.json'],
            }),
            tanstackStart(),
            netlify(),
            viteReact(),
        ],
    };
});
