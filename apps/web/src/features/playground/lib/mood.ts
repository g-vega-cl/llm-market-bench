/**
 * Market feeling, as one tagged union. Freshness and values cannot disagree,
 * because a stale reading carries no direction to disagree with.
 */
export type MoodDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL';
export type MoodTone = 'bullish' | 'bearish' | 'neutral';

export type Mood =
    | {
          kind: 'fresh';
          direction: MoodDirection;
          confidence: number;
          label: string;
          asOf: string;
      }
    | { kind: 'stale'; direction: 'NEUTRAL'; asOf: string; reason: 'quiet' }
    | { kind: 'unknown'; reason: 'unavailable' };

const DIRECTIONS = new Set(['BULLISH', 'BEARISH', 'NEUTRAL']);
/** A reading older than this cannot describe "now" — weekends alone are ~64 h. */
const MAX_FRESH_HOURS = 36;

export function normalizeMood(value: unknown, now: number = Date.now()): Mood {
    if (!value || typeof value !== 'object') return { kind: 'unknown', reason: 'unavailable' };
    const row = value as Record<string, unknown>;
    const direction = String(row.market_direction ?? row.sentiment ?? '')
        .trim()
        .toUpperCase();
    if (!DIRECTIONS.has(direction)) return { kind: 'unknown', reason: 'unavailable' };

    const asOfRaw = row.created_at ?? row.last_analyzed;
    const asOf = typeof asOfRaw === 'string' ? asOfRaw : '';
    const parsed = asOf ? Date.parse(asOf) : Number.NaN;
    if (!Number.isFinite(parsed))
        return { kind: 'stale', direction: 'NEUTRAL', asOf, reason: 'quiet' };

    const ageHours = (now - parsed) / 3_600_000;
    if (!Number.isFinite(ageHours) || ageHours > MAX_FRESH_HOURS) {
        return { kind: 'stale', direction: 'NEUTRAL', asOf, reason: 'quiet' };
    }

    const confidence = Number(row.confidence_score ?? row.confidence);
    return {
        kind: 'fresh',
        direction: direction as MoodDirection,
        confidence: Number.isFinite(confidence) ? confidence : 0,
        label: typeof row.sentiment_label === 'string' ? row.sentiment_label : '',
        asOf,
    };
}

export function moodTone(mood: Mood): MoodTone {
    if (mood.kind !== 'fresh') return 'neutral';
    if (mood.direction === 'BULLISH') return 'bullish';
    if (mood.direction === 'BEARISH') return 'bearish';
    return 'neutral';
}

/** Text always carries the fact; the world only echoes it in colour. */
export function moodSentence(mood: Mood): string {
    if (mood.kind === 'unknown') return 'Market mood unavailable right now.';
    if (mood.kind === 'stale') return 'Market mood is quiet — last reading is older than a day.';
    const confidence = mood.confidence > 0 ? `, ${Math.round(mood.confidence)}% confidence` : '';
    const label = mood.label ? ` — ${mood.label}` : '';
    return `Desk reads ${mood.direction.toLowerCase()}${confidence}${label}.`;
}

export function moodAsOf(mood: Mood): string | null {
    if (mood.kind === 'unknown' || !mood.asOf) return null;
    const parsed = Date.parse(mood.asOf);
    if (!Number.isFinite(parsed)) return null;
    return new Date(parsed).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'America/New_York',
    });
}
