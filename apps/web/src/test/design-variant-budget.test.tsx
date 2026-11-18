import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Design Variant Budget enforcement.
 *
 * Rule: at most two style variants per component.
 *   - Button / Badge / Card expose at most two variants.
 *   - Zero light-theme residue (dark:), zero text-white, zero backdrop-blur.
 *   - Zero banned font weights / sizes.
 *   - Zero ad-hoc raw <button> elements (all use the Button primitive).
 *   - Each component file uses at most two (size, weight) typography combos.
 *   - Each component file uses at most two decorative border treatments.
 */

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(TEST_DIR, '..', '..', '..', '..');
const UIDS = join(REPO_ROOT, 'packages', 'ui-design-system', 'src');
const WEB = join(REPO_ROOT, 'apps', 'web', 'src');

const SKIP_DIRS = new Set([
    'node_modules',
    'dist',
    'coverage',
    'build',
    '.scratch',
    '.git',
    '.netlify',
]);

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

function sourceFiles(): string[] {
    return [...walk(UIDS), ...walk(WEB)].filter(
        (f) =>
            (f.endsWith('.tsx') || f.endsWith('.ts')) &&
            !f.includes('.test.') &&
            !f.includes('.stories.') &&
            !f.endsWith('.d.ts'),
    );
}

function read(f: string): string {
    return readFileSync(f, 'utf8');
}

const FONT_SIZE_RE = /\btext-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl)\b/g;
const FONT_WEIGHT_RE =
    /\bfont-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)\b/g;
const BORDER_TOKEN_RE =
    /(?<![\w-])(border-(?:collapse|separate)|border-(?:t|r|b|l|x|y)(?:-(?:0|2|4|8))?|border-(?:0|2|4|8)|border|divide-[xy](?:-rev)?(?:-\d+)?|ring(?:-\d+)?(?:-inset)?|outline(?:-\d+)?)(?![\w-])/g;

const STRUCTURAL_BORDER = new Set(['border-collapse', 'border-separate']);

function isStructuralBorder(token: string): boolean {
    return (
        STRUCTURAL_BORDER.has(token) ||
        /^border-[trblxy]-0$/.test(token) ||
        token === 'border-0' ||
        token.startsWith('divide-') ||
        token.startsWith('ring') ||
        token.startsWith('outline')
    );
}

/**
 * Reduces a border token to a visual *style* (line weight), ignoring which
 * side it is drawn on. `border` and `border-t` are both a 1px rule; `border-2`
 * is a 2px rule; `border-l-4` is a 4px accent bar.
 */
function borderStyle(token: string): string | null {
    if (isStructuralBorder(token)) return null;
    if (/dashed|dotted|double/.test(token)) return 'dashed';
    const width = token.match(/-(0|2|4|8)$/);
    if (width) return width[1] === '0' ? null : `${width[1]}px`;
    return '1px';
}

/** Collects (size, weight) combos found inside the same string literal. */
function typographyCombos(text: string): Set<string> {
    const combos = new Set<string>();
    const strings = text.matchAll(/'([^'\\]*)'|"([^"\\]*)"|`([^`]*)`/gs);
    for (const m of strings) {
        const literal = m[1] ?? m[2] ?? m[3] ?? '';
        const size = [...literal.matchAll(new RegExp(FONT_SIZE_RE.source, 'g'))][0]?.[1];
        const weight = [...literal.matchAll(new RegExp(FONT_WEIGHT_RE.source, 'g'))][0]?.[1];
        if (size && weight) combos.add(`${size}/${weight}`);
    }
    return combos;
}

function borderTreatments(text: string): Set<string> {
    const out = new Set<string>();
    for (const m of text.matchAll(new RegExp(BORDER_TOKEN_RE.source, 'g'))) {
        const style = borderStyle(m[0]);
        if (style) out.add(style);
    }
    return out;
}

