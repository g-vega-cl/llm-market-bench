import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Site-wide Background & Font Contrast Audit.
 *
 * Prevents unreadable black-on-dark or cream-on-white regressions caused by:
 *   1. `text-voxel-trough` (#101713) or `text-accent-ink` without an explicit bright background.
 *   2. Dark-mode-stripped duplicate classes (`text-zinc-900 text-zinc-100`, `bg-white bg-zinc-900`)
 *      where Tailwind v4 CSS order makes the dark text shade win over the light shade.
 *   3. Dark text colors (`text-zinc-600..950`, `text-gray-600..950`, `text-emerald-600..700`, etc.)
 *      or light backgrounds (`bg-white`, `bg-zinc-50..200`, `bg-blue-100`, etc.) in a dark-only theme.
 *   4. `<Button>` or `<Badge>` primitive calls passing `bg-*`/`text-*` color overrides in `className`
 *      without setting `variant`/`colorScheme` (since `cn` omits `tailwind-merge`).
 *   5. Undefined shadcn/typo color tokens (`text-foreground`, `text-muted-foreground`, `border-border`,
 *      `bg-primary`, `text-zinc-905`, etc.).
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

const BRIGHT_BG_FOR_TROUGH =
    /\bbg-(?:accent|success|danger|info|warning|emerald-(?:400|500)|amber-(?:400|500|600)|cyan-(?:500|600)|blue-500|rose-500|electric-blue-500|cyber-yellow-500)\b(?!\/)/;

const DARK_TEXT_RE =
    /\b(?:hover:|group-hover:|focus:)?text-(?:black|zinc-(?:950|900|800|700|600|500)|gray-(?:950|900|800|700|600|500)|slate-(?:950|900|800|700|600|500)|neutral-(?:950|900|800|700|600|500)|stone-(?:950|900|800|700|600|500)|emerald-(?:600|700|800|900)|rose-(?:600|700|800|900)|red-(?:600|700|800|900)|amber-(?:600|700|800|900)|blue-(?:600|700|800|900)|indigo-(?:600|700|800|900)|purple-(?:600|700|800|900)|deep-purple-(?:600|700|800|900)|electric-blue-(?:600|700|800|900)|cyber-yellow-(?:600|700|800|900))\b/;

const LIGHT_BG_RE =
    /\b(?:hover:)?bg-(?:white|zinc-(?:50|100|200)|gray-(?:50|100|200)|slate-(?:50|100|200)|neutral-(?:50|100|200)|stone-(?:50|100|200)|emerald-(?:50|100)|rose-(?:50|100)|red-(?:50|100)|amber-(?:50|100)|blue-(?:50|100|200)|indigo-(?:50|100)|purple-(?:50|100)|accent-light|success-light|danger-light|info-light|warning-light|electric-blue-(?:50|100)|deep-purple-(?:50|100)|cyber-yellow-(?:50|100))(?:\b|\/)/;

const UNDEFINED_TOKEN_RE =
    /\b(?:bg-primary|text-primary|text-primary-foreground|text-muted-foreground|text-foreground|hover:text-foreground|bg-card|bg-muted|bg-background|border-border|divide-border|bg-zinc-55|text-zinc-905|text-zinc-250|text-zinc-650|border-zinc-150|bg-zinc-850|border-zinc-850|hover:bg-zinc-850|border-slate-850|bg-slate-850|text-slate-850|glow-red)\b/;

const BARE_COLOR_UTILITY_RE =
    /(?:^|[\s"'`])(text|bg|fill|stroke)-(?:zinc|gray|slate|neutral|stone|red|rose|amber|yellow|emerald|green|teal|cyan|sky|blue|indigo|purple|pink|electric-blue|deep-purple|cyber-yellow|alert-red|neon-green|voxel)-[a-z0-9-]+/g;

function hasDuplicateColorInString(str: string): string | null {
    const seen = new Map<string, string>();
    for (const m of str.matchAll(BARE_COLOR_UTILITY_RE)) {
        const prefix = m[1];
        const cls = m[0].trim();
        const prev = seen.get(prefix);
        if (prev) return `${prev} ... ${cls}`;
        seen.set(prefix, cls);
    }
    return null;
}

const TEXT_NON_COLOR_RE =
    /^text-(?:xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl|7xl|left|right|center|justify|start|end|display|mono|sans|serif|wrap|nowrap|balance|pretty|ellipsis|clip)$/;

function nextCursorQuote(ch: string, quote: string | null): string | null {
    if (quote) return ch === quote ? null : quote;
    return ch === "'" || ch === '"' || ch === '`' ? ch : null;
}

function scanTagEnd(text: string, startIndex: number): number | null {
    let brace = 0;
    let quote: string | null = null;
    for (let i = startIndex; i < text.length; i++) {
        const ch = text[i];
        if (ch === '\\') {
            i++;
            continue;
        }
        const wasQuoted = quote !== null;
        quote = nextCursorQuote(ch, quote);
        if (wasQuoted || quote !== null) continue;
        if (ch === '{') brace++;
        else if (ch === '}') brace--;
        else if (ch === '>' && brace === 0) return i;
    }
    return null;
}

function extractJsxTags(text: string, tagName: string): Array<{ line: number; tag: string }> {
    const results: Array<{ line: number; tag: string }> = [];
    const pat = new RegExp(`<${tagName}\\b`, 'g');
    let m: RegExpExecArray | null;
    // biome-ignore lint/suspicious/noAssignInExpressions: scanner loop
    while ((m = pat.exec(text)) !== null) {
        const end = scanTagEnd(text, pat.lastIndex);
        if (end === null) break;
        const line = text.slice(0, m.index).split('\n').length;
        results.push({ line, tag: text.slice(m.index, end + 1) });
        pat.lastIndex = end + 1;
    }
    return results;
}

function extractClassNameProp(tag: string): string {
    const match = /\bclassName=(?:"([^"]*)"|'([^']*)'|\{(`[^}]*`|"[^"]*"|'[^']*')\})/.exec(tag);
    return match?.[1] ?? match?.[2] ?? match?.[3] ?? '';
}

function isColorUtilityToken(token: string): boolean {
    if (token.startsWith('text-')) return !TEXT_NON_COLOR_RE.test(token);
    if (token.startsWith('bg-')) return !token.startsWith('bg-gradient-');
    return token !== 'fill-none' && token !== 'fill-current' && token !== 'stroke-current';
}

function findColorTokens(tag: string): string[] {
    const cls = extractClassNameProp(tag);
    if (!cls) return [];
    const tokens = cls.match(/\b(?:bg|text|fill|stroke)-[a-z0-9-]+\b/g) ?? [];
    return tokens.filter(isColorUtilityToken);
}

function scanDuplicateColorTokens(): string[] {
    const offenders: string[] = [];
    for (const f of sourceFiles()) {
        const lines = read(f).split('\n');
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.includes('?') && line.includes(':')) continue;
            for (const str of line.match(/"[^"]*"|'[^']*'/g) ?? []) {
                const dup = hasDuplicateColorInString(str);
                if (dup) offenders.push(`${relative(REPO_ROOT, f)}:${i + 1} (${dup})`);
            }
        }
    }
    return offenders;
}

