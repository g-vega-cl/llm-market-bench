import netlify from '@netlify/vite-plugin-tanstack-start';
import tailwindcss from '@tailwindcss/vite';
import { tanstackStart } from '@tanstack/react-start/plugin/vite';
import viteReact from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import tsConfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
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
    plugins: [
        tailwindcss(),
        tsConfigPaths({
            projects: ['./tsconfig.json'],
        }),
        tanstackStart(),
        netlify(),
        viteReact(),
    ],
});