describe('Design Variant Budget (max two variants per component)', () => {
    describe('Primitives expose at most two variants', () => {
        const cases: Array<[string, string]> = [
            ['Button', join(UIDS, 'primitives', 'Button.tsx')],
            ['Badge', join(UIDS, 'primitives', 'Badge.tsx')],
            ['Card', join(UIDS, 'primitives', 'Card.tsx')],
        ];

        it.each(cases)('%s variant union is at most two members', (_name, file) => {
            const text = read(file);
            const match = text.match(/variant\?:\s*([^;]+);/);
            expect(match, `${_name} must declare a variant prop`).toBeTruthy();
            const members = (match?.[1] ?? '')
                .split('|')
                .map((s) => s.trim().replace(/^'|'$/g, ''))
                .filter(Boolean);
            expect(
                members.length,
                `${_name} exposes ${members.length} variants`,
            ).toBeLessThanOrEqual(2);
        });
    });

    describe('No legacy decorative props', () => {
        it('SectionHeading no longer exposes a gradient prop', () => {
            const text = read(join(UIDS, 'patterns', 'SectionHeading.tsx'));
            expect(text).not.toMatch(/gradient\?:/);
        });

        it('Button no longer exposes gradient or rounded props', () => {
            const text = read(join(UIDS, 'primitives', 'Button.tsx'));
            expect(text).not.toMatch(/gradient\?:/);
            expect(text).not.toMatch(/rounded\?:/);
        });

        it('Badge no longer exposes radius or severity props', () => {
            const text = read(join(UIDS, 'primitives', 'Badge.tsx'));
            expect(text).not.toMatch(/radius\?:/);
            expect(text).not.toMatch(/severity\?:/);
        });
    });

    describe('Zero legacy theme residue in source', () => {
        const banned = [
            { label: 'dark: variant', re: /\bdark:/ },
            { label: 'text-white', re: /\btext-white\b/ },
            { label: 'backdrop-blur', re: /\bbackdrop-blur/ },
            {
                label: 'font-light/medium/semibold/extrabold/black',
                re: /\bfont-(light|medium|semibold|extrabold|black)\b/,
            },
            { label: 'banned font size', re: /\btext-(base|xl|2xl|3xl|4xl|5xl|6xl|7xl)\b/ },
        ];

        for (const { label, re } of banned) {
            it(`contains zero ${label}`, () => {
                const offenders = sourceFiles()
                    .filter((f) => re.test(read(f)))
                    .map((f) => relative(REPO_ROOT, f));
                expect(offenders, `${label} found in: ${offenders.join(', ')}`).toEqual([]);
            });
        }
    });

    describe('Zero ad-hoc raw <button> elements in apps/web', () => {
        it('every button renders through the Button primitive', () => {
            const offenders = sourceFiles()
                .filter((f) => f.startsWith(WEB))
                .filter((f) => /<button\b/.test(read(f)))
                .map((f) => relative(REPO_ROOT, f));
            expect(offenders, `raw <button> found in: ${offenders.join(', ')}`).toEqual([]);
        });
    });

    describe('Per-component typography budget (max two combos)', () => {
        it('no component mixes more than two size/weight combos', () => {
            const offenders: string[] = [];
            for (const f of sourceFiles()) {
                const combos = typographyCombos(read(f));
                if (combos.size > 2) {
                    offenders.push(`${relative(REPO_ROOT, f)} -> ${[...combos].join(', ')}`);
                }
            }
            expect(offenders, offenders.join('\n')).toEqual([]);
        });
    });

    describe('Per-component border budget (max two decorative treatments)', () => {
        it('no component mixes more than two decorative border treatments', () => {
            const offenders: string[] = [];
            for (const f of sourceFiles()) {
                const borders = borderTreatments(read(f));
                if (borders.size > 2) {
                    offenders.push(`${relative(REPO_ROOT, f)} -> ${[...borders].join(', ')}`);
                }
            }
            expect(offenders, offenders.join('\n')).toEqual([]);
        });
    });
});
