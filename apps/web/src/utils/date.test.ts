import { describe, expect, it } from 'vitest';
import {
    formatEasternDate,
    formatEasternDateTime,
    formatEasternShortDate,
    formatEasternShortTime,
    formatEasternTime,
    normalizeWhitespace,
} from './date';

describe('normalizeWhitespace utility', () => {
    it('should replace various ICU whitespace characters with standard U+0020 space', () => {
        const inputWithNarrowNBSP = '10:45\u202fAM';
        const inputWithNBSP = '10:45\u00a0AM';
        const inputWithMixed = 'May\u00a029\u202f•\u00a010:45\u202fAM';

        expect(normalizeWhitespace(inputWithNarrowNBSP)).toBe('10:45 AM');
        expect(normalizeWhitespace(inputWithNBSP)).toBe('10:45 AM');
        expect(normalizeWhitespace(inputWithMixed)).toBe('May 29 • 10:45 AM');

        // Character code assertion to be absolutely sure
        const result = normalizeWhitespace(inputWithNarrowNBSP);
        expect(result.charCodeAt(5)).toBe(32); // index of space should be 32 (U+0020)
    });
});

describe('Centralized Eastern Time date formatters', () => {
    const mockTimestamp = '2026-05-29T14:45:00Z'; // 10:45 AM EDT (Eastern Daylight Time)

    it('formatEasternTime should format correctly with ET suffix and standard space', () => {
        const formatted = formatEasternTime(mockTimestamp);
        expect(formatted).toBe('10:45 AM ET');

        // Assert no non-standard whitespace remains
        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('formatEasternDate should format correctly with full day/month structure', () => {
        const formatted = formatEasternDate(mockTimestamp);
        expect(formatted).toBe('Friday, May 29, 2026');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('formatEasternDateTime should format to a short date and time structure', () => {
        const formatted = formatEasternDateTime(mockTimestamp);
        expect(formatted).toBe('May 29 • 10:45 AM ET');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('formatEasternShortTime should format to time only with standard space', () => {
        const formatted = formatEasternShortTime(mockTimestamp);
        expect(formatted).toBe('10:45 AM');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('formatEasternShortDate should format to month and day only', () => {
        const formatted = formatEasternShortDate(mockTimestamp);
        expect(formatted).toBe('May 29');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('should gracefully handle null, undefined, or empty values', () => {
        expect(formatEasternTime(null)).toBe('Unknown');
        expect(formatEasternTime(undefined)).toBe('Unknown');
        expect(formatEasternTime('')).toBe('Unknown');

        expect(formatEasternDate(null)).toBe('Unknown');
        expect(formatEasternDate(undefined)).toBe('Unknown');
        expect(formatEasternDate('')).toBe('Unknown');

        expect(formatEasternDateTime(null)).toBe('Unknown');
        expect(formatEasternDateTime(undefined)).toBe('Unknown');
        expect(formatEasternDateTime('')).toBe('Unknown');

        expect(formatEasternShortTime(null)).toBe('Unknown');
        expect(formatEasternShortTime(undefined)).toBe('Unknown');
        expect(formatEasternShortTime('')).toBe('Unknown');

        expect(formatEasternShortDate(null)).toBe('Unknown');
        expect(formatEasternShortDate(undefined)).toBe('Unknown');
        expect(formatEasternShortDate('')).toBe('Unknown');
    });
});
