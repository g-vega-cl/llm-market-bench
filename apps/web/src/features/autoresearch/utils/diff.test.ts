import { describe, expect, it } from 'vitest';
import { diffLines } from './diff';

describe('diffLines', () => {
    it('handles identical inputs', () => {
        const text = 'line 1\nline 2\nline 3';
        const result = diffLines(text, text);
        expect(result).toEqual([{ value: 'line 1' }, { value: 'line 2' }, { value: 'line 3' }]);
    });

    it('handles line additions', () => {
        const oldText = 'line 1\nline 3';
        const newText = 'line 1\nline 2\nline 3';
        const result = diffLines(oldText, newText);
        expect(result).toEqual([
            { value: 'line 1' },
            { value: 'line 2', added: true },
            { value: 'line 3' },
        ]);
    });

    it('handles line deletions', () => {
        const oldText = 'line 1\nline 2\nline 3';
        const newText = 'line 1\nline 3';
        const result = diffLines(oldText, newText);
        expect(result).toEqual([
            { value: 'line 1' },
            { value: 'line 2', removed: true },
            { value: 'line 3' },
        ]);
    });

    it('handles both additions and deletions', () => {
        const oldText = 'line 1\nline 2';
        const newText = 'line 2\nline 3';
        const result = diffLines(oldText, newText);
        expect(result).toEqual([
            { value: 'line 1', removed: true },
            { value: 'line 2' },
            { value: 'line 3', added: true },
        ]);
    });

    it('handles completely different text', () => {
        const oldText = 'hello';
        const newText = 'world';
        const result = diffLines(oldText, newText);
        expect(result).toEqual([
            { value: 'hello', removed: true },
            { value: 'world', added: true },
        ]);
    });
});
