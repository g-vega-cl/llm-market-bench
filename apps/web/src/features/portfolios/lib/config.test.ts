import { describe, expect, it, vi } from 'vitest';
import { getActiveOwnerIds, isAutoresearchPortfolio, normalizeOwnerId } from './config';

// Mock modelsConfig
vi.mock('@repo/config/models.json', () => ({
    default: {
        OPENAI_MODEL: 'gpt-5.4-nano',
        ANTHROPIC_MODEL: 'claude-haiku-4-5',
        GEMINI_MODEL: 'gemini-3.1-flash-lite',
        DEEPSEEK_MODEL: 'deepseek-v4-pro',
        AUTORESEARCH_EXPERIMENT_OWNER_IDS: ['gemini-3.1-flash-lite', 'deepseek-v4-pro'],
    },
}));

describe('Portfolio Config Utils', () => {
    describe('normalizeOwnerId', () => {
        it('normalizes various formats', () => {
            expect(normalizeOwnerId('Gemini 3.1 Flash-Lite')).toBe('gemini-3.1-flash-lite');
            expect(normalizeOwnerId('DeepSeek_V4_Pro')).toBe('deepseek-v4-pro');
            expect(normalizeOwnerId('  GPT-5.4 Nano  ')).toBe('gpt-5.4-nano');
        });
    });

    describe('isAutoresearchPortfolio', () => {
        it('identifies autoresearch portfolios correctly', () => {
            expect(isAutoresearchPortfolio('gemini-3.1-flash-lite')).toBe(true);
            expect(isAutoresearchPortfolio('deepseek-v4-pro')).toBe(true);
            expect(isAutoresearchPortfolio('GPT-5.4-nano')).toBe(false);
            expect(isAutoresearchPortfolio('claude-haiku-4-5')).toBe(false);
        });

        it('handles normalization during check', () => {
            expect(isAutoresearchPortfolio('Gemini 3.1 Flash-Lite')).toBe(true);
            expect(isAutoresearchPortfolio('DeepSeek V4 Pro')).toBe(true);
        });

        it('returns false for null or empty ownerId', () => {
            expect(isAutoresearchPortfolio(null)).toBe(false);
            expect(isAutoresearchPortfolio('')).toBe(false);
        });
    });

    describe('getActiveOwnerIds', () => {
        it('filters out non-string values (like the experiment array)', () => {
            const activeIds = getActiveOwnerIds();
            expect(activeIds).toContain('gpt-5.4-nano');
            expect(activeIds).toContain('claude-haiku-4-5');
            expect(activeIds).toContain('gemini-3.1-flash-lite');
            expect(activeIds).toContain('deepseek-v4-pro');
            // It should NOT contain the string representation of the array or anything else
            expect(activeIds.length).toBe(4);
        });
    });
});
