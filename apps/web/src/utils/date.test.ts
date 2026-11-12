import { describe, expect, it } from 'vitest';
import {
    formatEasternDate,
    formatEasternDateTime,
    formatEasternDateTimeWithYear,
    formatEasternExactTime,
    formatEasternShortDate,
    formatEasternShortDateWithYear,
    formatEasternShortTime,
    formatEasternTime,
    getEasternDate,
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

    it('formatEasternDate should format date-only strings (YYYY-MM-DD) without rolling backward to previous day in Eastern Time', () => {
        expect(formatEasternDate('2026-11-10')).toBe('Tuesday, November 10, 2026');
        expect(formatEasternShortDateWithYear('2026-11-10')).toBe('Nov 10, 2026');
        expect(formatEasternShortDate('2026-11-10')).toBe('Nov 10');

        // Also handles UTC midnight ISO strings and Date objects instantiated at UTC midnight
        expect(formatEasternDate('2026-11-10T00:00:00Z')).toBe('Tuesday, November 10, 2026');
        expect(formatEasternDate('2026-11-10T00:00:00.000Z')).toBe('Tuesday, November 10, 2026');
        expect(formatEasternDate('2026-11-10T00:00:00+00:00')).toBe('Tuesday, November 10, 2026');
        expect(formatEasternDate(new Date('2026-11-10'))).toBe('Tuesday, November 10, 2026');
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

    it('formatEasternDateTimeWithYear should format to standard format with year and standard spaces', () => {
        const formatted = formatEasternDateTimeWithYear(mockTimestamp);
        expect(formatted).toBe('May 29, 2026, 10:45 AM ET');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('formatEasternExactTime should format with seconds and standard spaces', () => {
        const formatted = formatEasternExactTime(mockTimestamp);
        expect(formatted).toBe('10:45:00 AM ET');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('formatEasternShortDateWithYear should format to month, day, and year', () => {
        const formatted = formatEasternShortDateWithYear(mockTimestamp);
        expect(formatted).toBe('May 29, 2026');

        expect(formatted.includes('\u202f')).toBe(false);
        expect(formatted.includes('\u00a0')).toBe(false);
    });

    it('should gracefully handle null, undefined, or empty values', () => {
        expect(formatEasternTime(null)).toBe('Unknown');
        expect(formatEasternTime(undefined)).toBe('Unknown');
        expect(formatEasternTime('')).toBe('Unknown');

        expect(formatEasternExactTime(null)).toBe('Unknown');
        expect(formatEasternExactTime(undefined)).toBe('Unknown');
        expect(formatEasternExactTime('')).toBe('Unknown');

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

        expect(formatEasternShortDateWithYear(null)).toBe('Unknown');
        expect(formatEasternShortDateWithYear(undefined)).toBe('Unknown');
        expect(formatEasternShortDateWithYear('')).toBe('Unknown');

        expect(formatEasternDateTimeWithYear(null)).toBe('Pending');
        expect(formatEasternDateTimeWithYear(undefined)).toBe('Pending');
        expect(formatEasternDateTimeWithYear('')).toBe('Pending');
    });

    describe('getEasternDate', () => {
        it('extracts YYYY-MM-DD in America/New_York avoiding UTC rollover', () => {
            // At 19:30 EST (Nov 10), UTC is 00:30 UTC next day (Nov 11)
            const utcMidnightNextDay = '2026-11-11T00:30:00Z';
            expect(getEasternDate(utcMidnightNextDay)).toBe('2026-11-10');

            // At 15:00 UTC (10:00 AM EST)
            const dayTime = '2026-11-10T15:00:00Z';
            expect(getEasternDate(dayTime)).toBe('2026-11-10');

            // Date-only and UTC midnight should not roll back to previous day
            expect(getEasternDate('2026-11-10')).toBe('2026-11-10');
            expect(getEasternDate('2026-11-10T00:00:00Z')).toBe('2026-11-10');
            expect(getEasternDate(new Date('2026-11-10'))).toBe('2026-11-10');
        });

        it('handles null, undefined, or invalid dates gracefully', () => {
            expect(getEasternDate('invalid-date')).toBe('');
            expect(getEasternDate(null)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
            expect(getEasternDate(undefined)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        });
    });
});