function collectPrimitiveOverrides(tagName: string): string[] {
    const offenders: string[] = [];
    for (const f of sourceFiles()) {
        for (const { line, tag } of extractJsxTags(read(f), tagName)) {
            const colorTokens = findColorTokens(tag);
            if (colorTokens.length > 0) {
                offenders.push(`${relative(REPO_ROOT, f)}:${line} (${colorTokens.join(' ')})`);
            }
        }
    }
    return offenders;
}

function scanLinesForRegex(pattern: RegExp): string[] {
    const offenders: string[] = [];
    for (const f of sourceFiles()) {
        const lines = read(f).split('\n');
        for (let i = 0; i < lines.length; i++) {
            const m = lines[i].match(pattern);
            if (m) offenders.push(`${relative(REPO_ROOT, f)}:${i + 1} (${m[0]})`);
        }
    }
    return offenders;
}

describe('Site-wide Background & Font Contrast Audit', () => {
    it('never uses text-voxel-trough or text-accent-ink without an explicit bright background', () => {
        const offenders: string[] = [];
        for (const f of sourceFiles()) {
            const text = read(f);
            const lines = text.split('\n');
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i];
                if (/\b(?:hover:)?text-(?:voxel-trough|accent-ink)\b/.test(line)) {
                    // Allow in primitive definitions or when bright bg is in the same class expression
                    const windowText = lines.slice(Math.max(0, i - 2), i + 2).join(' ');
                    if (!BRIGHT_BG_FOR_TROUGH.test(windowText)) {
                        offenders.push(`${relative(REPO_ROOT, f)}:${i + 1}`);
                    }
                }
            }
        }
        expect(offenders, `text-voxel-trough without bright bg:\n${offenders.join('\n')}`).toEqual(
            [],
        );
    });

    it('contains zero dark-shade text classes on dark surfaces', () => {
        const offenders = scanLinesForRegex(DARK_TEXT_RE);
        expect(offenders, `Dark text colors found:\n${offenders.join('\n')}`).toEqual([]);
    });

    it('contains zero legacy light backgrounds (bg-white, bg-zinc-50/100/200, etc.)', () => {
        const offenders = scanLinesForRegex(LIGHT_BG_RE);
        expect(offenders, `Light backgrounds found:\n${offenders.join('\n')}`).toEqual([]);
    });

    it('contains zero undefined shadcn/typo color tokens', () => {
        const offenders = scanLinesForRegex(UNDEFINED_TOKEN_RE);
        expect(offenders, `Undefined tokens found:\n${offenders.join('\n')}`).toEqual([]);
    });

    it('contains zero stripped-dark duplicate color tokens on the same element', () => {
        const offenders = scanDuplicateColorTokens();
        expect(offenders, `Duplicate color classes found:\n${offenders.join('\n')}`).toEqual([]);
    });

    it('never overrides Button colors via className', () => {
        const offenders = collectPrimitiveOverrides('Button');
        expect(
            offenders,
            `<Button> color overrides in className:\n${offenders.join('\n')}`,
        ).toEqual([]);
    });

    it('never overrides Badge colors via className', () => {
        const offenders = collectPrimitiveOverrides('Badge');
        expect(offenders, `<Badge> color overrides in className:\n${offenders.join('\n')}`).toEqual(
            [],
        );
    });
});
