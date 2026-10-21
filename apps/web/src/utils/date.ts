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
 * Checks whether a timestamp is a date-only string ("YYYY-MM-DD")
 * or a UTC midnight timestamp ("YYYY-MM-DDT00:00:00..."), which represents
 * an End-Of-Day daily bar rather than an intraday time.
 */
export function isMidnightUtcOrDateOnly(dateStr: string | null | undefined): boolean {
    if (!dateStr) return false;
    if (!dateStr.includes('T')) return true;
    return /T00:00:00(\.000)?(\+00:00|Z)?$/.test(dateStr);
}

/**
 * Formats a date-only or midnight UTC EOD timestamp to "Mon DD Close", e.g. "Oct 21 Close".
 */
export function formatEODDateClose(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Market Close';
    const datePart = dateStr.substring(0, 10);
    const [y, m, d] = datePart.split('-').map(Number);
    if (!y || !m || !d) return 'Market Close';
    const noonUtc = new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
    const formatted = noonUtc.toLocaleDateString('en-US', {
        timeZone: 'America/New_York',
        month: 'short',
        day: 'numeric',
    });
    return `${normalizeWhitespace(formatted)} Close`;
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

/**
 * Formats a timestamp into a space-normalized exact Eastern Time string with seconds:
 * e.g. "10:45:00 AM ET"
 */
export function formatEasternExactTime(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const timeStr = date.toLocaleTimeString('en-US', {
            timeZone: 'America/New_York',
            hour: 'numeric',
            minute: '2-digit',
            second: '2-digit',
        });

        return normalizeWhitespace(`${timeStr} ET`);
    } catch {
        return 'Unknown';
    }
}

/**
 * Formats a timestamp into a space-normalized short Eastern Date with year:
 * e.g. "May 29, 2026"
 */
export function formatEasternShortDateWithYear(dateStr: string | null | undefined): string {
    if (!dateStr) return 'Unknown';
    try {
        const date = new Date(dateStr);
        if (Number.isNaN(date.getTime())) return 'Unknown';

        const dateStrFormatted = date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            month: 'short',
            day: 'numeric',
            year: 'numeric',
        });

        return normalizeWhitespace(dateStrFormatted);
    } catch {
        return 'Unknown';
    }
}
