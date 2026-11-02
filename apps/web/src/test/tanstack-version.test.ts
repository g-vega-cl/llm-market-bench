import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('TanStack Dependencies Version Sanity (TDD)', () => {
    it('requires @tanstack packages in apps/web to be updated to target release lines', () => {
        const pkgPath = resolve(__dirname, '../../package.json');
        const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'));

        const deps = pkg.dependencies || {};

        // Parse versions removing leading ^ or ~
        const cleanVersion = (v: string | undefined) => (v ? v.replace(/^[\^~]/, '') : '0.0.0');

        const queryVer = cleanVersion(deps['@tanstack/react-query']);
        const routerVer = cleanVersion(deps['@tanstack/react-router']);
        const startVer = cleanVersion(deps['@tanstack/react-start']);

        const parseParts = (v: string) => v.split('.').map((p) => Number.parseInt(p, 10));

        const isAtLeast = (v: string, min: [number, number, number]) => {
            const [maj, minr, pat] = parseParts(v);
            if (maj !== min[0]) return maj > min[0];
            if (minr !== min[1]) return minr > min[1];
            return pat >= min[2];
        };

        // Query must be at least 5.105.0
        expect(
            isAtLeast(queryVer, [5, 105, 0]),
            `@tanstack/react-query version ${queryVer} must be >= 5.105.0`,
        ).toBe(true);

        // Router must be at least 1.170.0
        expect(
            isAtLeast(routerVer, [1, 170, 0]),
            `@tanstack/react-router version ${routerVer} must be >= 1.170.0`,
        ).toBe(true);

        // Start must be at least 1.168.61
        expect(
            isAtLeast(startVer, [1, 168, 61]),
            `@tanstack/react-start version ${startVer} must be >= 1.168.61`,
        ).toBe(true);
    });
});
