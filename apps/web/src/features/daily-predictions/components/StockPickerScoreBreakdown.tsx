import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, SectionHeading } from '@llm-market-bench/ui-design-system';

export interface StockPickerScoreBreakdownProps {
    experiment: PromptExperiment;
}

interface StockPickerStoredMetrics {
    hurdle_score?: number;
    score?: number;
    hit_rate_pct?: number;
    ls_spread_alpha_pct?: number;
    conviction_norm?: number;
    sample_baskets?: number;
}

export function clampNormalizedAlpha(lsAlphaPct: number): number {
    return Math.max(0.0, Math.min(100.0, 50.0 + lsAlphaPct * 10.0));
}

export function StockPickerScoreBreakdown({ experiment }: StockPickerScoreBreakdownProps) {
    const metrics = (experiment.metrics || {}) as StockPickerStoredMetrics;
    const rawScore =
        typeof metrics.hurdle_score === 'number'
            ? metrics.hurdle_score
            : typeof metrics.score === 'number'
              ? metrics.score
              : null;

    if (rawScore === null) {
        return (
            <div className="p-5 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-col gap-2 min-w-0">
                <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                    <SectionHeading>Normalized Ratchet Hurdle Score Audit</SectionHeading>
                    <Badge variant="soft" colorScheme="warning">
                        Pending Evaluation
                    </Badge>
                </div>
                <p className="text-xs font-normal text-voxel-muted">
                    This active prompt variant is currently collecting live 3 UP / 3 DOWN sessions.
                    Ratchet scoring executes weekly on Sunday at 6:00 PM ET over the rolling
                    5-session window.
                </p>
            </div>
        );
    }

    const hitRate = typeof metrics.hit_rate_pct === 'number' ? metrics.hit_rate_pct : 0.0;
    const lsAlpha =
        typeof metrics.ls_spread_alpha_pct === 'number' ? metrics.ls_spread_alpha_pct : 0.0;
    const convictionNorm =
        typeof metrics.conviction_norm === 'number' ? metrics.conviction_norm : 50.0;
    const sampleBaskets =
        typeof metrics.sample_baskets === 'number' ? metrics.sample_baskets : null;
    const alphaNorm = clampNormalizedAlpha(lsAlpha);

    const hitContribution = 0.5 * hitRate;
    const alphaContribution = 0.4 * alphaNorm;
    const convictionContribution = 0.1 * convictionNorm;

    return (
        <div className="p-5 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-col gap-4 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-2 min-w-0">
                <SectionHeading>Normalized Ratchet Hurdle Score Audit</SectionHeading>
                <div className="flex flex-wrap items-center gap-2">
                    {sampleBaskets !== null && (
                        <Badge variant="soft" colorScheme="neutral">
                            {sampleBaskets} Sessions Evaluated
                        </Badge>
                    )}
                    <Badge variant="solid" colorScheme={rawScore >= 50 ? 'success' : 'danger'}>
                        Hurdle Score: {rawScore.toFixed(2)}
                    </Badge>
                </div>
            </div>

            <div className="p-4 bg-voxel-canvas border border-voxel-bevel-hi rounded-none flex flex-col gap-2 min-w-0 overflow-x-auto break-words">
                <div className="text-xs font-normal text-voxel-muted font-mono">
                    Score = 0.50 * Hit_Rate + 0.40 * clamp(50 + LS_Alpha * 10, 0, 100) + 0.10 *
                    Conviction_Norm
                </div>
                <div className="text-sm font-bold text-voxel-ink font-mono tabular-nums">
                    {rawScore.toFixed(2)} = 0.50 * {hitRate.toFixed(1)} (
                    {hitContribution.toFixed(2)}) + 0.40 * {alphaNorm.toFixed(1)} (
                    {alphaContribution.toFixed(2)}) + 0.10 * {convictionNorm.toFixed(1)} (
                    {convictionContribution.toFixed(2)})
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,13rem),1fr))] gap-4 items-stretch min-w-0">
                <div className="p-4 bg-voxel-surface border border-voxel-bevel-hi rounded-none flex flex-col justify-between gap-2 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-normal uppercase tracking-wider text-voxel-muted font-mono">
                            Directional Hit Rate
                        </span>
                        <Badge variant="soft" colorScheme="neutral">
                            50% Weight
                        </Badge>
                    </div>
                    <div className="text-sm font-bold font-mono tabular-nums text-success">
                        {hitRate.toFixed(1)}%
                    </div>
                    <div className="text-xs font-normal text-voxel-muted font-mono tabular-nums">
                        +{hitContribution.toFixed(2)} pts contribution
                    </div>
                </div>

                <div className="p-4 bg-voxel-surface border border-voxel-bevel-hi rounded-none flex flex-col justify-between gap-2 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-normal uppercase tracking-wider text-voxel-muted font-mono">
                            L/S Spread Alpha
                        </span>
                        <Badge variant="soft" colorScheme="neutral">
                            40% Weight
                        </Badge>
                    </div>
                    <div
                        className={`text-sm font-bold font-mono tabular-nums ${
                            lsAlpha >= 0 ? 'text-success' : 'text-danger'
                        }`}
                    >
                        {lsAlpha > 0 ? '+' : ''}
                        {lsAlpha.toFixed(2)}%
                    </div>
                    <div className="text-xs font-normal text-voxel-muted font-mono tabular-nums">
                        Norm {alphaNorm.toFixed(1)} (+{alphaContribution.toFixed(2)} pts)
                    </div>
                </div>

                <div className="p-4 bg-voxel-surface border border-voxel-bevel-hi rounded-none flex flex-col justify-between gap-2 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-normal uppercase tracking-wider text-voxel-muted font-mono">
                            Conviction Calibration
                        </span>
                        <Badge variant="soft" colorScheme="neutral">
                            10% Weight
                        </Badge>
                    </div>
                    <div className="text-sm font-bold font-mono tabular-nums text-voxel-ink">
                        {convictionNorm.toFixed(1)}
                    </div>
                    <div className="text-xs font-normal text-voxel-muted font-mono tabular-nums">
                        +{convictionContribution.toFixed(2)} pts contribution
                    </div>
                </div>
            </div>
        </div>
    );
}
