/**
 * NYSE market-hours utility.
 *
 * Models the NYSE regular trading session (09:30–16:00 America/New_York,
 * Monday through Friday) in a way that's correct for both EST (UTC-5) and
 * EDT (UTC-4). Pre-market and after-hours are intentionally not modeled.
 *
 * Why ET-relative instead of static UTC hours
 * ------------------------------------------
 * The naïve check `currentHour >= 13:30 && currentHour < 20` (UTC) is only
 * correct during EDT. During EST the open window shifts to 14:30–21:00 UTC,
 * which causes the function to report "open" at 8:30 AM ET and "closed" at
 * 3:00 PM ET for ~4 months of the year. The IANA `America/New_York` zone
 * already encodes the DST transition rules, so we delegate to the runtime
 * to give us the correct local hour for any instant in history or future.
 *
 * Known limitations
 * -----------------
 * - NYSE market holidays (10/year) are not modeled: the function reports
 *   "OPEN" on July 4th, Thanksgiving, etc. Adding a holiday calendar is
 *   tracked as a follow-up.
 * - Pre-market (04:00–09:30 ET) and after-hours (16:00–20:00 ET) are not
 *   modeled.
 */

const ET_TIMEZONE = 'America/New_York';

const WEEKDAY_FROM_SHORT: Record<string, number> = {
    Sun: 0,
    Mon: 1,
    Tue: 2,
    Wed: 3,
    Thu: 4,
    Fri: 5,
    Sat: 6,
};

export interface EasternParts {
    weekday: number;
    hour: number;
    minute: number;
}

/**
 * Decompose an instant into its calendar components as observed in
 * America/New_York. `weekday` follows JS Date convention: 0 = Sunday,
 * 6 = Saturday. `hour` is 0–23; `minute` is 0–59.
 */
export function getEasternParts(now: Date): EasternParts {
    const fmt = new Intl.DateTimeFormat('en-US', {
        timeZone: ET_TIMEZONE,
        weekday: 'short',
        hour: 'numeric',
        minute: '2-digit',
        hour12: false,
    });
    const lookup: Record<string, string> = {};
    for (const part of fmt.formatToParts(now)) {
        lookup[part.type] = part.value;
    }
    return {
        weekday: WEEKDAY_FROM_SHORT[lookup.weekday ?? 'Mon'] ?? 0,
        hour: parseInt(lookup.hour ?? '0', 10),
        minute: parseInt(lookup.minute ?? '0', 10),
    };
}

/**
 * True if the NYSE regular session is open at the given instant.
 *
 * @param now - The instant to check. Caller is responsible for timezone-
 *              neutral passing (this function treats `now` as an absolute
 *              UTC instant and converts internally).
 */
export function isNyseOpenAt(now: Date): boolean {
    const { weekday, hour, minute } = getEasternParts(now);
    const isWeekday = weekday >= 1 && weekday <= 5;
    const afterOpen = hour > 9 || (hour === 9 && minute >= 30);
    const beforeClose = hour < 16;
    return isWeekday && afterOpen && beforeClose;
}
