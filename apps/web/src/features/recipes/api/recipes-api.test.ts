import { describe, expect, it, vi } from 'vitest';
import { STARTER_RECIPES } from '../starter-templates';
import { assertSingleLlmStage } from './recipes-api';

vi.mock('~/lib/auth', () => ({
    getAuthServerClient: () => ({
        auth: {
            getUser: vi.fn(),
        },
    }),
}));

vi.mock('~/lib/db', () => ({
    getDbServerClient: () => ({}),
    getDbAdminClient: () => ({}),
}));

describe('assertSingleLlmStage', () => {
    const [stage] = STARTER_RECIPES[0].stages;

    it('accepts a strategy with exactly one LLM stage', () => {
        expect(() => assertSingleLlmStage(STARTER_RECIPES[0])).not.toThrow();
    });

    it('rejects a strategy that chains a second LLM stage', () => {
        const twoCalls = { ...STARTER_RECIPES[0], stages: [stage, { ...stage, id: 'stage-2' }] };
        expect(() => assertSingleLlmStage(twoCalls)).toThrow('exactly one LLM stage');
    });

    it('rejects a strategy with no LLM stage', () => {
        expect(() => assertSingleLlmStage({ ...STARTER_RECIPES[0], stages: [] })).toThrow(
            'exactly one LLM stage',
        );
    });
});
