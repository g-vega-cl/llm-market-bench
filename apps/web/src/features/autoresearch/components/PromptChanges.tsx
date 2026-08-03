import type { PromptExperiment } from '@llm-market-bench/database';
import { Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import { diffLines } from '../utils/diff';
import { splitPromptSections } from '../utils/promptSections';

interface PromptChangesProps {
    experiment: PromptExperiment;
    parentExperiment: PromptExperiment | null | undefined;
}

/**
 * Returns color-coded tailwind classes and diff symbol prefix for a line.
 */
function getLineStyle(added?: boolean, removed?: boolean) {
    if (added) {
        return {
            prefix: '+ ',
            classes: 'bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-500 px-2 py-0.5',
        };
    }
    if (removed) {
        return {
            prefix: '- ',
            classes:
                'bg-rose-500/10 text-rose-400 border-l-2 border-rose-500 px-2 py-0.5 line-through decoration-rose-500/30',
        };
    }
    return {
        prefix: '  ',
        classes: 'text-zinc-400 dark:text-zinc-500 px-2 py-0.5 opacity-60',
    };
}

export function PromptChanges({ experiment, parentExperiment }: PromptChangesProps) {
    const [showChangesOnly, setShowChangesOnly] = useState(true);

    // Compute diff on mutable sections only (header+footer are identical across all variants)
    const diffResult = useMemo(() => {
        if (!parentExperiment) return [];
        const parentMutable = splitPromptSections(parentExperiment.prompt_content || '').mutable;
        const currentMutable = splitPromptSections(experiment.prompt_content || '').mutable;
        // Fall back to full content if splitting didn't detect the mutable boundary
        const parentText = parentMutable || parentExperiment.prompt_content || '';
        const currentText = currentMutable || experiment.prompt_content || '';
        return diffLines(parentText, currentText);
    }, [parentExperiment, experiment.prompt_content]);

    // Check if there are actual additions/deletions
    const hasChanges = useMemo(() => {
        return diffResult.some((item) => item.added || item.removed);
    }, [diffResult]);

    // Filtered lines depending on toggle
    const filteredChanges = useMemo(() => {
        if (!showChangesOnly) return diffResult;
        return diffResult.filter((item) => item.added || item.removed);
    }, [diffResult, showChangesOnly]);

    // If no parent experiment, we render a callout card (after hooks to satisfy React rules)
    if (!parentExperiment) {
        const isBaseline = experiment.experiment_type === 'baseline';
        return (
            <Card className="p-8 border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50">
                <div className="flex flex-col items-center justify-center text-center space-y-3 py-4">
                    <span className="text-2xl">🌱</span>
                    <h3 className="font-bold text-zinc-900 dark:text-zinc-100">
                        {isBaseline ? 'Initial baseline prompt' : 'No parent prompt'}
                    </h3>
                    <p className="text-zinc-500 dark:text-zinc-400 text-sm max-w-md">
                        {isBaseline
                            ? 'This is the starting point of the auto-research loop. No previous variant is available to compare.'
                            : 'This experiment does not have a registered parent variant to compare against.'}
                    </p>
                </div>
            </Card>
        );
    }

    return (
        <Card className="p-8 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                    <SectionHeading>Prompt Changes</SectionHeading>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        Comparing{' '}
                        <span className="font-mono text-emerald-500">
                            v{parentExperiment.variant_tag}
                        </span>{' '}
                        (old) →{' '}
                        <span className="font-mono text-emerald-500">
                            v{experiment.variant_tag}
                        </span>{' '}
                        (new) &mdash;{' '}
                        <span className="italic">mutable strategies section only</span>
                    </p>
                </div>

                {hasChanges && (
                    <Button
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={() => setShowChangesOnly(!showChangesOnly)}
                    >
                        {showChangesOnly ? 'Show Full Prompt Diff' : 'Show Changes Only'}
                    </Button>
                )}
            </div>

            <div className="relative group">
                <div className="relative font-mono text-[11px] leading-relaxed max-h-[400px] overflow-y-auto bg-zinc-950 border border-zinc-800 rounded-xl p-4 md:p-6 space-y-[2px]">
                    {!hasChanges ? (
                        <div className="text-center text-zinc-500 dark:text-zinc-400 py-8 text-sm">
                            ✨ No prompt text changes detected between these variants.
                        </div>
                    ) : showChangesOnly && filteredChanges.length === 0 ? (
                        <div className="text-center text-zinc-500 dark:text-zinc-400 py-8 text-sm">
                            No added or removed lines to show.
                        </div>
                    ) : (
                        filteredChanges.map((change, idx) => {
                            const { prefix, classes } = getLineStyle(change.added, change.removed);

                            return (
                                // biome-ignore lint/suspicious/noArrayIndexKey: Static diff lines sequence
                                <div key={idx} className={`${classes} whitespace-pre-wrap`}>
                                    {prefix}
                                    {change.value}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </Card>
    );
}
