import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import { defineConfig } from 'vitest/config';

export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./src/test/setup.ts'],
        include: ['src/**/*.{test,spec}.{ts,tsx}'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            thresholds: {
                statements: 40,
                branches: 40,
                functions: 40,
                lines: 40,
            },
            exclude: [
                'node_modules/**',
                'dist/**',
                '**/*.d.ts',
                '**/*.test.{ts,tsx}',
                'src/test/**',
            ],
        },
    },
});
