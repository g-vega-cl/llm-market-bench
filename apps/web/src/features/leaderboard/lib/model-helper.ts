import type { LeaderboardEntityType, LLMLeaderboardRow } from '@llm-market-bench/database';
import { legacyModelLabel } from '~/config/model-aliases';
import { MODELS } from '~/config/models';
import { getSystemPortfolioSubtitle, isSystemPortfolio } from '~/features/portfolios/lib/config';

export const modelDisplayConfig: Record<
    string,
    {
        name: string;
        color: string;
        bgColor: string;
        gradient: 'electric' | 'success' | 'alert' | 'catalyst' | 'ai';
    }
> = {
    [MODELS.OPENAI]: {
        name: 'OpenAI (gpt-6-luna)',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500',
        gradient: 'success',
    },
    [MODELS.ANTHROPIC]: {
        name: 'Claude (haiku-5-5)',
        color: 'text-amber-500',
        bgColor: 'bg-amber-500',
        gradient: 'catalyst',
    },
    [MODELS.GEMINI]: {
        name: 'Gemini (3.5-flash-lite)',
        color: 'text-blue-400',
        bgColor: 'bg-blue-500',
        gradient: 'electric',
    },
    [MODELS.DEEPSEEK]: {
        name: 'DeepSeek (flash)',
        color: 'text-purple-400',
        bgColor: 'bg-purple-500',
        gradient: 'ai',
    },
    [MODELS.MINIMAX]: {
        name: 'MiniMax (M3.1)',
        color: 'text-pink-400',
        bgColor: 'bg-pink-500',
        gradient: 'catalyst',
    },
};

export interface LeaderboardDisplayInfo {
    name: string;
    subtitle: string;
    entityType: LeaderboardEntityType;
    categoryLabel: 'LLM' | 'System' | 'User Bot';
    badgeColor: 'accent' | 'warning' | 'info' | 'neutral';
    color: string;
    bgColor: string;
    gradient: 'electric' | 'success' | 'alert' | 'catalyst' | 'ai';
}

function formatFallbackOwnerName(ownerId: string): string {
    const cleanName = ownerId.split('/').pop() || ownerId;
    return cleanName.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getModelDisplayInfo(ownerId: string | null | undefined): LeaderboardDisplayInfo {
    if (!ownerId) {
        return {
            name: 'Unknown',
            subtitle: '',
            entityType: 'llm',
            categoryLabel: 'LLM',
            badgeColor: 'neutral',
            color: 'text-voxel-muted',
            bgColor: 'bg-zinc-500',
            gradient: 'electric',
        };
    }

    if (isSystemPortfolio(ownerId)) {
        const subtitle = getSystemPortfolioSubtitle(ownerId) || ownerId;
        return {
            name: formatFallbackOwnerName(ownerId),
            subtitle,
            entityType: 'system',
            categoryLabel: 'System',
            badgeColor: 'warning',
            color: 'text-accent',
            bgColor: 'bg-amber-500',
            gradient: 'catalyst',
        };
    }

    const legacy = legacyModelLabel(ownerId);
    if (legacy) {
        return {
            name: legacy,
            subtitle: ownerId,
            entityType: 'llm',
            categoryLabel: 'LLM',
            badgeColor: 'accent',
            color: 'text-zinc-400',
            bgColor: 'bg-zinc-600',
            gradient: 'electric',
        };
    }

    const normalized = ownerId.toLowerCase().trim();
    const matchedConfig = Object.entries(modelDisplayConfig).find(
        ([key]) => key.toLowerCase() === normalized,
    )?.[1];
    if (matchedConfig) {
        return {
            ...matchedConfig,
            subtitle: ownerId,
            entityType: 'llm',
            categoryLabel: 'LLM',
            badgeColor: 'accent',
        };
    }

    return {
        name: formatFallbackOwnerName(ownerId),
        subtitle: ownerId,
        entityType: 'llm',
        categoryLabel: 'LLM',
        badgeColor: 'accent',
        color: 'text-zinc-400',
        bgColor: 'bg-zinc-600',
        gradient: 'electric',
    };
}

export function getLeaderboardDisplayInfo(row: LLMLeaderboardRow): LeaderboardDisplayInfo {
    if (row.entity_type === 'user_bot' || row.recipe_id) {
        return {
            name: row.display_name || 'User Bot',
            subtitle: row.is_live ? 'Live paper bot' : 'Paper strategy bot',
            entityType: 'user_bot',
            categoryLabel: 'User Bot',
            badgeColor: 'info',
            color: 'text-info',
            bgColor: 'bg-emerald-500',
            gradient: 'electric',
        };
    }

    if (row.entity_type === 'system' || isSystemPortfolio(row.model_name)) {
        return getModelDisplayInfo(row.model_name);
    }

    return getModelDisplayInfo(row.model_name);
}

export function formatWinRate(winRate: number | null | undefined): string {
    if (winRate === null || winRate === undefined || !Number.isFinite(winRate)) {
        return '—';
    }
    return `${winRate.toFixed(1)}%`;
}

/**
 * Consistency is a Laplace-smoothed up-day rate, so the bare percentage hides
 * its sample size. Render the counts next to it (`9/10 · 78.6%`) so the column
 * reads as "how often did the equity line close green", not "how stable is it".
 */
export function formatUpDays(
    upDays: number | null | undefined,
    activeDays: number | null | undefined,
    consistencyScore: number,
): string {
    const percent = `${consistencyScore.toFixed(1)}%`;
    if (
        upDays === null ||
        upDays === undefined ||
        activeDays === null ||
        activeDays === undefined ||
        !Number.isFinite(upDays) ||
        !Number.isFinite(activeDays)
    ) {
        return percent;
    }
    return `${upDays}/${activeDays} · ${percent}`;
}
