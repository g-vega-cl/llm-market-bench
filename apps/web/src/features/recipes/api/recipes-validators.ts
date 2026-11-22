import recipeNamingJson from '../../../../../../packages/config/recipe-naming.json';
import type { StrategyStage } from '../types';

const PREV_OUTPUT_PLACEHOLDER = '{{prev_output}}';

interface RecipeNaming {
    defaultName: string;
    nameMaxLength: number;
}

// Shared with apps/engine/recipes/push_schema.py so the two sides cannot drift.
export const { defaultName: DEFAULT_RECIPE_NAME, nameMaxLength: RECIPE_NAME_MAX_LENGTH } =
    recipeNamingJson as RecipeNaming;

/**
 * Single source of truth for the persisted recipe name. The DB column is
 * `TEXT NOT NULL`, so a blank or missing name must never reach the insert.
 */
export function normalizeRecipeName(name: string | null | undefined): string {
    return name?.trim().slice(0, RECIPE_NAME_MAX_LENGTH) || DEFAULT_RECIPE_NAME;
}

export function assertSingleLlmStage(recipe: { stages: readonly StrategyStage[] }): void {
    if (!Array.isArray(recipe.stages) || recipe.stages.length !== 1) {
        throw new Error('Invalid strategy: must contain exactly one LLM stage');
    }
}

export function assertNoPrevOutputPlaceholder(recipe: { stages: readonly StrategyStage[] }): void {
    for (const stage of recipe.stages ?? []) {
        for (const block of stage.blocks ?? []) {
            if (block.type === 'prompt' && block.text.includes(PREV_OUTPUT_PLACEHOLDER)) {
                throw new Error(
                    'Invalid strategy: prev_output is not available in a single-stage strategy',
                );
            }
        }
    }
}

/**
 * Canonical rule-metric vocabulary. `metric` is a free-form string in the schema,
 * so without this gate a typo produces a rule the model can never satisfy — the
 * indicator simply is not in any curated tool's output, and the gate is silently
 * ignored at run time instead of failing at build time.
 */
export const RULE_METRIC_LABELS = [
    'RSI',
    'MACD',
    'RVOL',
    'Price vs VWAP',
    'price_52w_pct',
    'P/E',
    'FCF',
    'ROE',
    'market_cap',
    'beta',
] as const;

export type RuleMetricLabel = (typeof RULE_METRIC_LABELS)[number];

export function assertKnownRuleMetrics(recipe: { stages: readonly StrategyStage[] }): void {
    const allowed = new Set<string>(RULE_METRIC_LABELS);
    for (const stage of recipe.stages ?? []) {
        for (const block of stage.blocks ?? []) {
            if (block.type !== 'technicals') continue;
            for (const rule of block.rules) {
                if (!allowed.has(rule.metric)) {
                    throw new Error(`Invalid strategy: unknown rule metric "${rule.metric}"`);
                }
            }
        }
    }
}
