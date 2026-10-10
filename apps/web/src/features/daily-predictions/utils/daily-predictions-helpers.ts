import type { PromptExperiment } from '@llm-market-bench/database';
import type { DailyPrediction } from '../api/fetch-daily-predictions';

export const DEFAULT_DAILY_PREDICTOR_TOOLS = [
    'fetch_daily_newsletter',
    'get_calendar_scenario_analysis',
    'get_global_macro_context',
    'get_macro_options_sentiment',
    'get_volatility_index_details',
    'get_market_health_barometer',
    'get_market_feeling',
    'get_today_economic_releases',
    'get_premarket_quote',
];

import modelsConfig from '@repo/config/models.json';

export type SupportedDailyTicker = 'SPY' | 'TLT';

export interface ModelConfig {
    id: string;
    label: string;
    matches: (modelName: string) => boolean;
}

const OPENAI_MODEL_ID = (modelsConfig as { OPENAI_MODEL?: string }).OPENAI_MODEL || 'gpt-5.6-luna';

export const SPY_PREDICTOR_MODELS: ModelConfig[] = [
    {
        id: 'deepseek-v4-flash',
        label: 'DeepSeek Flash',
        matches: (m: string) => m.toLowerCase().includes('deepseek'),
    },
    {
        id: 'MiniMax-M3',
        label: 'MiniMax M3',
        matches: (m: string) => m.toLowerCase().includes('minimax'),
    },
    {
        id: '~typesafe/jev-latest',
        label: 'Jev (TypeSafe)',
        matches: (m: string) =>
            m.toLowerCase().includes('jev') &&
            !m.toLowerCase().includes('local') &&
            !m.toLowerCase().includes('autoresearch'),
    },
    {
        id: 'jev-local-autoresearched',
        label: 'Jev (Local Champion)',
        matches: (m: string) =>
            m.toLowerCase().includes('local-autoresearch') || m.toLowerCase().includes('jev-local'),
    },
];

export interface ParsedCuratedManifest {
    selected_newsletters?: string[] | null;
    include_synthetic_newsletter?: boolean;
    include_macro_proxies?: string[];
    include_currency_uup?: boolean;
    include_options_derivatives?: boolean;
    include_economic_calendar?: boolean;
    include_market_health_barometer?: boolean;
    include_recent_market_feeling?: boolean;
    include_intraday_profile?: boolean;
}

export function parseCuratedManifest(
    promptContent: string | null | undefined,
): ParsedCuratedManifest | null {
    if (!promptContent) return null;
    try {
        const parsed = JSON.parse(promptContent);
        if (parsed && typeof parsed === 'object' && parsed.manifest) {
            return parsed.manifest as ParsedCuratedManifest;
        }
    } catch {
        // Plain text prompt content
    }
    return null;
}

export const BOND_PREDICTOR_MODELS: ModelConfig[] = [
    {
        id: OPENAI_MODEL_ID,
        label: 'GPT-5.6 Luna',
        matches: (m: string) =>
            m.toLowerCase().includes('gpt-5.6') ||
            m.toLowerCase().includes('luna') ||
            m.toLowerCase().includes('openai'),
    },
    {
        id: 'deepseek-v4-flash',
        label: 'DeepSeek Flash',
        matches: (m: string) => m.toLowerCase().includes('deepseek'),
    },
    {
        id: '~typesafe/jev-latest',
        label: 'Jev (TypeSafe)',
        matches: (m: string) => m.toLowerCase().includes('jev'),
    },
];

export const PREDICTOR_MODELS: ModelConfig[] = SPY_PREDICTOR_MODELS;

export function getPredictorModelsForTicker(ticker: SupportedDailyTicker): ModelConfig[] {
    return ticker === 'TLT' ? BOND_PREDICTOR_MODELS : SPY_PREDICTOR_MODELS;
}

export function computeDailyPredictionStats(predictions: DailyPrediction[]) {
    const evaluatedPredictions = predictions.filter(
        (p) => p.status === 'evaluated' && (p.predicted_direction as string) !== 'NO_TRADE',
    );
    const totalEvaluated = evaluatedPredictions.length;
    const correctCount = evaluatedPredictions.filter((p) => p.is_correct === true).length;
    const accuracyPct =
        totalEvaluated > 0 ? ((correctCount / totalEvaluated) * 100).toFixed(1) : 'N/A';

    const intradayHitCount = evaluatedPredictions.filter(
        (p) => p.intraday_hit === true || (p.intraday_hit === null && p.is_correct === true),
    ).length;
    const intradayHitPct =
        totalEvaluated > 0 ? ((intradayHitCount / totalEvaluated) * 100).toFixed(1) : 'N/A';

    const brierScores = evaluatedPredictions
        .map((p) => p.brier_score)
        .filter((s): s is number => s !== null && s !== undefined);
    const avgBrier =
        brierScores.length > 0
            ? (brierScores.reduce((a, b) => a + b, 0) / brierScores.length).toFixed(4)
            : 'N/A';

    return { correctCount, totalEvaluated, accuracyPct, intradayHitPct, avgBrier };
}

