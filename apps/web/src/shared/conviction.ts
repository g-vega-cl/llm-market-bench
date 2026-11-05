/**
 * Conviction score presentation helpers.
 *
 * These mirror the normalisation in `apps/engine/core/conviction_scoring.py`,
 * which is the single source of truth for scoring. The engine persists the raw
 * per-prediction log-score in `conviction_score`; this module only aggregates
 * those stored values for display.
 */

export const CONVICTION_NEUTRAL_SCORE = 50;
const NORM_SCALE = 50;

interface ConvictionScored {
    conviction_score?: number | null;
}

/**
 * Map mean conviction points onto the 0-100 composite scale centred at 50.
 * A coin flip (0 points) maps to exactly 50.
 */
export function normalizeConvictionPoints(meanCp: number): number {
    if (!Number.isFinite(meanCp)) return CONVICTION_NEUTRAL_SCORE;
    return 50 + 50 * Math.tanh(meanCp / NORM_SCALE);
}

/** Mean stored conviction points, or null when no row has been scored. */
export function meanConvictionPoints(predictions: ConvictionScored[]): number | null {
    const values = predictions
        .map((p) => p.conviction_score)
        .filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
    if (values.length === 0) return null;
    return values.reduce((a, b) => a + b, 0) / values.length;
}

/** Normalised 0-100 conviction score, defaulting to neutral for unscored sets. */
export function resolveConvictionScore(predictions: ConvictionScored[]): number {
    const mean = meanConvictionPoints(predictions);
    if (mean === null) return CONVICTION_NEUTRAL_SCORE;
    return normalizeConvictionPoints(mean);
}
