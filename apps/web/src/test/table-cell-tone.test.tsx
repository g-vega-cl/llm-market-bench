import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
    TABLE_CELL_TONES,
    Table,
    TableBody,
    TableCell,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

/**
 * TableCell tone contract.
 *
 * `cn()` is plain clsx (no tailwind-merge), so a caller-supplied `text-success`
 * / `text-danger` class loses to the cell's own `text-voxel-ink` in the emitted
 * stylesheet order. Semantic cell colours therefore must come from the bounded
 * `tone` prop, never from `className`. Weight is fixed at Tier 3 `font-normal`:
 * there is no bold-cell variant.
 */

const TEST_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(TEST_DIR, '..', '..', '..', '..');
const UIDS = join(REPO_ROOT, 'packages', 'ui-design-system', 'src');
const WEB = join(REPO_ROOT, 'apps', 'web', 'src');

const SKIP_DIRS = new Set(['node_modules', 'dist', 'coverage', 'build', '.scratch', '.git']);

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

/** Classes the primitive owns: colour, size, weight, alignment, decoration. */
const BANNED = [
    /\btext-(success|danger|accent|warning|info)(-\w+)?\b/,
    /\btext-voxel-(ink|muted)\b/,
    /\btext-(white|black)\b/,
    /\btext-(zinc|slate|gray|grey|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/,
    /\btext-(xs|sm|base|lg|xl|2xl|3xl)\b/,
    /\bfont-(thin|light|normal|medium|semibold|bold|extrabold|black)\b/,
    /\btext-(left|center|right)\b/,
    /\b(italic|not-italic|underline|line-through)\b/,
    /\bp-\d/, // shorthand is emitted before px-*/py-*, so the base always wins
    /\bp[xyltrb]?-\[[^\]]+\]/, // arbitrary escapes
    /(^|\s)(sm|md|lg|xl|2xl):/, // viewport breakpoints are banned outright
];

/** Padding utilities are only dead when they are at or below the base (`px-4 py-3`). */
const PADDING = /^(px|py)-(\d+(?:\.\d+)?)$/;
const PADDING_BASE: Record<string, number> = { px: 4, py: 3 };

/** Index of the `>` that closes a `<TableCell` opening tag (brace- and quote-aware). */
function tagEnd(text: string, from: number): number {
    // Blank out string literals so their braces and quotes cannot be miscounted.
    const region = text
        .slice(from)
        .replace(/"[^"]*"|'[^']*'|`[^`]*`/g, (literal) => ' '.repeat(literal.length));
    let depth = 0;
    for (let index = 0; index < region.length; index++) {
        const char = region[index];
        if (char === '{') depth += 1;
        else if (char === '}') depth -= 1;
        else if (char === '>' && depth === 0) return from + index;
    }
    return text.length;
}

/** Every `<TableCell …>` opening tag with its 1-based line number. */
function cellTags(text: string): { tag: string; line: number }[] {
    const tags: { tag: string; line: number }[] = [];
    for (const match of text.matchAll(/<TableCell\b/g)) {
        const start = match.index ?? 0;
        const end = tagEnd(text, start + '<TableCell'.length);
        tags.push({
            tag: text.slice(start, end + 1),
            line: text.slice(0, start).split('\n').length,
        });
    }
    return tags;
}

/** Offending classes (or a dynamic className) carried by one cell tag. */
function tagOffenders(tag: string): string[] {
    if (/(^|\s)emphasis(=|\s|>)/.test(tag))
        return ['emphasis prop removed — cells are Tier 3 normal'];
    if (/className=\{/.test(tag)) return ['dynamic className'];
    const literal = tag.match(/className=(?:"([^"]*)"|'([^']*)')/s);
    const value = literal?.[1] ?? literal?.[2];
    if (!value) return [];
    const offenders = BANNED.map((pattern) => value.match(pattern)?.[0]).filter(
        (hit): hit is string => Boolean(hit),
    );
    for (const token of value.split(/\s+/)) {
        const padding = token.match(PADDING);
        if (!padding) continue;
        const [, axis, size] = padding;
        if (Number(size) <= PADDING_BASE[axis]) offenders.push(token);
    }
    return offenders;
}

function cell(props: Record<string, unknown> = {}) {
    return render(
        <Table>
            <TableBody>
                <TableRow>
                    <TableCell {...props}>value</TableCell>
                </TableRow>
            </TableBody>
        </Table>,
    );
}

describe('TableCell tone', () => {
    it('keeps the ink default when no tone is given', () => {
        cell();
        const td = screen.getByRole('cell');
        expect(td.className).toContain('text-voxel-ink');
        expect(td.className).toContain('font-normal');
    });

    it('gainer cells are green and never emit the ink base class', () => {
        cell({ tone: 'positive' });
        const td = screen.getByRole('cell');
        expect(td.className).toContain('text-success');
        expect(td.className).not.toContain('text-voxel-ink');
        expect(td.className).not.toContain('text-danger');
    });

    it('loser cells are red and never emit the ink base class', () => {
        cell({ tone: 'negative' });
        const td = screen.getByRole('cell');
        expect(td.className).toContain('text-danger');
        expect(td.className).not.toContain('text-voxel-ink');
        expect(td.className).not.toContain('text-success');
    });

    it('muted cells are muted and never emit the ink base class', () => {
        cell({ tone: 'muted' });
        const td = screen.getByRole('cell');
        expect(td.className).toContain('text-voxel-muted');
        expect(td.className).not.toContain('text-voxel-ink');
    });

    it('always renders Tier 3 normal weight — there is no bold cell variant', () => {
        cell({ tone: 'positive' });
        const td = screen.getByRole('cell');
        expect(td.className).toContain('font-normal');
        expect(td.className).not.toContain('font-bold');
    });

    it('exposes exactly three tones — the budget is closed', () => {
        expect([...TABLE_CELL_TONES].sort()).toEqual(['muted', 'negative', 'positive']);
    });

    it('no TableCell restyles itself through className', () => {
        const offenders: string[] = [];
        for (const file of [...walk(UIDS), ...walk(WEB)].filter(
            (f) => /\.tsx?$/.test(f) && !f.includes('.test.') && !f.endsWith('.d.ts'),
        )) {
            const text = readFileSync(file, 'utf8');
            for (const { tag, line } of cellTags(text)) {
                for (const hit of tagOffenders(tag)) {
                    offenders.push(
                        `${relative(REPO_ROOT, file)}:${line} "${hit}" — use tone / align`,
                    );
                }
            }
        }
        expect(offenders).toEqual([]);
    });
});
