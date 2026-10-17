import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('Vite production profiling configuration', () => {
    it('aliases react-dom/client to react-dom/profiling in vite.config.ts', () => {
        const configPath = join(__dirname, '../../vite.config.ts');
        const content = readFileSync(configPath, 'utf8');

        // Verify resolve.alias is configured for react-dom/client -> react-dom/profiling
        expect(content).toMatch(/['"]react-dom\/client['"]\s*:\s*['"]react-dom\/profiling['"]/);
    });
});