export function resolveActiveDailyPrompt(modelExperiments: PromptExperiment[]): {
    activePrompt: PromptExperiment | null;
    isBaselineAnchor: boolean;
} {
    const sorted = [...modelExperiments].sort((a, b) => {
        if (!a.created_at || !b.created_at) return 0;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

    const trackActive = sorted.find((e) => e.status === 'active');
    if (trackActive) {
        return { activePrompt: trackActive, isBaselineAnchor: false };
    }

    const trackBaseline = sorted.find((e) => e.status === 'baseline');
    if (trackBaseline) {
        return { activePrompt: trackBaseline, isBaselineAnchor: true };
    }

    const trackSaved = sorted.find((e) => e.status === 'saved');
    if (trackSaved) {
        return { activePrompt: trackSaved, isBaselineAnchor: true };
    }

    return {
        activePrompt: sorted[0] || null,
        isBaselineAnchor: false,
    };
}

export function computeExperimentMilestones(experiments: PromptExperiment[]) {
    const { activePrompt, isBaselineAnchor } = resolveActiveDailyPrompt(experiments);
    const activeScore = activePrompt?.metrics?.score ?? null;

    let bestBaselineScore: number | null = null;
    for (const exp of experiments) {
        const s = exp.metrics?.score;
        if (typeof s === 'number' && (bestBaselineScore === null || s > bestBaselineScore)) {
            bestBaselineScore = s;
        }
    }

    const parentExp = experiments.find((e) => e.variant_tag === activePrompt?.parent_tag);
    const parentScore = parentExp?.metrics?.score ?? null;
    const delta =
        activeScore !== null && parentScore !== null
            ? Number(activeScore) - Number(parentScore)
            : null;

    return {
        activeExp: activePrompt,
        activeScore,
        bestBaselineScore,
        delta,
        isBaselineAnchor,
    };
}

export function formatDeltaText(delta: number | null, isEvaluating = false): string {
    if (isEvaluating) return 'Pending Evaluation';
    if (delta === null) return 'Baseline Initialized';
    const sign = delta > 0 ? '▲ +' : delta < 0 ? '▼ ' : '';
    return `${sign}${delta.toFixed(2)} vs Parent`;
}

export function getDeltaColor(delta: number | null): string {
    if (delta === null) return '#0f172a';
    if (delta > 0) return '#16a34a';
    if (delta < 0) return '#dc2626';
    return '#0f172a';
}

export function getActiveBadge(status?: string): {
    text: string;
    colorScheme: 'success' | 'accent' | 'neutral';
} {
    if (status === 'active') {
        return { text: '🟢 ACTIVE', colorScheme: 'success' };
    }
    if (status === 'baseline') {
        return { text: '🏆 BASELINE', colorScheme: 'accent' };
    }
    return {
        text: `📦 ${status?.toUpperCase() || 'BASELINE'}`,
        colorScheme: 'neutral',
    };
}

export function getMilestoneSubtitle(isBaselineAnchor: boolean, status?: string): string {
    if (isBaselineAnchor) return 'Ratchet-reverted to all-time benchmark';
    if (status === 'active') return 'Live mutated strategy undergoing evaluation';
    return `Status: ${status || 'baseline'}`;
}

export function getSidebarStatusBadge(
    status: string,
    isActiveVariant?: boolean,
): {
    colorScheme: 'success' | 'neutral' | 'accent' | 'danger';
    label: string;
} {
    if (isActiveVariant) return { colorScheme: 'success', label: '🟢 ACTIVE' };
    if (status === 'active') return { colorScheme: 'neutral', label: '📦 SAVED' };
    if (status === 'baseline') return { colorScheme: 'accent', label: '🏆 BASELINE' };
    if (status === 'discarded') return { colorScheme: 'danger', label: '❌ DISCARDED' };
    return { colorScheme: 'neutral', label: '📦 SAVED' };
}
