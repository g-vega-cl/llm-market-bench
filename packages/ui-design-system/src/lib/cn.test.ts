import { describe, expect, it } from 'vitest';
import { cn } from './cn';

describe('cn', () => {
    it('combines string classes correctly', () => {
        expect(cn('class-a', 'class-b')).toBe('class-a class-b');
    });

    it('ignores falsy values like null, undefined, false', () => {
        expect(cn('class-a', null, 'class-b', undefined, false, 'class-c')).toBe(
            'class-a class-b class-c',
        );
    });

    it('handles arrays of classes', () => {
        expect(cn(['class-a', 'class-b'], 'class-c')).toBe('class-a class-b class-c');
    });

    it('handles objects with boolean values', () => {
        expect(cn('class-a', { 'class-b': true, 'class-c': false })).toBe('class-a class-b');
    });

    it('handles complex combinations', () => {
        expect(
            cn(
                'class-a',
                ['class-b', 'class-c'],
                { 'class-d': true, 'class-e': false },
                undefined,
                'class-f',
            ),
        ).toBe('class-a class-b class-c class-d class-f');
    });
});
