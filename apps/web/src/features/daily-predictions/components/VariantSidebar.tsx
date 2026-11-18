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

    const borderClass = isSelected
        ? 'border-2 border-blue-500 shadow-sm'
        : isActiveVariant
          ? 'border-2 border-emerald-500'
          : 'border border-zinc-200 border-zinc-800';

    const bgClass = isSelected
        ? 'bg-blue-50/70 bg-blue-950/30'
        : isActiveVariant
          ? 'bg-emerald-50/60 bg-emerald-950/20'
          : 'bg-white bg-zinc-900';

    return (
        <Button
            type="button"
            onClick={onSelect}
            className={`w-full text-left cursor-pointer transition-all duration-150 min-w-0 p-3 rounded-none ${borderClass} ${bgClass}`}
        >
            <div className="flex justify-between items-center gap-2">
                <span
                    className={`font-bold text-sm break-all ${
                        isSelected ? 'text-blue-700 text-blue-400' : 'text-zinc-900 text-zinc-100'
                    }`}
                >
                    {exp.variant_tag}
                </span>
                {typeof score === 'number' && (
                    <span
                        className={`text-sm font-bold px-1.5 py-0.5 rounded-none shrink-0 tabular-nums ${
                            isScorePositive
                                ? 'text-emerald-700 bg-emerald-100 bg-emerald-950/60 text-emerald-400'
                                : 'text-rose-700 bg-rose-100 bg-rose-950/60 text-rose-400'
                        }`}
                    >
                        {score.toFixed(1)}
                    </span>
                )}
            </div>
            <div className="flex gap-1.5 mt-1.5 flex-wrap items-center">
                <Badge colorScheme={statusBadge.colorScheme} variant="soft" size="xs">
                    {statusBadge.label}
                </Badge>
                <span className="text-xs font-normal text-zinc-500 text-zinc-400">
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
            <div className="text-sm font-bold text-zinc-500 text-zinc-400 uppercase tracking-wider">
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
