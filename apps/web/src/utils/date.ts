/**
 * Centralized Date & Time utilities normalized for SSR compatibility.
 * Standardizes formatting to America/New_York (Eastern Time) and strips any
 * narrow/standard non-breaking space ICU characters to prevent React hydration mismatches.
 */

/**
 * Replaces any form of whitespace (including U+202F narrow no-break space
 * and U+00A0 non-breaking space) with a standard U+0020 space.
 */
export function normalizeWhitespace(str: string): string {
    return str.replace(/\s+/g, ' ').trim();
}

/**
 * Formats a timestamp into a space-normalized Eastern Time string: e.g. "10:45 AM ET"
 */
export function formatEasternTime(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const timeStr = date.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: 'numeric',
            minute: '2-digit',
        });

        return normalizeWhitespace(`${timeStr} ET`);
    } catch {
        return 'Unknown';
    }
}

/**
 * Formats a timestamp or Date object into a space-normalized full Eastern Date string:
 * e.g. "Friday, May 29, 2026"
 */
export function formatEasternDate(dateStrOrObj: string | Date | null | undefined): string {
    if (!dateStrOrObj) return 'Unknown';
    try {
        const date = typeof dateStrOrObj === 'string' ? new Date(dateStrOrObj) : dateStrOrObj;
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const dateStr = date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        });

        return normalizeWhitespace(dateStr);
    } catch {
        return 'Unknown';
    }
}

/**
 * Formats a timestamp into a space-normalized short Eastern Date & Time string:
 * e.g. "May 29 • 10:45 AM ET"
 */
export function formatEasternDateTime(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const formattedDate = date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            month: 'short',
            day: 'numeric',
        });

        const formattedTime = date.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: 'numeric',
            minute: '2-digit',
        });

        return normalizeWhitespace(`${formattedDate} • ${formattedTime} ET`);
    } catch {
        return 'Unknown';
    }
}

/**
 * Formats a timestamp into a space-normalized time-only Eastern string: e.g. "10:45 AM"
 */
export function formatEasternShortTime(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const timeStr = date.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: 'numeric',
            minute: '2-digit',
        });

        return normalizeWhitespace(timeStr);
    } catch {
        return 'Unknown';
    }
}

/**
 * Formats a timestamp into a space-normalized short Eastern Date string: e.g. "May 29"
 */
export function formatEasternShortDate(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const dateStrFormatted = date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            month: 'short',
            day: 'numeric',
        });

        return normalizeWhitespace(dateStrFormatted);
    } catch {
        return 'Unknown';
    }
}

/**
 * Formats a timestamp into a space-normalized Eastern Date & Time string with year:
 * e.g. "May 29, 2026, 10:45 AM ET"
 */
export function formatEasternDateTimeWithYear(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Pending';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Pending';

        const formattedDate = date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });

        const formattedTime = date.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: '2-digit',
            minute: '2-digit',
        });

        return normalizeWhitespace(`${formattedDate}, ${formattedTime} ET`);
    } catch {
        return 'Pending';
    }
}
