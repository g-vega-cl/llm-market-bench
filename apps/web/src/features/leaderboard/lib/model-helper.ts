import { MODELS } from '~/config/models';

export const modelDisplayConfig: Record<
    string,
    {
        name: string;
        color: string;
        bgColor: string;
        emoji: string;
        gradient: 'electric' | 'success' | 'alert' | 'catalyst' | 'ai';
    }
> = {
    [MODELS.OPENAI]: {
        name: 'OpenAI (gpt-5.6-luna)',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500',
        emoji: '🟢',
        gradient: 'success',
    },
    [MODELS.ANTHROPIC]: {
        name: 'Claude (haiku-4-5)',
        color: 'text-amber-500',
        bgColor: 'bg-amber-500',
        emoji: '🟠',
        gradient: 'catalyst',
    },
    [MODELS.GEMINI]: {
        name: 'Gemini (3.5-flash-lite)',
        color: 'text-blue-400',
        bgColor: 'bg-blue-500',
        emoji: '🔵',
        gradient: 'electric',
    },
    [MODELS.DEEPSEEK]: {
        name: 'DeepSeek (v4-pro)',
        color: 'text-purple-400',
        bgColor: 'bg-purple-500',
        emoji: '🟣',
        gradient: 'ai',
    },
    [MODELS.MINIMAX]: {
        name: 'MiniMax (M3)',
        color: 'text-pink-400',
        bgColor: 'bg-pink-500',
        emoji: '🟡',
        gradient: 'catalyst',
    },
    [MODELS.CONTRARIAN]: {
        name: 'Contrarian Agent',
        color: 'text-rose-500',
        bgColor: 'bg-rose-500',
        emoji: '🔴',
        gradient: 'alert',
    },
};

export function getModelDisplayInfo(ownerId: string | null | undefined) {
    if (!ownerId) {
        return {
            name: 'Unknown',
            color: 'text-zinc-500',
            bgColor: 'bg-zinc-500',
            emoji: '🤖',
            gradient: 'electric' as const,
        };
    }
    const normalized = ownerId.toLowerCase().trim();
    for (const [key, config] of Object.entries(modelDisplayConfig)) {
        const keyLower = key.toLowerCase();
        if (normalized.includes(keyLower) || keyLower.includes(normalized)) {
            return config;
        }
    }
    // Fallback: clean up the ID into a display name
    const cleanName = ownerId.split('/').pop() || ownerId;
    const displayName = cleanName.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
    return {
        name: displayName,
        color: 'text-zinc-400',
        bgColor: 'bg-zinc-600',
        emoji: '🤖',
        gradient: 'electric' as const,
    };
}
