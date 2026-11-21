/**
 * Dynamic atmosphere phase resolution for Benchify living-scene stages.
 *
 * Defaults to the US Eastern market session clock (`America/New_York`) so
 * atmosphere phases stay domain-native and deterministic across SSR and
 * client hydration when given a shared timestamp.
 */

export const ATMOSPHERE_PHASES = ['dawn', 'daylight', 'dusk', 'after-hours'] as const;

export type AtmospherePhase = (typeof ATMOSPHERE_PHASES)[number];

export type AtmosphereClockMode = 'market-et' | 'local';

const ET_TIME_FORMATTER = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
});

function getEasternMinutes(date: Date): number {
    const parts = ET_TIME_FORMATTER.formatToParts(date);
    const rawHour = Number(parts.find((p) => p.type === 'hour')?.value ?? '0');
    const minute = Number(parts.find((p) => p.type === 'minute')?.value ?? '0');
    const hour = rawHour % 24;
    return hour * 60 + minute;
}

interface PhaseThresholds {
    dawnStart: number;
    daylightStart: number;
    duskStart: number;
    afterHoursStart: number;
}

const MARKET_ET_THRESHOLDS: PhaseThresholds = {
    dawnStart: 240, // 04:00 ET
    daylightStart: 570, // 09:30 ET
    duskStart: 960, // 16:00 ET
    afterHoursStart: 1200, // 20:00 ET
};

const LOCAL_THRESHOLDS: PhaseThresholds = {
    dawnStart: 300, // 05:00
    daylightStart: 540, // 09:00
    duskStart: 1020, // 17:00
    afterHoursStart: 1260, // 21:00
};

function resolveByThresholds(minutes: number, t: PhaseThresholds): AtmospherePhase {
    if (minutes >= t.dawnStart && minutes < t.daylightStart) return 'dawn';
    if (minutes >= t.daylightStart && minutes < t.duskStart) return 'daylight';
    if (minutes >= t.duskStart && minutes < t.afterHoursStart) return 'dusk';
    return 'after-hours';
}

/**
 * Resolves the Matcha & Cedar atmospheric sky phase for a given timestamp.
 *
 * - `market-et` (default, US Eastern):
 *   - `dawn`:        04:00–09:29 ET (pre-market)
 *   - `daylight`:    09:30–15:59 ET (regular session)
 *   - `dusk`:        16:00–19:59 ET (close & golden-hour twilight)
 *   - `after-hours`: 20:00–03:59 ET (overnight)
 *
 * - `local` (visitor timezone):
 *   - `dawn`:        05:00–08:59
 *   - `daylight`:    09:00–16:59
 *   - `dusk`:        17:00–20:59
 *   - `after-hours`: 21:00–04:59
 */
export function resolveAtmospherePhase(
    date: Date = new Date(),
    mode: AtmosphereClockMode = 'market-et',
): AtmospherePhase {
    if (Number.isNaN(date.getTime())) return 'dusk';

    if (mode === 'local') {
        const minutes = date.getHours() * 60 + date.getMinutes();
        return resolveByThresholds(minutes, LOCAL_THRESHOLDS);
    }

    return resolveByThresholds(getEasternMinutes(date), MARKET_ET_THRESHOLDS);
}
