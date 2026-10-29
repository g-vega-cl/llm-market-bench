import type { CandlestickBar } from '../components/SPYCandlestickChart';

export function filterLastBars(
    bars: CandlestickBar[] | null | undefined,
    maxBars = 60,
): CandlestickBar[] {
    if (!bars || !Array.isArray(bars)) return [];
    return bars.slice(-maxBars);
}

export function isRegularMarketHours(date = new Date()): boolean {
    const utcHours = date.getUTCHours();
    const utcMinutes = date.getUTCMinutes();
    const day = date.getUTCDay();

    // Weekend check (0 is Sunday, 6 is Saturday)
    if (day === 0 || day === 6) return false;

    // US regular market hours: 14:30 UTC to 21:00 UTC (9:30 AM to 4:00 PM ET)
    const totalMinutes = utcHours * 60 + utcMinutes;
    return totalMinutes >= 870 && totalMinutes < 1260;
}
