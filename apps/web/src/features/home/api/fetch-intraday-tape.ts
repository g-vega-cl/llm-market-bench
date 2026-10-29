import type { CandlestickBar } from '../components/SPYCandlestickChart';

export function generateFallbackIntradayBars(count = 120, basePrice = 582.5): CandlestickBar[] {
    const bars: CandlestickBar[] = [];
    const now = new Date();
    let currentPrice = basePrice;

    for (let i = count; i >= 1; i--) {
        const barTime = new Date(now.getTime() - i * 60 * 1000);
        // Deterministic pseudo-random variation based on minute index
        const delta = Math.sin(i * 0.15) * 0.35 + Math.cos(i * 0.08) * 0.2;
        const open = currentPrice;
        const close = Number((open + delta).toFixed(2));
        const high = Number((Math.max(open, close) + 0.25).toFixed(2));
        const low = Number((Math.min(open, close) - 0.2).toFixed(2));
        const volume = Math.floor(10000 + Math.abs(Math.sin(i)) * 25000);

        bars.push({
            time: barTime.toISOString(),
            open,
            high,
            low,
            close,
            volume,
        });

        currentPrice = close;
    }

    return bars;
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
