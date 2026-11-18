import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { isExperimentColdStart } from '../../autoresearch/utils/coldStart';
import type { DailyPrediction } from '../api/fetch-daily-predictions';
import {
    getExperimentDisplayScore,
    getSidebarStatusBadge,
} from '../utils/daily-predictions-helpers';

export interface VariantSidebarItemProps {
    exp: PromptExperiment;
    predictions?: DailyPrediction[];
    isSelected: boolean;
    isActiveVariant?: boolean;
    onSelect: () => void;
}

export function VariantSidebarItem({
    exp,
    predictions,
    isSelected,
    isActiveVariant,
    onSelect,
}: VariantSidebarItemProps) {
    const score = getExperimentDisplayScore(exp, predictions);
    const isScorePositive = typeof score === 'number' && score > 0;
    const statusBadge = getSidebarStatusBadge(exp.status, isActiveVariant);

    return (
        <Button
            type="button"
            variant="outline"
            colorScheme={isSelected ? 'accent' : isActiveVariant ? 'success' : 'neutral'}
            onClick={onSelect}
            className="w-full text-left min-w-0 p-3 flex flex-col items-stretch gap-1"
        >
            <div className="flex justify-between items-center gap-2">
                <span
                    className={`font-bold text-sm break-all ${
                        isSelected ? 'text-accent' : 'text-voxel-ink'
                    }`}
                >
                    {exp.variant_tag}
                </span>
                {typeof score === 'number' && (
                    <span
                        className={`text-sm font-bold px-1.5 py-0.5 rounded-none shrink-0 tabular-nums border ${
                            isScorePositive
                                ? 'bg-emerald-950/60 text-success border-emerald-500/30'
                                : 'bg-rose-950/60 text-danger border-rose-500/30'
                        }`}
                    >
                        {score.toFixed(1)}
                    </span>
                )}
            </div>
            <div className="flex gap-1.5 mt-1 flex-wrap items-center">
                <Badge colorScheme={statusBadge.colorScheme} variant="soft" size="xs">
                    {statusBadge.label}
                </Badge>
                <span className="text-xs font-normal text-voxel-muted">
                    {exp.experiment_type || 'incremental'}
                </span>
                {isExperimentColdStart(exp) && (
                    <Badge colorScheme="warning" variant="soft" size="xs">
                        From 0
                    </Badge>
                )}
            </div>
        </Button>
    );
}

export interface VariantSidebarProps {
    experiments: PromptExperiment[];
    predictions?: DailyPrediction[];
    selectedExpId: string | null;
    activePromptTag?: string | null;
    onSelectExp: (id: string) => void;
}

export function VariantSidebar({
    experiments,
    predictions,
    selectedExpId,
    activePromptTag,
    onSelectExp,
}: VariantSidebarProps) {
    return (
        <div className="w-full flex-1 basis-72 min-w-0 flex flex-col gap-2">
            <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                Experiment Lineage
            </div>
            <div className="flex flex-col gap-2 max-h-96 overflow-y-auto pr-1 min-w-0">
                {experiments.map((exp) => (
                    <VariantSidebarItem
                        key={exp.id}
                        exp={exp}
                        predictions={predictions}
                        isSelected={exp.id === selectedExpId}
                        isActiveVariant={exp.variant_tag === activePromptTag}
                        onSelect={() => onSelectExp(exp.id)}
                    />
                ))}
            </div>
        </div>
    );
}
