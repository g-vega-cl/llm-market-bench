import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PageLayout } from '@llm-market-bench/ui-design-system';
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

/**
 * Page-surface conventions.
 *
 * Two rules from `.agents/rules/design-spec.md` are enforced here, because both
 * decay silently when they are only prose:
 *
 * 1. §4a — action surfaces (`/personality`, `/build`, `/chat`) carry no visible
 *    page title; the page name survives as exactly one `sr-only` <h1> per render
 *    branch. Browse surfaces keep a visible <h1>.
 * 2. §3.4 — a page with its own vertical rhythm opts out of `PageLayout` padding
 *    (`withPadding={false}` + its own px/py) instead of overriding it through
 *    `className`. `cn` is bare clsx, so an override keeps both declarations and
 *    the stylesheet order decides the winner.
 *
 * `ACTION_SURFACE_FILES` is deliberately a literal list: adding a page means
 * editing this file and the spec section in the same change.
 */

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const WEB = join(TEST_DIR, '..');
const REPO_ROOT = join(TEST_DIR, '..', '..', '..', '..');

const ACTION_SURFACE_FILES = [
    join(WEB, 'features', 'personality', 'PersonalityQuizPage.tsx'),
    join(WEB, 'features', 'recipes', 'builder', 'BuilderChatPanel.tsx'),
    join(WEB, 'features', 'recipes', 'builder', 'CompiledBotWorkspace.tsx'),
    join(WEB, 'features', 'chat', 'ChatPage.tsx'),
];

const SKIP_DIRS = new Set([
    'node_modules',
    'dist',
    'coverage',
    'build',
    '.scratch',
    '.git',
    '.netlify',
]);

const PADDING_TOKEN = /^(p|px|py|pt|pr|pb|pl)-[\w.[\]/-]+$/;
const VARIANT_PREFIX = /^(?:[a-z0-9-]+:)+/;

function walk(dir: string): string[] {
    const out: string[] = [];
    for (const entry of readdirSync(dir)) {
        if (SKIP_DIRS.has(entry)) continue;
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) out.push(...walk(full));
        else out.push(full);
    }
    return out;
}

/** `<PageLayout ...>` opening tags, including tags that span several lines. */
function pageLayoutTags(source: string): string[] {
    return source.match(/<PageLayout\b[^>]*>/g) ?? [];
}

/**
 * Every class string the tag can carry, including `className={cn('py-6', x)}`
 * and template literals. Unquoted identifiers (`styles.shell`) are invisible to
 * a source scan — the spec forbids that composition for padding.
 */
function classValuesOf(tag: string): string[] {
    const attribute = tag.match(/className=\{[\s\S]*?\}|className="[^"]*"/);
    if (!attribute) return [];
    return [...attribute[0].matchAll(/["'`]([^"'`]*)["'`]/g)].map((match) => match[1]);
}

function paddingTokensOf(tag: string): string[] {
    return classValuesOf(tag)
        .flatMap((value) => value.split(/\s+/))
        .map((token) => token.replace(VARIANT_PREFIX, ''))
        .filter((token) => PADDING_TOKEN.test(token));
}

function paddingViolations(file: string): string[] {
    const source = readFileSync(file, 'utf8');
    const violations: string[] = [];

    for (const tag of pageLayoutTags(source)) {
        const paddingTokens = paddingTokensOf(tag);
        if (paddingTokens.length === 0) continue;

        const optedOut = tag.includes('withPadding={false}');
        if (!optedOut) {
            violations.push(
                `${relative(REPO_ROOT, file)} sets ${paddingTokens.join(', ')} without withPadding={false}`,
            );
            continue;
        }

        // Opting out removes the base px-6 md:px-12, so the page must re-declare it.
        if (!paddingTokens.some((token) => token.startsWith('px-') || token === 'p-0')) {
            violations.push(
                `${relative(REPO_ROOT, file)} opts out of PageLayout padding without horizontal padding`,
            );
        }
    }

    return violations;
}

/** Class tokens on an element: exact match, so `not-sr-only` cannot pass as hidden. */
function classTokensOf(tag: string): string[] {
    const match = tag.match(/className="([^"]*)"/);
    return match ? match[1].split(/\s+/).filter(Boolean) : [];
}

describe('action surfaces carry no visible page title', () => {
    it.each(
        ACTION_SURFACE_FILES.map((file) => [relative(REPO_ROOT, file), file] as const),
    )('%s keeps exactly one sr-only h1', (_label, file) => {
        const tags = readFileSync(file, 'utf8').match(/<h1\b[^>]*>/g) ?? [];

        expect(tags).toHaveLength(1);
        expect(classTokensOf(tags[0] ?? '')).toContain('sr-only');
    });
});

describe('PageLayout padding is opted out, never overridden', () => {
    it('every PageLayout caller that sets padding passes withPadding={false}', () => {
        const violations = walk(WEB)
            .filter((file) => file.endsWith('.tsx') && !file.includes('.test.'))
            .flatMap(paddingViolations);

        expect(violations).toEqual([]);
    });

    it('withPadding={false} emits no base vertical padding to collide with the page', () => {
        const { container } = render(
            <PageLayout withPadding={false} className="px-6 md:px-12 py-6">
                content
            </PageLayout>,
        );
        const shell = container.firstElementChild as HTMLElement;

        expect(shell.className).toContain('px-6');
        expect(shell.className).toContain('py-6');
        expect(shell.className).not.toContain('py-8');
        expect(shell.className).not.toContain('md:py-12');
    });
});
