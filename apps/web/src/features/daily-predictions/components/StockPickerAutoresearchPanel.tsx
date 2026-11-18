import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { useState } from 'react';
import { PromptChanges } from '../../autoresearch/components/PromptChanges';
import { ResearchRationaleCard } from '../../autoresearch/components/ResearchRationaleCard';
import {
    getExperimentDisplayScore,
    resolveActiveDailyPrompt,
    STOCK_PICKER_TRACK_MODELS,
} from '../utils/daily-predictions-helpers';
import { SelectedVariantHeader } from './AutoresearchHistoryArena';
import { AutoresearchMilestoneCards } from './AutoresearchMilestoneCards';
import { SegmentedPromptInspector } from './SegmentedPromptInspector';
import { StockPickerScoreBreakdown } from './StockPickerScoreBreakdown';
import { VariantSidebar } from './VariantSidebar';

export interface StockPickerAutoresearchPanelProps {
    experiments: PromptExperiment[];
    selectedModel: string;
    onSelectModel: (modelId: string) => void;
}

export function StockPickerAutoresearchPanel({
    experiments,
    selectedModel,
    onSelectModel,
}: StockPickerAutoresearchPanelProps) {
    const [selectedExpId, setSelectedExpId] = useState<string | null>(null);

    const activeTrackCfg =
        STOCK_PICKER_TRACK_MODELS.find((m) => m.id === selectedModel) ||
        STOCK_PICKER_TRACK_MODELS.find((m) =>
            experiments.some((e) => (e.track_id ? m.matches(e.track_id) : false)),
        ) ||
        STOCK_PICKER_TRACK_MODELS[0];

    const trackExperiments = experiments.filter((e) =>
        e.track_id ? activeTrackCfg.matches(e.track_id) : true,
    );

    const { activePrompt } = resolveActiveDailyPrompt(trackExperiments);

    const selectedExperiment =
        trackExperiments.find((e) => e.id === selectedExpId) ||
        trackExperiments.find((e) => e.variant_tag === activePrompt?.variant_tag) ||
        trackExperiments[0] ||
        null;

    const selectedIdx = selectedExperiment
        ? trackExperiments.findIndex((e) => e.id === selectedExperiment.id)
        : -1;

    const parentExperiment = selectedExperiment?.parent_tag
        ? trackExperiments.find((e) => e.variant_tag === selectedExperiment.parent_tag) || null
        : selectedIdx >= 0 && selectedIdx + 1 < trackExperiments.length
          ? trackExperiments[selectedIdx + 1]
          : null;

    return (
        <div className="flex flex-col gap-6 min-w-0">
            {selectedModel === 'consensus' && (
                <div className="p-4 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-wrap items-center justify-between gap-4 min-w-0">
                    <div className="flex flex-col gap-1 min-w-0">
                        <span className="text-sm font-bold text-voxel-ink">
                            Consensus RRF Aggregates 3 Independent Autoresearch Tracks
                        </span>
                        <span className="text-xs font-normal text-voxel-muted">
                            The Consensus basket combines the top picks from DeepSeek Flash,
                            MiniMax-M3.1-Flash, and GPT-6 Luna via Reciprocal Rank Fusion. Select an
                            underlying model track below to inspect its prompt mutations and ratchet
                            score history.
                        </span>
                    </div>
                    <Badge variant="soft" colorScheme="accent">
                        Showing: {activeTrackCfg.label}
                    </Badge>
                </div>
            )}

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-4 items-stretch min-w-0">
                {STOCK_PICKER_TRACK_MODELS.map((track) => {
                    const exps = experiments.filter((e) =>
                        e.track_id ? track.matches(e.track_id) : false,
                    );
                    const { activePrompt: trackActive } = resolveActiveDailyPrompt(exps);
                    const score = trackActive ? getExperimentDisplayScore(trackActive) : null;
                    const isCurrentTrack = activeTrackCfg.id === track.id;

                    return (
                        <Button
                            key={track.id}
                            type="button"
                            variant="outline"
                            colorScheme={isCurrentTrack ? 'accent' : 'neutral'}
                            onClick={() => {
                                onSelectModel(track.id);
                                setSelectedExpId(null);
                            }}
                            className="p-4 text-left flex flex-col items-stretch justify-between gap-2 h-full min-w-0"
                        >
                            <div className="flex items-center justify-between gap-2 min-w-0">
                                <span className="text-sm font-bold text-voxel-ink truncate">
                                    {track.label}
                                </span>
                                <Badge
                                    variant="soft"
                                    colorScheme={isCurrentTrack ? 'accent' : 'neutral'}
                                    size="xs"
                                >
                                    {exps.length} Variants
                                </Badge>
                            </div>
                            <div className="flex items-baseline justify-between gap-2 min-w-0">
                                <span className="text-xs font-normal text-voxel-muted font-mono truncate">
                                    {trackActive?.variant_tag || 'Unseeded baseline'}
                                </span>
                                <span className="text-sm font-bold font-mono tabular-nums text-success shrink-0">
                                    {score !== null ? `${score.toFixed(2)} pts` : 'Pending'}
                                </span>
                            </div>
                        </Button>
                    );
                })}
            </div>

            {trackExperiments.length === 0 ? (
                <div className="p-8 text-center text-voxel-muted bg-voxel-surface rounded-none border border-voxel-bevel-hi font-mono text-xs">
                    No stock picker prompt experiments recorded for {activeTrackCfg.label} yet.
                    Weekly stock picker autoresearch executes on Sunday at 6:00 PM ET (10:00 PM
                    UTC).
                </div>
            ) : (
                <>
                    <AutoresearchMilestoneCards experiments={trackExperiments} />

                    <div className="p-5 min-w-0 w-full overflow-hidden bg-voxel-surface rounded-none border border-voxel-bevel-hi flex flex-col gap-4">
                        <div className="flex flex-wrap justify-between items-center gap-2 min-w-0">
                            <h2 className="text-sm font-bold text-voxel-ink">
                                3 Up / 3 Down Prompt Lineage & Hurdle Benchmarks (
                                {activeTrackCfg.label})
                            </h2>
                            {activePrompt?.variant_tag && (
                                <div className="inline-flex items-center gap-2 bg-voxel-trough border border-voxel-bevel-hi px-3 py-1 rounded-none text-sm text-success font-bold">
                                    <span>Active Runtime:</span>
                                    <code className="font-mono font-bold break-all">
                                        {activePrompt.variant_tag}
                                    </code>
                                </div>
                            )}
                        </div>

                        <div className="flex flex-wrap gap-6 items-start min-w-0 w-full">
                            <VariantSidebar
                                experiments={trackExperiments}
                                selectedExpId={selectedExperiment?.id ?? null}
                                activePromptTag={activePrompt?.variant_tag}
                                onSelectExp={(id) => setSelectedExpId(id)}
                            />

                            {selectedExperiment && (
                                <div className="w-full flex-[3] basis-96 min-w-0 flex flex-col gap-4">
                                    <SelectedVariantHeader
                                        experiment={selectedExperiment}
                                        isActiveVariant={
                                            selectedExperiment.variant_tag ===
                                            activePrompt?.variant_tag
                                        }
                                    />

                                    <StockPickerScoreBreakdown experiment={selectedExperiment} />

                                    <ResearchRationaleCard experiment={selectedExperiment} />

                                    <PromptChanges
                                        experiment={selectedExperiment}
                                        parentExperiment={parentExperiment}
                                    />

                                    <SegmentedPromptInspector
                                        promptContent={selectedExperiment.prompt_content}
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
