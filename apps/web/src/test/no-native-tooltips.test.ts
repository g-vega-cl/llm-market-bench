import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, test } from 'vitest';

const DOM_TITLE = /<([a-z][\w.-]*)\b[^>]*?\btitle\s*=/g;
const BADGE_TITLE = /<Badge\b[^>]*?\btitle\s*=/g;
const SVG_TITLE = /<title\b/g;

function findNativeTooltips(source: string): string[] {
    const offenders: string[] = [];
    const report = (match: RegExpExecArray, label: string) => {
        const line = source.slice(0, match.index).split('\n').length;
        offenders.push(`${label} at line ${line}`);
    };
    for (const match of source.matchAll(DOM_TITLE)) report(match, `DOM <${match[1]}> title`);
    for (const match of source.matchAll(BADGE_TITLE)) report(match, 'Badge title');
    for (const match of source.matchAll(SVG_TITLE)) report(match, 'SVG <title>');
    return offenders;
}

function productionTsxFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((entry) => {
        const path = join(dir, entry);
        if (statSync(path).isDirectory()) return productionTsxFiles(path);
        return path.endsWith('.tsx') && !path.endsWith('.test.tsx') ? [path] : [];
    });
}

describe('native tooltip ban', () => {
    test('scanner catches real tooltip patterns but not component title props', () => {
        expect(findNativeTooltips('<span title="hint">text</span>')).toHaveLength(1);
        expect(findNativeTooltips('<Badge title="hint">BAD</Badge>')).toHaveLength(1);
        expect(findNativeTooltips('<svg><title>Icon</title></svg>')).toHaveLength(1);
        expect(findNativeTooltips('<ErrorCard title="Failed" message="..." />')).toEqual([]);
    });

    test('production TSX has no title attributes or SVG title tags', () => {
        const srcDir = join(process.cwd(), 'src');
        const offenders = productionTsxFiles(srcDir).flatMap((file) =>
            findNativeTooltips(readFileSync(file, 'utf8')).map((issue) => `${file}: ${issue}`),
        );

        expect(offenders).toEqual([]);
    });
});
