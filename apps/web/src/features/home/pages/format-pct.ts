/** Signed percentage with a fixed precision; an unknown value renders as a dash, never 0%. */
export function formatPct(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return '—';
    const rounded = Math.abs(value) < 0.005 ? 0 : value;
    return `${rounded > 0 ? '+' : ''}${rounded.toFixed(2)}%`;
}
