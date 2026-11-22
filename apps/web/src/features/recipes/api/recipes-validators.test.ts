import { describe, expect, it } from 'vitest';
import recipeNamingJson from '../../../../../../packages/config/recipe-naming.json';
import type { PushStrategy, StrategyBlock } from '../types';
import {
    assertKnownRuleMetrics,
    assertNoPrevOutputPlaceholder,
    DEFAULT_RECIPE_NAME,
    normalizeRecipeName,
    RECIPE_NAME_MAX_LENGTH,
    RULE_METRIC_LABELS,
} from './recipes-validators';

function strategyWithRules(metrics: string[]): PushStrategy {
    const blocks: StrategyBlock[] = [
        { id: 'p', type: 'prompt', text: 'Test prompt.' },
        {
            id: 't',
            type: 'technicals',
            rules: metrics.map((metric, index) => ({
                id: `r${String(index)}`,
                metric,
                operator: '>',
                target: '1',
            })),
        },
        { id: 'o', type: 'output_format' },
    ];
    return {
        version: '2.0-push',
        name: 'Test',
        description: 'Test',
        cadence: '3h',
        stages: [{ id: 'stage-1', selected_tools: ['get_technical_indicators'], blocks }],
    };
}

describe('normalizeRecipeName', () => {
    it('keeps the shared naming contract in sync with packages/config', () => {
        expect(DEFAULT_RECIPE_NAME).toBe(recipeNamingJson.defaultName);
        expect(RECIPE_NAME_MAX_LENGTH).toBe(recipeNamingJson.nameMaxLength);
    });

    it('trims surrounding whitespace', () => {
        expect(normalizeRecipeName('  Momentum Rotation  ')).toBe('Momentum Rotation');
    });

    it('falls back to the default for blank, null, and undefined names', () => {
        expect(normalizeRecipeName('')).toBe(DEFAULT_RECIPE_NAME);
        expect(normalizeRecipeName('   ')).toBe(DEFAULT_RECIPE_NAME);
        expect(normalizeRecipeName(null)).toBe(DEFAULT_RECIPE_NAME);
        expect(normalizeRecipeName(undefined)).toBe(DEFAULT_RECIPE_NAME);
    });

    it('caps the name at the shared maximum length', () => {
        expect(normalizeRecipeName('x'.repeat(RECIPE_NAME_MAX_LENGTH + 20))).toHaveLength(
            RECIPE_NAME_MAX_LENGTH,
        );
    });
});

describe('assertKnownRuleMetrics', () => {
    it('accepts every sanctioned metric label', () => {
        expect(() =>
            assertKnownRuleMetrics(strategyWithRules([...RULE_METRIC_LABELS])),
        ).not.toThrow();
    });

    it('rejects a metric no curated tool returns, instead of letting the gate be silently ignored', () => {
        // `metric` is a free string in the schema: a typo or a ghost indicator would
        // otherwise compile into a bot whose rule the model cannot satisfy.
        expect(() => assertKnownRuleMetrics(strategyWithRules(['FCF_yield']))).toThrow(
            'Invalid strategy: unknown rule metric "FCF_yield"',
        );
        expect(() => assertKnownRuleMetrics(strategyWithRules(['RSI', 'EV_EBITDA']))).toThrow(
            'unknown rule metric "EV_EBITDA"',
        );
    });

    it('ignores stages without a technicals block', () => {
        const strategy: PushStrategy = {
            version: '2.0-push',
            name: 'Prompt only',
            description: 'No rules',
            cadence: '3h',
            stages: [
                {
                    id: 'stage-1',
                    selected_tools: ['get_stock_quote'],
                    blocks: [
                        { id: 'p', type: 'prompt', text: 'Hello.' },
                        { id: 'o', type: 'output_format' },
                    ],
                },
            ],
        };
        expect(() => assertKnownRuleMetrics(strategy)).not.toThrow();
    });
});

describe('assertNoPrevOutputPlaceholder', () => {
    it('rejects the placeholder in a single-stage recipe', () => {
        const strategy = strategyWithRules(['RSI']);
        strategy.stages[0].blocks[0] = {
            id: 'p',
            type: 'prompt',
            text: 'Continue from {{prev_output}}.',
        };
        expect(() => assertNoPrevOutputPlaceholder(strategy)).toThrow('prev_output');
    });
});
