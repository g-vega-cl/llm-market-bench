import type { PromptExperiment } from '@llm-market-bench/database';
import { isExperimentColdStart } from '~/features/autoresearch/utils/coldStart';
import type { SectorPrediction } from '../api/fetch-predictions';

export function isSectorTrackColdStart(trackExps: PromptExperiment[]): boolean {
    if (trackExps.length === 0) return false;
    const activeExp = trackExps.find((e) => e.status === 'active');
    const targetExp = activeExp || trackExps[0];
    return isExperimentColdStart(targetExp);
}

export type SectorTrackId = 'all' | 'deepseek' | 'minimax' | 'gemini' | 'openai' | 'legacy';

export interface SectorTrackConfig {
    id: SectorTrackId;
    label: string;
    shortLabel: string;
    badgeColorScheme: 'accent' | 'neutral' | 'success' | 'warning' | 'info';
    badgeClass: string;
    matches: (trackId?: string | null, variantTag?: string | null) => boolean;
    matchesPrediction: (modelName: string) => boolean;
}

export const SECTOR_MODEL_TRACKS: SectorTrackConfig[] = [
    {
        id: 'deepseek',
        label: 'DeepSeek Flash',
        shortLabel: 'DeepSeek',
        badgeColorScheme: 'info',
        badgeClass: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
        matches: (trackId, variantTag) => {
            const t = (trackId || '').toLowerCase();
            const v = (variantTag || '').toLowerCase();
            return t.includes('deepseek') || v.includes('deepseek');
        },
        matchesPrediction: (m) => m.toLowerCase().includes('deepseek'),
    },
    {
        id: 'minimax',
        label: 'MiniMax-M3',
        shortLabel: 'MiniMax',
        badgeColorScheme: 'success',
        badgeClass: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
        matches: (trackId, variantTag) => {
            const t = (trackId || '').toLowerCase();
            const v = (variantTag || '').toLowerCase();
            return t.includes('minimax') || v.includes('minimax');
        },
        matchesPrediction: (m) => m.toLowerCase().includes('minimax'),
    },
    {
        id: 'gemini',
        label: 'Gemini 3.5',
        shortLabel: 'Gemini',
        badgeColorScheme: 'warning',
        badgeClass: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
        matches: (trackId, variantTag) => {
            const t = (trackId || '').toLowerCase();
            const v = (variantTag || '').toLowerCase();
            return t.includes('gemini') || v.includes('gemini');
        },
        matchesPrediction: (m) => m.toLowerCase().includes('gemini'),
    },
    {
        id: 'openai',
        label: 'OpenAI GPT-5.6',
        shortLabel: 'OpenAI',
        badgeColorScheme: 'accent',
        badgeClass: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
        matches: (trackId, variantTag) => {
            const t = (trackId || '').toLowerCase();
            const v = (variantTag || '').toLowerCase();
            return (
                t.includes('gpt') ||
                t.includes('openai') ||
                v.includes('gpt') ||
                v.includes('openai')
            );
        },
        matchesPrediction: (m) => {
            const lower = m.toLowerCase();
            return lower.includes('gpt') || lower.includes('openai');
        },
    },
];

export const LEGACY_TRACK_CONFIG: SectorTrackConfig = {
    id: 'legacy',
    label: 'Legacy / Default',
    shortLabel: 'Legacy',
    badgeColorScheme: 'neutral',
    badgeClass: 'bg-slate-500/20 text-slate-400 border border-slate-500/30',
    matches: (trackId, variantTag) => {
        // Matches if it DOES NOT match any of the 4 standard model tracks
        return !SECTOR_MODEL_TRACKS.some((trk) => trk.matches(trackId, variantTag));
    },
    matchesPrediction: () => false,
};

export function getAvailableTracks(experiments: PromptExperiment[]): SectorTrackConfig[] {
    const hasLegacy = experiments.some((exp) =>
        LEGACY_TRACK_CONFIG.matches(exp.track_id, exp.variant_tag),
    );

    return hasLegacy ? [...SECTOR_MODEL_TRACKS, LEGACY_TRACK_CONFIG] : SECTOR_MODEL_TRACKS;
}

export function filterExperimentsByTrack(
    experiments: PromptExperiment[],
    trackId: SectorTrackId,
): PromptExperiment[] {
    if (trackId === 'all') {
        return experiments;
    }

    if (trackId === 'legacy') {
        return experiments.filter((exp) =>
            LEGACY_TRACK_CONFIG.matches(exp.track_id, exp.variant_tag),
        );
    }

    const track = SECTOR_MODEL_TRACKS.find((t) => t.id === trackId);
    if (!track) return experiments;

    return experiments.filter((exp) => track.matches(exp.track_id, exp.variant_tag));
}

export function filterPredictionsByTrack(
    predictions: SectorPrediction[],
    trackId: SectorTrackId,
): SectorPrediction[] {
    if (trackId === 'all' || trackId === 'legacy') {
        return predictions;
    }

    const track = SECTOR_MODEL_TRACKS.find((t) => t.id === trackId);
    if (!track) return predictions;

    return predictions.filter((p) => track.matchesPrediction(p.model_name));
}

export function calculateTrackBaselineScore(experiments: PromptExperiment[]): string {
    const scores = experiments
        .map((exp) => exp.metrics?.score)
        .filter((s): s is number => s !== undefined && s !== null);
    if (scores.length === 0) return 'N/A';
    return Math.max(...scores).toFixed(4);
}

export function findTrackActiveVariant(experiments: PromptExperiment[]): string {
    return experiments.find((exp) => exp.status === 'active')?.variant_tag || 'N/A';
}

export function getExperimentTrackInfo(exp: PromptExperiment): {
    label: string;
    badgeClass: string;
    colorScheme: 'accent' | 'neutral' | 'success' | 'warning' | 'info';
} {
    for (const track of SECTOR_MODEL_TRACKS) {
        if (track.matches(exp.track_id, exp.variant_tag)) {
            return {
                label: track.shortLabel,
                badgeClass: track.badgeClass,
                colorScheme: track.badgeColorScheme,
            };
        }
    }

    return {
        label: exp.track_id ? exp.track_id.replace(/^track_/, '') : 'Legacy',
        badgeClass: LEGACY_TRACK_CONFIG.badgeClass,
        colorScheme: LEGACY_TRACK_CONFIG.badgeColorScheme,
    };
}

export interface ModelTrackSummary {
    track: SectorTrackConfig;
    activeVariant: string;
    baselineScore: string;
    numericBaselineScore: number | null;
    experimentCount: number;
    isColdStart: boolean;
    status: 'active' | 'baseline' | 'saved' | 'none';
}

export function computeModelTrackSummaries(experiments: PromptExperiment[]): ModelTrackSummary[] {
    return SECTOR_MODEL_TRACKS.map((track) => {
        const trackExps = experiments.filter((exp) => track.matches(exp.track_id, exp.variant_tag));
        const baseline = calculateTrackBaselineScore(trackExps);
        const activeExp = trackExps.find((exp) => exp.status === 'active');
        const activeVariant = activeExp?.variant_tag || trackExps[0]?.variant_tag || 'N/A';
        const isCold = isSectorTrackColdStart(trackExps);

        return {
            track,
            activeVariant,
            baselineScore: baseline,
            numericBaselineScore: baseline !== 'N/A' ? Number.parseFloat(baseline) : null,
            experimentCount: trackExps.length,
            isColdStart: isCold,
            status: activeExp ? 'active' : trackExps.length > 0 ? 'baseline' : 'none',
        };
    });
}
