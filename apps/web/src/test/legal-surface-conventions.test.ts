import type { Stats } from 'node:fs';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { privacyPolicy } from '~/features/legal/legal-content';

/**
 * Legal-surface conventions.
 *
 * Three defects shipped in the launch-legal batch and were caught only by a
 * cold read, so each one gets a guard here:
 *
 * 1. `/footer` used `md:flex-row md:justify-between` — `.agents/rules/design-spec.md`
 *    §1 bans viewport prefixes outright.
 * 2. The footer notice said inputs were masked while `maskTextSelector` matched
 *    no element, and the policy implied on-screen text was safe.
 * 3. The privacy policy listed every processor except the language-model
 *    providers that receive the text users actually type.
 *
 * The copy assertions are deliberately narrow: they pin the facts that were
 * wrong, not the prose around them.
 */

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const WEB = join(TEST_DIR, '..', '..');

const LEGAL_FILES = [
    join(WEB, 'src', 'features', 'legal'),
    join(WEB, 'src', 'routes', 'privacy.tsx'),
    join(WEB, 'src', 'routes', 'terms.tsx'),
    join(WEB, 'src', 'routes', 'disclaimer.tsx'),
];

const VIEWPORT_PREFIX = /(^|\s)(sm|md|lg|xl|2xl):[\w-]/;
const RAW_BUTTON = /<button[\s>]/;

function walk(path: string): string[] {
    let stat: Stats;
    try {
        stat = statSync(path);
    } catch {
        return [];
    }
    if (!stat.isDirectory()) return [path];
    return readdirSync(path).flatMap((entry) => {
        const full = join(path, entry);
        return statSync(full).isDirectory() ? walk(full) : [full];
    });
}

const files = LEGAL_FILES.flatMap(walk).filter(
    (f) => /\.tsx?$/.test(f) && !/\.test\.tsx?$/.test(f),
);

describe('legal surface conventions', () => {
    it('finds the legal components it is meant to guard', () => {
        expect(files.length).toBeGreaterThanOrEqual(5);
    });

    it('uses no viewport prefixes anywhere in the legal surface', () => {
        const offenders = files.flatMap((file) =>
            readFileSync(file, 'utf8')
                .split('\n')
                .map((line, index) => ({ line, index }))
                .filter(({ line }) => VIEWPORT_PREFIX.test(line))
                .map(({ line, index }) => `${relative(WEB, file)}:${index + 1}: ${line.trim()}`),
        );
        expect(offenders).toEqual([]);
    });

    it('renders no raw <button> (the design system Button primitive is mandatory)', () => {
        const offenders = files.filter((file) => RAW_BUTTON.test(readFileSync(file, 'utf8')));
        expect(offenders.map((f) => relative(WEB, f))).toEqual([]);
    });
});

describe('privacy policy facts', () => {
    const providers = privacyPolicy.sections.find(
        (s) => s.heading === 'Who receives your information',
    );
    const bullets = providers?.bullets ?? [];

    it('names the language-model providers that receive user text', () => {
        const aiBullets = bullets.filter((b) => /language-model|AI provider/i.test(b));
        expect(aiBullets).toHaveLength(1);
        // The direct chat integration and the gateway are the two paths user text
        // demonstrably takes; a policy that drops either is incomplete again.
        expect(aiBullets[0]).toMatch(/DeepSeek/);
        expect(aiBullets[0]).toMatch(/gateway/i);
    });

    it('does not claim session replay masks on-screen text', () => {
        const usage = privacyPolicy.sections
            .flatMap((s) => s.bullets ?? [])
            .find((b) => b.startsWith('Usage data:'));
        expect(usage).toBeDefined();
        expect(usage).not.toMatch(/text inputs masked/i);
        expect(usage).toMatch(/form inputs masked/i);
    });

    it('does not offer a third-party-script blocker as the analytics opt-out', () => {
        const choices = privacyPolicy.sections.flatMap((s) => s.paragraphs ?? []).join(' ');
        // PostHog is first-party proxied at /p, so that advice could not work.
        expect(choices).not.toMatch(/blocking third-party scripts/i);
        expect(choices).toMatch(/benchify\.dev\/p/);
    });

    it('commits to a response window a data-subject request can be held to', () => {
        const choices = privacyPolicy.sections.flatMap((s) => s.paragraphs ?? []).join(' ');
        expect(choices).toMatch(/respond within 30 days/i);
        expect(choices).not.toMatch(/within a reasonable period/i);
    });
});
