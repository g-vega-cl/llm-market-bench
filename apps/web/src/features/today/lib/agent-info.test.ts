import { describe, expect, it } from 'vitest';
import { MODELS } from '~/config/models';
import { agentConfig, getAgentInfo } from './agent-info';

describe('getAgentInfo', () => {
    const unknownAgent = {
        name: 'Unknown',
        color: 'text-zinc-500',
        bgColor: 'bg-zinc-500',
        emoji: '⚪',
    };

    it('returns unknown for falsy inputs', () => {
        expect(getAgentInfo(null)).toEqual(unknownAgent);
        expect(getAgentInfo(undefined)).toEqual(unknownAgent);
        expect(getAgentInfo('')).toEqual(unknownAgent);
        expect(getAgentInfo('   ')).toEqual(unknownAgent); // Becomes empty string after trim() but not caught by !ownerId check directly, handled by fallback
    });

    it('performs exact matching using keys from MODELS', () => {
        expect(getAgentInfo(MODELS.OPENAI)).toEqual(agentConfig[MODELS.OPENAI]);
        // Case insensitive and trim
        expect(getAgentInfo(`  ${MODELS.ANTHROPIC.toUpperCase()}  `)).toEqual(
            agentConfig[MODELS.ANTHROPIC.toLowerCase()],
        );
    });

    it('performs matching for MiniMax', () => {
        expect(getAgentInfo(MODELS.MINIMAX).name).toEqual('MiniMax');
        expect(getAgentInfo('minimax').name).toEqual('MiniMax');
    });

    it('performs fuzzy matching when input contains the MODELS key', () => {
        // e.g. input is 'some-prefix-gpt-5.4-nano-suffix', key is 'gpt-5.4-nano'
        expect(getAgentInfo(`prefix-${MODELS.GEMINI}-suffix`)).toEqual(
            agentConfig[MODELS.GEMINI.toLowerCase()],
        );
    });

    it('performs fuzzy matching when MODELS key contains the input', () => {
        // e.g. input is 'gpt', key is 'gpt-5.4-nano'
        // Let's use 'gpt' which is part of 'gpt-5.4-nano'
        expect(getAgentInfo('gpt')).toEqual(agentConfig[MODELS.OPENAI.toLowerCase()]);

        // Let's use 'claude' which is part of 'claude-haiku-4-5'
        expect(getAgentInfo('claude')).toEqual(agentConfig[MODELS.ANTHROPIC.toLowerCase()]);
    });

    it('returns fallback for unrecognized inputs', () => {
        expect(getAgentInfo('completely-unknown-agent-id-123')).toEqual(unknownAgent);
    });
});
