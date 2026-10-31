import netlify from '@netlify/vite-plugin-tanstack-start';
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
            },
        },
        resolve: {
            alias: {
                'react-dom/client': 'react-dom/profiling',
            },
        },
        plugins: [
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
