import { describe, expect, it } from 'vitest';
import {
    extractPercentage,
    parseScenarioPercentages,
    parseScenarios,
} from './parse-scenario-percentages';

describe('parseScenarioPercentages', () => {
    it('extracts basic percentage (40%)', () => {
        const result = parseScenarioPercentages('Market drops 40% in the bear case');
        expect(result).toHaveLength(1);
        expect(result[0].percentage).toBe('40%');
        expect(result[0].text).toBe('Market drops 40% in the bear case');
    });

    it('extracts percentage with space (40 %)', () => {
        const result = parseScenarioPercentages('Probability is 40 % for this outcome');
        expect(result[0].percentage).toBe('40%');
    });

    it('extracts percentage in parentheses (80%)', () => {
        const result = parseScenarioPercentages('high chance (80%) for bullish case');
        expect(result[0].percentage).toBe('80%');
    });

    it('returns null for lines without percentages', () => {
        const result = parseScenarioPercentages('Bullish scenario with strong momentum');
        expect(result[0].percentage).toBeNull();
    });

    it('handles multiple lines with mixed percentages', () => {
        const input =
            'Bull case: 70% probability\nBear case: 30% probability\nNeutral: steady growth';
        const result = parseScenarioPercentages(input);

        expect(result).toHaveLength(3);
        expect(result[0].percentage).toBe('70%');
        expect(result[1].percentage).toBe('30%');
        expect(result[2].percentage).toBeNull();
    });

    it('handles triple-digit percentages (100%)', () => {
        const result = parseScenarioPercentages('Full allocation at 100%');
        expect(result[0].percentage).toBe('100%');
    });

    it('handles empty string', () => {
        const result = parseScenarioPercentages('');
        expect(result).toHaveLength(1);
        expect(result[0].text).toBe('');
        expect(result[0].percentage).toBeNull();
    });

    it('extracts only first percentage if multiple on same line', () => {
        const result = parseScenarioPercentages('Range is 50% to 80% likely');
        expect(result[0].percentage).toBe('50%');
    });

    it('splits scenarios without newlines using Scenario A style pattern', () => {
        const input =
            'Scenario A: Bullish case (70%) - price goes up. Scenario B: Bearish case (30%) - price goes down.';
        const result = parseScenarioPercentages(input);

        expect(result).toHaveLength(2);
        expect(result[0].percentage).toBe('70%');
        expect(result[0].text).toBe('Scenario A: Bullish case (70%) - price goes up.');
        expect(result[1].percentage).toBe('30%');
        expect(result[1].text).toBe('Scenario B: Bearish case (30%) - price goes down.');
    });
});

describe('extractPercentage', () => {
    it('extracts percentage from text', () => {
        expect(extractPercentage('Scenario A (65%):')).toBe('65%');
    });

    it('extracts percentage with space', () => {
        expect(extractPercentage('65 % probability of market rally')).toBe('65%');
    });

    it('returns null when no percentage present', () => {
        expect(extractPercentage('Bullish market outlook')).toBeNull();
    });

    it('extracts percentage from inline text', () => {
        expect(extractPercentage('There is a 70% chance of rate hike')).toBe('70%');
    });

    it('handles single-digit percentages', () => {
        expect(extractPercentage('Only 5% chance of recession')).toBe('5%');
    });

    it('returns first percentage if multiple exist', () => {
        expect(extractPercentage('60% bull case, 40% bear case')).toBe('60%');
    });
});

describe('parseScenarios', () => {
    it('parses structured scenario analysis with outcomes and trading plans', () => {
        const input =
            'Scenario A: Bullish case (70%) - price goes up. Trading Plan: Buy SPY calls.';
        const result = parseScenarios(input);

        expect(result).toHaveLength(1);
        expect(result[0].rawHeader).toBe('Scenario A:');
        expect(result[0].cleanHeader).toBe('Scenario A:');
        expect(result[0].percentage).toBe('70%');
        expect(result[0].outcome).toBe('Bullish case (70%) - price goes up.');
        expect(result[0].tradingPlan).toBe('Buy SPY calls.');
    });

    it('cleans headers with inline probability patterns', () => {
        const input = 'Scenario A (85% probability): Rally continues.';
        const result = parseScenarios(input);

        expect(result).toHaveLength(1);
        expect(result[0].cleanHeader).toBe('Scenario A:');
        expect(result[0].percentage).toBe('85%');
        expect(result[0].outcome).toBe('Rally continues.');
    });

    it('falls back to raw text lines if scenario headers not found', () => {
        const input = 'General market outlook is positive.\nGrowth expected next quarter.';
        const result = parseScenarios(input);

        expect(result).toHaveLength(2);
        expect(result[0].outcome).toBe('General market outlook is positive.');
        expect(result[0].percentage).toBeNull();
        expect(result[0].tradingPlan).toBeNull();
        expect(result[1].outcome).toBe('Growth expected next quarter.');
    });
});
