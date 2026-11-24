/**
 * Shared America/New_York equity market hours, 30-minute live slot, and Turbo window helpers.
 */

const LIVE_SLOT_MINUTES_ET: readonly number[] = [
    9 * 60 + 30,
    10 * 60,
    10 * 60 + 30,
    11 * 60,
    11 * 60 + 30,
    12 * 60,
    12 * 60 + 30,
    13 * 60,
    13 * 60 + 30,
    14 * 60,
    14 * 60 + 30,
    15 * 60,
    15 * 60 + 30,
    16 * 60,
];

const MARKET_OPEN_MINUTES_ET = 9 * 60 + 30;
const MARKET_CLOSE_MINUTES_ET = 16 * 60;
const TURBO_ACTIVATION_CUTOFF_MINUTES_ET = 15 * 60 + 55;
const TURBO_DURATION_MS = 60 * 60 * 1000;

/** One spelling of the live cadence for user-facing copy, next to the schedule it describes. */
export const LIVE_CADENCE_LABEL = '30m';
export const TURBO_CADENCE_LABEL = '5m';

export interface EtClockParts {
    etDate: string;
    weekday: string;
    hour: number;
    minute: number;
    totalMinutes: number;
    isoOffset: string;
}

function parseIsoOffset(shortOffset: string): string {
    const match = shortOffset.match(/GMT([+-])(\d{1,2})(?::(\d{2}))?/);
    if (!match) return '-05:00';
    const sign = match[1];
    const hours = match[2].padStart(2, '0');
    const mins = (match[3] || '00').padStart(2, '0');
    return `${sign}${hours}:${mins}`;
}

export function getEtClockParts(now: Date = new Date()): EtClockParts {
    const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: 'America/New_York',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        weekday: 'short',
        hour: 'numeric',
        minute: 'numeric',
        hourCycle: 'h23',
        timeZoneName: 'shortOffset',
    }).formatToParts(now);

    const get = (type: Intl.DateTimeFormatPartTypes) =>
        parts.find((p) => p.type === type)?.value ?? '';

    const year = get('year');
    const month = get('month');
    const day = get('day');
    const weekday = get('weekday');
    const hour = Number(get('hour') || '0');
    const minute = Number(get('minute') || '0');
    const isoOffset = parseIsoOffset(get('timeZoneName'));

    return {
        etDate: `${year}-${month}-${day}`,
        weekday,
        hour,
        minute,
        totalMinutes: hour * 60 + minute,
        isoOffset,
    };
}

export function getEtDateString(now: Date = new Date()): string {
    return getEtClockParts(now).etDate;
}

function isObservedFixedHoliday(
    month: number,
    day: number,
    utcDay: number,
    targetMonth: number,
    targetDay: number,
    allowFridayObserved: boolean,
): boolean {
    if (month !== targetMonth) return false;
    if (day === targetDay) return true;
    if (day === targetDay + 1 && utcDay === 1) return true;
    return allowFridayObserved && day === targetDay - 1 && utcDay === 5;
}

function computeGoodFridayMonthDay(year: number): [number, number] {
    const a = year % 19;
    const b = Math.floor(year / 100);
    const c = year % 100;
    const d = Math.floor(b / 4);
    const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4);
    const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const easterMonth = Math.floor((h + l - 7 * m + 114) / 31);
    const easterDay = ((h + l - 7 * m + 114) % 31) + 1;
    const goodFriday = new Date(Date.UTC(year, easterMonth - 1, easterDay - 2));
    return [goodFriday.getUTCMonth() + 1, goodFriday.getUTCDate()];
}

