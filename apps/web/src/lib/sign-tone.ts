import type { TableCellTone } from '@llm-market-bench/ui-design-system';

/**
 * Signed metric → semantic `TableCell` tone.
 *
 * Unknown values (null, undefined, blank strings, non-finite numbers) return
 * `undefined`, so the cell keeps the neutral ink default instead of being
 * painted as a gain — absence means unknown, not zero. A flat zero is muted
 * rather than green: a 0.00% move is not a gain.
 */
export function signTone(value: number | string | null | undefined): TableCellTone | undefined {
    if (value === null || value === undefined) return undefined;
    if (typeof value === 'string' && value.trim() === '') return undefined;
    const numeric = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(numeric)) return undefined;
    if (numeric > 0) return 'positive';
    if (numeric < 0) return 'negative';
    return 'muted';
}

/** Same mapping, but an unreadable value reads as muted instead of neutral ink. */
export function signToneOrMuted(value: number | string | null | undefined): TableCellTone {
    return signTone(value) ?? 'muted';
}
