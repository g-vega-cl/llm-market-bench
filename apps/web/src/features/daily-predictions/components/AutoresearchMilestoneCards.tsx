import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type * as React from 'react';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import {
    computeExperimentMilestones,
    formatDeltaText,
    getActiveBadge,
    getMilestoneSubtitle,
} from '../utils/daily-predictions-helpers';

export interface AutoresearchMilestonesProps {
    experiments: PromptExperiment[];
    predictions?: DailyPrediction[];
}

interface MilestoneCardProps {
    title: string;
    value: React.ReactNode;
    subtitle: string;
    valueClassName?: string;
    fontSize?: string;
}

export function MilestoneCard({ title, value, subtitle, valueClassName }: MilestoneCardProps) {
    return (
        <Card className="p-5 flex flex-col justify-between min-w-0 overflow-hidden rounded-none h-full gap-2">
            <div className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                {title}
            </div>
            <div
                className={`text-lg font-bold font-mono break-words overflow-wrap-anywhere ${valueClassName ?? 'text-boxel-ink'}`}
            >
                {value}
            </div>
            <div className="text-xs font-normal text-boxel-muted">{subtitle}</div>
        </Card>
    );
}

function getDeltaClassName(isEvaluating: boolean, delta: number | null): string {
    if (isEvaluating || delta === null) return 'text-boxel-muted';
    if (delta > 0) return 'text-success';
    if (delta < 0) return 'text-danger';
    return 'text-boxel-ink';
}

function getActiveScoreClassName(isEvaluating: boolean, score: number | null): string {
    if (isEvaluating) return 'text-boxel-muted';
    if (score !== null && Number(score) > 0) return 'text-success';
    if (score !== null) return 'text-danger';
    return 'text-boxel-ink';
}

export function AutoresearchMilestoneCards({
    experiments,
    predictions,
}: AutoresearchMilestonesProps) {
    const { activeExp, activeScore, bestBaselineScore, delta, isBaselineAnchor } =
        computeExperimentMilestones(experiments, predictions);

    const isEvaluating = activeExp?.status === 'active' && activeScore === null;
    const deltaClassName = getDeltaClassName(isEvaluating, delta);
    const deltaText = formatDeltaText(delta, isEvaluating);

    const activeScoreClassName = getActiveScoreClassName(
        isEvaluating,
        activeScore !== null ? Number(activeScore) : null,
    );
    const activeScoreDisplay =
        activeScore !== null ? Number(activeScore).toFixed(2) : isEvaluating ? 'Pending' : 'N/A';
    const bestBaselineDisplay = bestBaselineScore !== null ? bestBaselineScore.toFixed(2) : 'N/A';

    const activeTagDisplay = activeExp?.variant_tag || 'daily-pred-baseline';
    const activeBadge = getActiveBadge(activeExp?.status);
    const activeSubtitle = getMilestoneSubtitle(isBaselineAnchor, activeExp?.status);

    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch min-w-0">
            <MilestoneCard
                title="Current Active Prompt"
                value={
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                        <span className="text-sm font-bold text-accent break-all">
                            {activeTagDisplay}
                        </span>
                        <Badge
                            colorScheme={activeBadge.colorScheme}
                            variant="soft"
                            size="xs"
                            className="shrink-0"
                        >
                            {activeBadge.text}
                        </Badge>
                    </div>
                }
                subtitle={activeSubtitle}
            />
            <MilestoneCard
                title="Active Ratchet Score"
                value={activeScoreDisplay}
                subtitle="Weighted accuracy, target hit & conviction"
                valueClassName={activeScoreClassName}
            />
            <MilestoneCard
                title="All-Time Best Baseline"
                value={bestBaselineDisplay}
                subtitle="Highest performance benchmark"
                valueClassName="text-accent"
            />
            <MilestoneCard
                title="Score Progression"
                value={deltaText}
                subtitle={activeSubtitle}
                valueClassName={deltaClassName}
            />
            <MilestoneCard
                title="Mutated Variants Tracked"
                value={experiments.length}
                subtitle="Evolution iterations for model"
            />
        </div>
    );
}
