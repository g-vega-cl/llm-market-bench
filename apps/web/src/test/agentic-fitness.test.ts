import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const WEB_SRC = join(TEST_DIR, '..');
const REPO_ROOT = join(TEST_DIR, '..', '..', '..', '..');

const SKIP_DIRS = new Set([
    'node_modules',
    'dist',
    'coverage',
    'build',
    '.scratch',
    '.git',
    '.netlify',
]);
const IGNORED_GENERATED_FILES = new Set(['apps/web/src/routeTree.gen.ts']);

// Ratchet caps on preexisting >800 LOC legacy web files so none grow and zero new >800 LOC files land.
const LEGACY_WEB_LOC_CAPS: Record<string, number> = {
    'apps/web/src/features/daily-predictions/pages/DailyPredictionsPage.test.tsx': 1075,
    'apps/web/src/features/memories/components/MemoryCard.tsx': 1060,
    'apps/web/src/features/home/backdrop/garden-renderer.ts': 925,
};

const SKIP_OR_ONLY_RE = /\b(?:it|test|describe)\.(?:skip|only)\s*\(/;
const FORBIDDEN_ENGINE_IMPORT_RE = /(?:from\s+|import\s*\()\s*['"][^'"]*apps\/engine[^'"]*['"]/;

function walk(dir: string): string[] {
    const out: string[] = [];
    for (const entry of readdirSync(dir)) {
        if (SKIP_DIRS.has(entry)) continue;
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) {
            out.push(...walk(full));
        } else if (/\.(?:ts|tsx)$/.test(entry)) {
            out.push(full);
        }
    }
    return out;
}

describe('Agentic Web Architecture Fitness', () => {
    const allTsFiles = walk(WEB_SRC);

    it('forbids .skip and .only on Vitest suites and tests', () => {
        const violations: string[] = [];
        for (const file of allTsFiles) {
            const rel = relative(REPO_ROOT, file);
            if (rel === 'apps/web/src/test/agentic-fitness.test.ts') continue;
            const src = readFileSync(file, 'utf8');
            if (SKIP_OR_ONLY_RE.test(src)) {
                violations.push(
                    `${rel} contains .skip or .only on a test/suite. ` +
                        'REMEDIATION: Fix failing tests and never commit focused .only or skipped tests.',
                );
            }
        }
        expect(violations).toEqual([]);
    });

    it('forbids static or dynamic imports from apps/engine inside apps/web', () => {
        const violations: string[] = [];
        for (const file of allTsFiles) {
            const rel = relative(REPO_ROOT, file);
            if (rel === 'apps/web/src/test/agentic-fitness.test.ts') continue;
            const src = readFileSync(file, 'utf8');
            if (FORBIDDEN_ENGINE_IMPORT_RE.test(src)) {
                violations.push(
                    `${rel} imports from apps/engine. ` +
                        'REMEDIATION: Share schemas/constants via packages/config or packages/database, never across apps/engine.',
                );
            }
        }
        expect(violations).toEqual([]);
    });

    it('enforces the 800 LOC hard ceiling across apps/web/src', () => {
        const violations: string[] = [];
        for (const file of allTsFiles) {
            const rel = relative(REPO_ROOT, file);
            if (IGNORED_GENERATED_FILES.has(rel)) continue;
            const lineCount = readFileSync(file, 'utf8').split('\n').length;
            const cap = LEGACY_WEB_LOC_CAPS[rel] ?? 800;
            if (lineCount > cap) {
                violations.push(
                    `${rel} is ${lineCount} LOC (ceiling: ${cap}). ` +
                        'REMEDIATION: Decompose into vertical-slice subcomponents or pure view-model helpers.',
                );
            }
        }
        expect(violations).toEqual([]);
    });
});
