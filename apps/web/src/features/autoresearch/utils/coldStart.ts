import type { PromptExperiment } from '@llm-market-bench/database';

/**
 * Returns whether a prompt experiment was generated "from 0" via cold-start reset.
 */
export function isExperimentColdStart(exp?: PromptExperiment | null): boolean {
    if (!exp) return false;
    const output = exp.research_output as { is_cold_start?: boolean } | null;
    return Boolean(output?.is_cold_start);
}

/**
 * Returns whether a given track's current live strategy is running "from 0".
 * Evaluates the active experiment first, falling back to the latest experiment.
 */
export function isTrackColdStart(trackId: string, experiments: PromptExperiment[]): boolean {
    const trackExps = experiments.filter((e) => (e.track_id || 'track_default') === trackId);
    if (trackExps.length === 0) return false;

    const activeExp = trackExps.find((e) => e.status === 'active');
    const targetExp = activeExp || trackExps[0];
    return isExperimentColdStart(targetExp);
}
