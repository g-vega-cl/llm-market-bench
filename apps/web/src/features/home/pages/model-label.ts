/**
 * Public model label. OpenRouter free-tier ids carry a `:free` suffix
 * (`tencent/hy4-flash:free`); the suffix is stripped for display only — the
 * stored value keeps the truth, the card just names the model.
 */
export function modelLabel(model: string | null | undefined): string | null {
    if (typeof model !== 'string') return null;
    const trimmed = model.trim();
    if (!trimmed) return null;
    return trimmed.replace(/:free$/i, '');
}
