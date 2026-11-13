import cases from '@repo/config/news-excerpt-cases.json';
import { describe, expect, it } from 'vitest';
import { buildNewsExcerpt } from './news-excerpt';

describe('buildNewsExcerpt', () => {
    it('centers on the keyword hit', () => {
        const text = `${'alpha '.repeat(100)}Trump announced new chips tariffs ${'omega '.repeat(100)}`;
        const out = buildNewsExcerpt(text, ['chips']);
        expect(out).toContain('chips');
        expect(out.startsWith('…')).toBe(true);
        expect(out.endsWith('…')).toBe(true);
        expect(out.length).toBeLessThan(400);
    });

    it('is case-insensitive and collapses whitespace', () => {
        expect(buildNewsExcerpt('Line one\n\n  mentions   TRUMP here', ['trump'])).toBe(
            'Line one mentions TRUMP here',
        );
    });

    it('falls back to the lead without keywords or body hit', () => {
        const out = buildNewsExcerpt(`start ${'filler '.repeat(200)}`, ['nvidia']);
        expect(out.startsWith('start')).toBe(true);
        expect(out.endsWith('…')).toBe(true);
        expect(buildNewsExcerpt('word '.repeat(200), []).length).toBeLessThanOrEqual(301);
    });

    it('returns empty for empty text', () => {
        expect(buildNewsExcerpt('', ['x'])).toBe('');
        expect(buildNewsExcerpt(null, ['x'])).toBe('');
    });
});

describe('buildNewsExcerpt parity with engine (shared fixture)', () => {
    // Same cases are asserted by apps/engine/recipes/test_push_hydrator.py.
    it.each(cases)('$name', ({ text, keywords, expected }) => {
        expect(buildNewsExcerpt(text, keywords)).toBe(expected);
    });
});
