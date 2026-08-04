import { beforeEach, describe, expect, it, vi } from 'vitest';

// We mock it for the top-level block
vi.mock('@repo/config/models.json', () => ({
    default: {
        OPENAI_MODEL: 'gpt-5.4-nano',
        ANTHROPIC_MODEL: 'claude-haiku-4-5',
        GEMINI_MODEL: 'gemini-3.5-flash-lite',
        DEEPSEEK_MODEL: 'deepseek-v4-pro',
        AUTORESEARCH_EXPERIMENT_OWNER_IDS: ['gemini-3.5-flash-lite', 'deepseek-v4-pro'],
    },
}));

describe('Portfolio Config Utils', () => {
    let configModule: typeof import('./config');

    beforeEach(async () => {
        vi.resetModules();
        vi.doMock('@repo/config/models.json', () => ({
            default: {
                OPENAI_MODEL: 'gpt-5.4-nano',
                ANTHROPIC_MODEL: 'claude-haiku-4-5',
                GEMINI_MODEL: 'gemini-3.5-flash-lite',
                DEEPSEEK_MODEL: 'deepseek-v4-pro',
                AUTORESEARCH_EXPERIMENT_OWNER_IDS: ['gemini-3.5-flash-lite', 'deepseek-v4-pro'],
            },
        }));
        // Dynamic import to get fresh module state for caching tests
        configModule = await import('./config');
    });

    describe('normalizeOwnerId', () => {
        it('normalizes various formats', () => {
            expect(configModule.normalizeOwnerId('Gemini 3.5 Flash-Lite')).toBe(
                'gemini-3.5-flash-lite',
            );
            expect(configModule.normalizeOwnerId('DeepSeek_V4_Pro')).toBe('deepseek-v4-pro');
            expect(configModule.normalizeOwnerId('  GPT-5.4 Nano  ')).toBe('gpt-5.4-nano');
            expect(configModule.normalizeOwnerId('---TEST_model---')).toBe('test-model');
            expect(configModule.normalizeOwnerId('model-with  spaces_and_dashes')).toBe(
                'model-with-spaces-and-dashes',
            );
        });

        it('returns empty string for null', () => {
            expect(configModule.normalizeOwnerId(null)).toBe('');
        });

        it('returns empty string for empty string', () => {
            expect(configModule.normalizeOwnerId('')).toBe('');
        });
    });

    describe('isAutoresearchPortfolio', () => {
        it('identifies autoresearch portfolios correctly', () => {
            expect(configModule.isAutoresearchPortfolio('gemini-3.5-flash-lite')).toBe(true);
            expect(configModule.isAutoresearchPortfolio('deepseek-v4-pro')).toBe(true);
            expect(configModule.isAutoresearchPortfolio('GPT-5.4-nano')).toBe(false);
            expect(configModule.isAutoresearchPortfolio('claude-haiku-4-5')).toBe(false);
        });

        it('handles normalization during check', () => {
            expect(configModule.isAutoresearchPortfolio('Gemini 3.5 Flash-Lite')).toBe(true);
            expect(configModule.isAutoresearchPortfolio('DeepSeek V4 Pro')).toBe(true);
        });

        it('returns false for null or empty ownerId', () => {
            expect(configModule.isAutoresearchPortfolio(null)).toBe(false);
            expect(configModule.isAutoresearchPortfolio('')).toBe(false);
        });
    });

    describe('getActiveOwnerIds', () => {
        it('filters out non-string values (like the experiment array)', () => {
            const activeIds = configModule.getActiveOwnerIds();
            expect(activeIds).toContain('gpt-5.4-nano');
            expect(activeIds).toContain('claude-haiku-4-5');
            expect(activeIds).toContain('gemini-3.5-flash-lite');
            expect(activeIds).toContain('deepseek-v4-pro');
            expect(activeIds.length).toBe(4);
        });

        it('returns cached values on subsequent calls', () => {
            const firstCall = configModule.getActiveOwnerIds();
            const secondCall = configModule.getActiveOwnerIds();
            expect(firstCall).toBe(secondCall); // Reference equality
        });
    });

    describe('getAutoresearchOwnerIds', () => {
        it('returns array of normalized autoresearch ids', () => {
            const ids = configModule.getAutoresearchOwnerIds();
            expect(ids).toContain('gemini-3.5-flash-lite');
            expect(ids).toContain('deepseek-v4-pro');
            expect(ids.length).toBe(2);
        });

        it('returns cached values on subsequent calls', () => {
            const firstCall = configModule.getAutoresearchOwnerIds();
            const secondCall = configModule.getAutoresearchOwnerIds();
            expect(firstCall).toBe(secondCall); // Reference equality
        });

        it('handles missing or undefined AUTORESEARCH_EXPERIMENT_OWNER_IDS by returning empty array', async () => {
            vi.resetModules();
            vi.doMock('@repo/config/models.json', () => ({
                default: {
                    AUTORESEARCH_EXPERIMENT_OWNER_IDS: null,
                },
            }));
            const freshModule = await import('./config');
            const result = freshModule.getAutoresearchOwnerIds();
            expect(result).toEqual([]);
        });
    });

    describe('getPortfolioTrack', () => {
        it('resolves track for portfolios in AUTORESEARCH_TRACKS', async () => {
            vi.resetModules();
            vi.doMock('@repo/config/models.json', () => ({
                default: {
                    AUTORESEARCH_EXPERIMENT_OWNER_IDS: ['gemini-3.5-flash-lite'],
                    AUTORESEARCH_TRACKS: {
                        track_default: ['gemini-3.5-flash-lite'],
                        track_claude: ['claude-haiku-4-5'],
                    },
                },
            }));
            const freshModule = await import('./config');
            expect(freshModule.getPortfolioTrack('gemini-3.5-flash-lite')).toEqual({
                trackId: 'track_default',
                trackLabel: 'Default Track',
            });
            expect(freshModule.getPortfolioTrack('claude-haiku-4-5')).toEqual({
                trackId: 'track_claude',
                trackLabel: 'Claude',
            });
            expect(freshModule.getPortfolioTrack('gpt-5.4-nano')).toBeNull();
        });
    });

    describe('hasVerifier', () => {
        it('identifies if a portfolio uses a verifier correctly', () => {
            expect(configModule.hasVerifier('gemini-3.5-flash-lite')).toBe(true);
            expect(configModule.hasVerifier('deepseek-v4-pro')).toBe(true);
            expect(configModule.hasVerifier('MiniMax-M3')).toBe(false);
            expect(configModule.hasVerifier('minimax-m3')).toBe(false);
        });

        it('returns false for null or empty ownerId', () => {
            expect(configModule.hasVerifier(null)).toBe(false);
            expect(configModule.hasVerifier('')).toBe(false);
        });
    });
});

