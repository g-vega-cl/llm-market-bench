/**
 * Display labels for retired model ids that still exist in stored rows.
 *
 * Model strings are immutable historical keys: `daily_predictions.model_name`,
 * `sector_predictions.model_name`, `earnings_predictions.model_name` and
 * `portfolio_performance` joins all keep whatever id was live when the row was
 * written. Renaming a slot must not relabel or hide those rows, so display
 * helpers resolve a retired id to the name it actually ran under.
 *
 * Routing always uses `MODELS` from `~/config/models`; this map is presentation
 * only and must never be consulted when calling a provider.
 */
const LEGACY_MODEL_LABELS: Readonly<Record<string, string>> = {
    'gpt-5.6-luna': 'GPT-5.6 Luna',
    'deepseek-v4-flash': 'DeepSeek Flash',
    'minimax-m3': 'MiniMax M3',
};

/** Returns the historical display label for a retired model id, if any. */
export function legacyModelLabel(modelName: string | null | undefined): string | undefined {
    if (!modelName) return undefined;
    return LEGACY_MODEL_LABELS[modelName.trim().toLowerCase()];
}

/** True when the id is a retired model that still backs historical rows. */
export function isLegacyModelId(modelName: string | null | undefined): boolean {
    return legacyModelLabel(modelName) !== undefined;
}
