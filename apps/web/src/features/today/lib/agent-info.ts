/**
 * Agent configuration and helpers for the Today feature.
 *
 * NOTE: This is internal to the Today feature slice.
 * Other features must not import from here.
 */

import { MODELS } from '~/config/models';

export const agentConfig: Record<
    string,
    { name: string; color: string; bgColor: string; emoji: string }
> = {
    [MODELS.OPENAI]: {
        name: 'OpenAI',
        color: 'text-emerald-500',
        bgColor: 'bg-emerald-500',
        emoji: '🟢',
    },
    [MODELS.ANTHROPIC]: {
        name: 'Claude',
        color: 'text-amber-600',
        bgColor: 'bg-amber-600',
        emoji: '🟠',
    },
    [MODELS.GEMINI]: {
        name: 'Gemini',
        color: 'text-blue-500',
        bgColor: 'bg-blue-500',
        emoji: '🔵',
    },
    [MODELS.DEEPSEEK]: {
        name: 'DeepSeek',
        color: 'text-purple-500',
        bgColor: 'bg-purple-500',
        emoji: '🟣',
    },
    [MODELS.MINIMAX]: {
        name: 'MiniMax',
        color: 'text-pink-500',
        bgColor: 'bg-pink-500',
        emoji: '🟡',
    },
    [MODELS.CONTRARIAN]: {
        name: 'Contrarian',
        color: 'text-rose-500',
        bgColor: 'bg-rose-500',
        emoji: '🔴',
    },
};

export function getAgentInfo(ownerId: string | null | undefined) {
    if (!ownerId)
        return { name: 'Unknown', color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' };
    const normalized = ownerId.toLowerCase().trim();
    if (!normalized)
        return { name: 'Unknown', color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' };
    // Exact match
    const exact = agentConfig[normalized];
    if (exact) return exact;
    // Fuzzy match: normalized string contains key or vice versa
    for (const [key, config] of Object.entries(agentConfig)) {
        const keyLower = key.toLowerCase();
        if (normalized.includes(keyLower) || keyLower.includes(normalized)) {
            return config;
        }
    }
    return { name: 'Unknown', color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' };
}