/** Rule-based US equity market holiday check matching MarketSessionManager fallback. */
export function isKnownUsMarketHolidayEt(etDate: string): boolean {
    const [year, month, day] = etDate.split('-').map(Number);
    if (!year || !month || !day) return false;

    const utcDay = new Date(Date.UTC(year, month - 1, day)).getUTCDay(); // 0=Sun..6=Sat
    const [gfMonth, gfDay] = computeGoodFridayMonthDay(year);
    const fixedMatch =
        (month === gfMonth && day === gfDay) || // Good Friday
        isObservedFixedHoliday(month, day, utcDay, 1, 1, false) || // New Year's Day
        isObservedFixedHoliday(month, day, utcDay, 6, 19, true) || // Juneteenth
        isObservedFixedHoliday(month, day, utcDay, 7, 4, true) || // Independence Day
        isObservedFixedHoliday(month, day, utcDay, 12, 25, true); // Christmas Day

    if (fixedMatch) return true;

    const nthWeekdayMatch =
        (month === 1 && utcDay === 1 && day >= 15 && day <= 21) || // MLK Day
        (month === 2 && utcDay === 1 && day >= 15 && day <= 21) || // Presidents' Day
        (month === 5 && utcDay === 1 && day >= 25) || // Memorial Day
        (month === 9 && utcDay === 1 && day <= 7) || // Labor Day
        (month === 11 && utcDay === 4 && day >= 22 && day <= 28); // Thanksgiving Day

    return nthWeekdayMatch;
}

/** True during regular US equity market hours (Mon-Fri 09:30-16:00 ET, excluding US holidays). */
export function isRegularMarketHoursEt(now: Date = new Date()): boolean {
    const { etDate, weekday, totalMinutes } = getEtClockParts(now);
    if (weekday === 'Sat' || weekday === 'Sun') return false;
    if (isKnownUsMarketHolidayEt(etDate)) return false;
    return totalMinutes >= MARKET_OPEN_MINUTES_ET && totalMinutes < MARKET_CLOSE_MINUTES_ET;
}

/** True when Turbo can be activated (>= 5 minutes remaining before 16:00 ET close). */
export function canActivateTurboEt(now: Date = new Date()): boolean {
    const { etDate, weekday, totalMinutes } = getEtClockParts(now);
    if (weekday === 'Sat' || weekday === 'Sun') return false;
    if (isKnownUsMarketHolidayEt(etDate)) return false;
    return (
        totalMinutes >= MARKET_OPEN_MINUTES_ET && totalMinutes < TURBO_ACTIVATION_CUTOFF_MINUTES_ET
    );
}

/** Compute the Turbo expiration UTC ISO string: min(now + 1h, today 16:00:00 ET). */
export function computeTurboExpiryIso(now: Date = new Date()): string {
    const { etDate, isoOffset } = getEtClockParts(now);
    const marketCloseUtc = new Date(`${etDate}T16:00:00${isoOffset}`);
    const expiryMs = Math.min(now.getTime() + TURBO_DURATION_MS, marketCloseUtc.getTime());
    return new Date(expiryMs).toISOString();
}

export function isTurboActive(
    turboExpiresAt: string | null | undefined,
    now: Date = new Date(),
): boolean {
    if (!turboExpiresAt) return false;
    const expiryMs = Date.parse(turboExpiresAt);
    if (!Number.isFinite(expiryMs) || expiryMs <= now.getTime()) return false;
    return isRegularMarketHoursEt(now);
}

export function formatTurboRemainingLabel(
    turboExpiresAt: string | null | undefined,
    now: Date = new Date(),
): string | null {
    if (!isTurboActive(turboExpiresAt, now) || !turboExpiresAt) return null;
    const remainingMs = Date.parse(turboExpiresAt) - now.getTime();
    const mins = Math.max(1, Math.ceil(remainingMs / 60000));
    return `${mins}m left`;
}

export function getNextLiveSlotLabel(now: Date = new Date()): string {
    const { etDate, weekday, totalMinutes } = getEtClockParts(now);
    if (weekday === 'Sat' || weekday === 'Sun') return '09:30 ET Monday';
    if (isKnownUsMarketHolidayEt(etDate)) return '09:30 ET next trading day';

    const nextSlot = LIVE_SLOT_MINUTES_ET.find((s) => s > totalMinutes);
    if (nextSlot === undefined) {
        return weekday === 'Fri' ? '09:30 ET Monday' : '09:30 ET tomorrow';
    }

    const slotHour = Math.floor(nextSlot / 60);
    const slotMinute = nextSlot % 60;
    return `${slotHour.toString().padStart(2, '0')}:${slotMinute.toString().padStart(2, '0')} ET today`;
}
