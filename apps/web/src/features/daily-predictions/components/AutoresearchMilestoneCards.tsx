import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type * as React from 'react';
import {
    computeExperimentMilestones,
    formatDeltaText,
    getActiveBadge,
    getDeltaColor,
    getMilestoneSubtitle,
} from '../utils/daily-predictions-helpers';

export interface AutoresearchMilestonesProps {
    experiments: PromptExperiment[];
}

interface MilestoneCardProps {
    title: string;
    value: React.ReactNode;
    subtitle: string;
    valueColor?: string;
    fontSize?: string;
}

export function MilestoneCard({
    title,
    value,
    subtitle,
    valueColor,
    fontSize,
}: MilestoneCardProps) {
    return (
        <Card className="p-5 flex flex-col justify-between min-w-0 overflow-hidden">
            <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">{title}</div>
            <div
                className={`font-bold mt-1 break-words overflow-wrap-anywhere ${
                    fontSize ? '' : 'text-2xl'
                }`}
                style={{
                    color: valueColor,
                    fontSize: fontSize || undefined,
                }}
            >
                {value}
            </div>
            <div className="text-xs text-zinc-400 dark:text-zinc-500 mt-1">{subtitle}</div>
        </Card>
    );
}

export function AutoresearchMilestoneCards({ experiments }: AutoresearchMilestonesProps) {
    const { activeExp, activeScore, bestBaselineScore, delta, isBaselineAnchor } =
        computeExperimentMilestones(experiments);

    const isEvaluating = activeExp?.status === 'active' && activeScore === null;
    const deltaColor = isEvaluating ? '#64748b' : getDeltaColor(delta);
    const deltaText = formatDeltaText(delta, isEvaluating);

    const isScorePositive = activeScore !== null && Number(activeScore) > 0;
    const activeScoreColor = isScorePositive ? '#16a34a' : isEvaluating ? '#64748b' : undefined;
    const activeScoreDisplay =
        activeScore !== null ? Number(activeScore).toFixed(2) : isEvaluating ? 'Pending' : 'N/A';
    const bestBaselineDisplay = bestBaselineScore !== null ? bestBaselineScore.toFixed(2) : 'N/A';

    const activeTagDisplay = activeExp?.variant_tag || 'daily-pred-baseline';
    const activeBadge = getActiveBadge(activeExp?.status);
    const activeSubtitle = getMilestoneSubtitle(isBaselineAnchor, activeExp?.status);

    return (
        <div
            style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 12rem), 1fr))',
                gap: '16px',
                marginBottom: '24px',
                minWidth: 0,
            }}
        >
            <MilestoneCard
                title="Current Active Prompt"
                value={
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                        <span className="text-sm font-bold text-blue-600 dark:text-blue-400 break-all">
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
                subtitle="Weighted accuracy, target hit & Brier"
                valueColor={activeScoreColor}
            />
            <MilestoneCard
                title="All-Time Best Baseline"
                value={bestBaselineDisplay}
                subtitle="Highest performance benchmark"
                valueColor="#4f46e5"
            />
            <MilestoneCard
                title="Score Progression"
                value={deltaText}
                subtitle={activeSubtitle}
                valueColor={deltaColor}
                fontSize="20px"
            />
            <MilestoneCard
                title="Mutated Variants Tracked"
                value={experiments.length}
                subtitle="Evolution iterations for model"
            />
        </div>
    );
}