describe('Portfolio Config Utils Error Handling', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('getActiveOwnerIds handles errors gracefully', async () => {
        vi.doMock('@repo/config/models.json', () => ({
            default: null, // Object.values(null) throws TypeError
        }));

        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const { getActiveOwnerIds } = await import('./config');

        const result = getActiveOwnerIds();

        expect(result).toEqual([]);
        expect(consoleSpy).toHaveBeenCalledWith(
            'Failed to load models.json:',
            expect.any(TypeError),
        );
        consoleSpy.mockRestore();
    });

    it('getAutoresearchOwnerIds handles errors gracefully', async () => {
        vi.doMock('@repo/config/models.json', () => ({
            default: new Proxy(
                {},
                {
                    get() {
                        throw new Error('Mock error for autoresearch config');
                    },
                },
            ),
        }));

        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const { getAutoresearchOwnerIds } = await import('./config');

        const result = getAutoresearchOwnerIds();

        expect(result).toEqual([]);
        expect(consoleSpy).toHaveBeenCalledWith(
            'Failed to load autoresearch config:',
            expect.any(Error),
        );
        consoleSpy.mockRestore();
    });

    it('getAutoresearchOwnerIds covers fallback empty array return when mapped somehow null', async () => {
        // Here we mock the behavior of line 54 where cachedAutoresearchOwnerIds could evaluate to something falsy like null after the assignment
        // Actually, since it's `const ids = ... as string[]; cachedAutoresearchOwnerIds = (ids || []).map(...)`,
        // The array `.map` method will always return an array (truthy).
        // However, we can mock `AUTORESEARCH_EXPERIMENT_OWNER_IDS` to an object that has a custom `map` method returning `undefined`.
        vi.doMock('@repo/config/models.json', () => ({
            default: {
                AUTORESEARCH_EXPERIMENT_OWNER_IDS: {
                    map: () => undefined,
                },
            },
        }));

        const { getAutoresearchOwnerIds } = await import('./config');

        const result = getAutoresearchOwnerIds();
        expect(result).toEqual([]);
    });
});
