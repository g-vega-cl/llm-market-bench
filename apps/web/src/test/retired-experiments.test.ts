import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Retired experiment guard.
 *
 * `homepage-bg-experiment` (PostHog experiment 376759) shipped four WebGL
 * backgrounds on the homepage, then lost its reader on 2026-06-13 when
 * `GlobalBackground` replaced per-page backdrops. The PostHog record stayed
 * "running" with two lifetime exposures while `ShaderBackground.tsx` rotted as
 * an orphan. Deleting the code is therefore half the cleanup: this test keeps
 * the flag name and the component from creeping back without an owner.
 */

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_SRC = join(TEST_DIR, '..');

const RETIRED_FLAGS = ['homepage-bg-experiment'];
const RETIRED_SYMBOLS = ['ShaderBackground'];

function sourceFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((entry) => {
        const path = join(dir, entry);
        if (statSync(path).isDirectory()) return sourceFiles(path);
        return /\.(?:ts|tsx)$/.test(entry) ? [path] : [];
    });
}

describe('retired homepage background experiment', () => {
    it('has no flag reads and no ShaderBackground source left in src', () => {
        const self = fileURLToPath(import.meta.url);
        const files = sourceFiles(WEB_SRC).filter((file) => file !== self);
        const retired = [...RETIRED_FLAGS, ...RETIRED_SYMBOLS];
        const offenders = files.flatMap((file) => {
            const source = readFileSync(file, 'utf8');
            return retired
                .filter((token) => source.includes(token))
                .map((token) => `${relative(WEB_SRC, file)} -> ${token}`);
        });

        expect(
            offenders,
            'Homepage backdrop is GlobalBackground; the A/B experiment is retired.',
        ).toEqual([]);
        expect(existsSync(join(WEB_SRC, 'components', 'ui', 'ShaderBackground.tsx'))).toBe(false);
    });
});
