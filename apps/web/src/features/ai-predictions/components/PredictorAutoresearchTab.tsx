import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    SectionHeading,
    SubHeading,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import { CognitiveToolboxCard } from '~/features/autoresearch/components/CognitiveToolboxCard';
import { PromptBlocksCard } from '~/features/autoresearch/components/PromptBlocksCard';
import { PromptChanges } from '~/features/autoresearch/components/PromptChanges';
import { ResearchRationaleCard } from '~/features/autoresearch/components/ResearchRationaleCard';
import { isExperimentColdStart } from '~/features/autoresearch/utils/coldStart';
import { splitPromptSections } from '~/features/autoresearch/utils/promptSections';
import type { SectorPrediction } from '../api/fetch-predictions';
import {
    calculateTrackBaselineScore,
    computeModelTrackSummaries,
    filterExperimentsByTrack,
    filterPredictionsByTrack,
    findTrackActiveVariant,
    getAvailableTracks,
    getExperimentTrackInfo,
    LEGACY_TRACK_CONFIG,
    SECTOR_MODEL_TRACKS,
    type SectorTrackConfig,
    type SectorTrackId,
} from '../lib/sector-tracks';
import { formatStableDate } from './PredictionFeedCard';
import { PredictorModelOverviewGrid } from './PredictorModelOverviewGrid';
import { PredictorTrackTabs } from './PredictorTrackTabs';
import { SectorScoreBreakdown } from './SectorScoreBreakdown';

export const DEFAULT_SECTOR_PREDICTOR_TOOLS = [
    'get_historical_correlation',
    'get_sector_fundamentals',
    'get_global_macro_context',
    'fetch_daily_newsletter',
    'get_macro_economic_series',
    'run_stock_screener',
    'find_uncorrelated_assets',
    'get_volatility_metrics',
];

export interface PredictorAutoresearchTabProps {
    experimentsList: PromptExperiment[];
    predictions?: SectorPrediction[];
    initialTrack?: SectorTrackId;
}

export function PredictorStatusBadge({ status }: { status: string }) {
    switch (status) {
        case 'active':
            return (
                <Badge colorScheme="success" variant="soft">
                    Active
                </Badge>
            );
        case 'baseline':
            return (
                <Badge colorScheme="accent" variant="soft">
                    Baseline
                </Badge>
            );
        case 'saved':
        case 'kept':
            return (
                <Badge colorScheme="neutral" variant="soft">
                    Saved
                </Badge>
            );
        case 'discarded':
            return (
                <Badge colorScheme="neutral" variant="soft">
                    Discarded
                </Badge>
            );
        case 'crashed':
            return (
                <Badge colorScheme="danger" variant="soft">
                    Crashed
                </Badge>
            );
        default:
            return <Badge>{status}</Badge>;
    }
}

interface PredictorExperimentRowProps {
    exp: PromptExperiment;
    isSelected: boolean;
    onSelect: (id: string) => void;
    showModelBadge?: boolean;
}

function PredictorExperimentRow({
    exp,
    isSelected,
    onSelect,
    showModelBadge = true,
}: PredictorExperimentRowProps) {
    const score = exp.metrics?.score;
    const formattedScore = score !== undefined && score !== null ? score.toFixed(3) : 'N/A';
    const trackInfo = getExperimentTrackInfo(exp);

    return (
        <TableRow
            onClick={() => onSelect(exp.id)}
            className={`cursor-pointer border-slate-800 hover:bg-slate-800/30 ${
                isSelected ? 'bg-slate-800/50' : ''
            }`}
        >
            {showModelBadge && (
                <TableCell>
                    <span
                        className={`inline-block px-2 py-0.5 text-xs font-normal rounded-none ${trackInfo.badgeClass}`}
                    >
                        {trackInfo.label}
                    </span>
                </TableCell>
            )}
            <TableCell className="font-mono text-boxel-ink font-normal text-xs break-all max-w-[120px]">
                {exp.variant_tag}
            </TableCell>
            <TableCell>
                <div className="flex items-center gap-1.5 flex-wrap">
                    <Badge variant={exp.experiment_type === 'baseline' ? 'solid' : 'soft'}>
                        {exp.experiment_type}
                    </Badge>
                    {isExperimentColdStart(exp) && (
                        <Badge variant="soft" colorScheme="warning" size="xs">
                            From 0
                        </Badge>
                    )}
                </div>
            </TableCell>
            <TableCell
                className={`font-bold ${
                    formattedScore === 'N/A'
                        ? 'text-boxel-muted font-normal'
                        : score > 0
                          ? 'text-emerald-400'
                          : 'text-rose-400'
                }`}
            >
                {formattedScore}
            </TableCell>
            <TableCell className="text-slate-400 text-xs whitespace-nowrap">
                {formatStableDate(exp.week_start).split(',')[0]} -{' '}
                {formatStableDate(exp.week_end).split(',')[0]}
            </TableCell>
            <TableCell>
                <PredictorStatusBadge status={exp.status} />
            </TableCell>
        </TableRow>
    );
}

function PredictorTrackHeaderCards({
    trackConfig,
    baselineScore,
    activeVariant,
}: {
    trackConfig: SectorTrackConfig | null;
    baselineScore: string;
    activeVariant: string;
}) {
    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch">
            <div className="bg-boxel-surface border border-boxel-bevel-hi rounded-none p-6 flex flex-col justify-between h-full">
                <div className="flex justify-between items-start">
                    <h2 className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        {trackConfig?.label ?? 'Model'} All-Time Baseline Score
                    </h2>
                    <span
                        className={`px-2 py-0.5 text-xs font-normal rounded-none ${
                            trackConfig?.badgeClass ?? ''
                        }`}
                    >
                        {trackConfig?.shortLabel}
                    </span>
                </div>
                <div className="text-lg font-bold text-emerald-400 font-mono">{baselineScore}</div>
                <p className="text-boxel-muted text-xs font-normal">
                    Ratchet high-water mark for {trackConfig?.label ?? 'this model track'}
                </p>
            </div>

            <div className="bg-boxel-surface border border-boxel-bevel-hi rounded-none p-6 flex flex-col justify-between h-full">
                <div className="flex justify-between items-start">
                    <h2 className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        {trackConfig?.label ?? 'Model'} Active Prompt
                    </h2>
                    <span
                        className={`px-2 py-0.5 text-xs font-normal rounded-none ${
                            trackConfig?.badgeClass ?? ''
                        }`}
                    >
                        {trackConfig?.shortLabel}
                    </span>
                </div>
                <div className="text-lg font-bold text-accent font-mono">{activeVariant}</div>
                <p className="text-boxel-muted text-xs font-normal">
                    The currently deployed strategy for {trackConfig?.label ?? 'this model track'}
                </p>
            </div>
        </div>
    );
}

function PredictorPromptInspector({
    promptContent,
    variantTag,
}: {
    promptContent: string;
    variantTag: string;
}) {
    const { header, mutable, footer, isSplit } = splitPromptSections(promptContent);

    if (!isSplit) {
        return (
            <Card className="p-6 bg-slate-800/20 border-slate-700/50 flex flex-col gap-4 rounded-none shadow-sm">
                <SectionHeading className="text-slate-200">The Predictor Prompt</SectionHeading>
                <div className="relative group">
                    <pre className="p-4 bg-slate-950 text-slate-300 rounded-none overflow-x-auto text-xs font-mono leading-relaxed border border-slate-800 max-h-96 overflow-y-auto shadow-sm whitespace-pre-wrap break-words">
                        {promptContent}
                    </pre>
                </div>
            </Card>
        );
    }

    return (
        <div className="flex flex-col gap-4">
            {header && (
                <div className="p-4 bg-boxel-canvas border border-boxel-bevel-hi rounded-none flex flex-col gap-2">
                    <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        Frozen System Constraints (Header)
                    </div>
                    <pre className="whitespace-pre-wrap font-mono text-xs font-normal text-boxel-muted max-h-48 overflow-y-auto">
                        {header}
                    </pre>
                </div>
            )}

            <div className="p-4 bg-boxel-trough border border-emerald-500/30 rounded-none flex flex-col gap-2">
                <div className="flex items-center justify-between">
                    <div className="text-sm font-bold text-emerald-400 uppercase tracking-wider">
                        Mutable Analytical Strategies (Evolved by Autoresearch)
                    </div>
                    <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-none font-mono font-normal">
                        v{variantTag}
                    </span>
                </div>
                <pre className="whitespace-pre-wrap font-mono text-xs font-normal text-emerald-100 max-h-96 overflow-y-auto">
                    {mutable}
                </pre>
            </div>

            {footer && (
                <div className="p-4 bg-boxel-canvas border border-boxel-bevel-hi rounded-none flex flex-col gap-2">
                    <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        Frozen Output Schema (Footer)
                    </div>
                    <pre className="whitespace-pre-wrap font-mono text-xs font-normal text-boxel-muted max-h-48 overflow-y-auto">
                        {footer}
                    </pre>
                </div>
            )}
        </div>
    );
}

function PredictorExperimentDetailsPane({
    selectedExperiment,
    parentExperiment,
    trackPredictions,
    numericBaselineScore,
}: {
    selectedExperiment: PromptExperiment | null;
    parentExperiment: PromptExperiment | null;
    trackPredictions: SectorPrediction[];
    numericBaselineScore: number | null;
}) {
    if (!selectedExperiment) {
        return (
            <div className="h-full flex items-center justify-center p-12 border-2 border-dashed border-slate-800 rounded-none text-slate-500 text-xs font-normal shadow-sm">
                Select an experiment to view details
            </div>
        );
    }

    const trkInfo = getExperimentTrackInfo(selectedExperiment);
    const researchOutput = selectedExperiment.research_output as {
        selected_tools?: string[];
        selected_prompt_blocks?: string[];
    } | null;

    const parentResearchOutput = parentExperiment?.research_output as {
        selected_tools?: string[];
        selected_prompt_blocks?: string[];
    } | null;

    return (
        <div className="space-y-6">
            <div className="flex items-center space-x-4 px-2">
                <SectionHeading className="text-slate-200">Experiment Details</SectionHeading>
                <div className="h-px flex-1 bg-slate-800" />
                <span className={`px-2 py-0.5 text-xs font-bold rounded ${trkInfo.badgeClass}`}>
                    {trkInfo.label}
                </span>
                <span className="text-sm font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {selectedExperiment.variant_tag}
                </span>
            </div>

            {/* Sector Score Breakdown & Math Audit */}
            <SectorScoreBreakdown
                experiment={selectedExperiment}
                predictions={trackPredictions}
                baselineScore={numericBaselineScore}
            />

            {/* Research Rationale, Confidence Gauge, and Hypothesis */}
            <ResearchRationaleCard experiment={selectedExperiment} />

            {/* Cognitive Tools Used by Model / Researcher */}
            <CognitiveToolboxCard
                selectedTools={researchOutput?.selected_tools || DEFAULT_SECTOR_PREDICTOR_TOOLS}
                parentSelectedTools={
                    parentResearchOutput?.selected_tools ||
                    (parentExperiment ? DEFAULT_SECTOR_PREDICTOR_TOOLS : undefined)
                }
                title="Cognitive Toolbox Configuration"
                subtitle="Contextual data feeds and analytical tools provided to the sector predictor model."
            />

            {/* Active Prompt Blocks */}
            <PromptBlocksCard
                selectedBlocks={researchOutput?.selected_prompt_blocks}
                parentSelectedBlocks={parentResearchOutput?.selected_prompt_blocks}
            />

            {/* Metadata Row & Change Description */}
            <Card className="p-6 bg-boxel-surface border-boxel-bevel-hi flex flex-col gap-6">
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-4 p-4 bg-boxel-trough rounded-none border border-boxel-bevel-hi text-xs font-normal items-stretch">
                    <div>
                        <div className="text-boxel-muted text-sm font-bold uppercase tracking-wider mb-1">
                            Experiment Type
                        </div>
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <Badge
                                variant={
                                    selectedExperiment.experiment_type === 'baseline'
                                        ? 'solid'
                                        : 'soft'
                                }
                            >
                                {selectedExperiment.experiment_type}
                            </Badge>
                            {isExperimentColdStart(selectedExperiment) && (
                                <Badge variant="soft" colorScheme="warning" size="xs">
                                    From 0
                                </Badge>
                            )}
                        </div>
                    </div>
                    <div>
                        <div className="text-boxel-muted text-sm font-bold uppercase tracking-wider mb-1">
                            Active Period
                        </div>
                        <div className="text-boxel-ink font-normal">
                            {formatStableDate(selectedExperiment.week_start)} -{' '}
                            {formatStableDate(selectedExperiment.week_end)}
                        </div>
                    </div>
                    <div>
                        <div className="text-boxel-muted text-sm font-bold uppercase tracking-wider mb-1">
                            Parent Variant
                        </div>
                        <div className="text-boxel-ink font-mono font-normal">
                            {selectedExperiment.parent_tag || (
                                <span className="text-boxel-muted italic">None (Root)</span>
                            )}
                        </div>
                    </div>
                    <div>
                        <div className="text-boxel-muted text-sm font-bold uppercase tracking-wider mb-1">
                            Created At
                        </div>
                        <div className="text-boxel-ink font-normal">
                            {formatStableDate(selectedExperiment.created_at)}
                        </div>
                    </div>
                </div>

                <div className="flex flex-col gap-2">
                    <SubHeading className="text-boxel-ink">Change Description</SubHeading>
                    <p className="text-boxel-muted italic text-xs font-normal">
                        "{selectedExperiment.change_description || 'No description provided.'}"
                    </p>
                </div>
            </Card>

            {/* Prompt Changes */}
            <PromptChanges experiment={selectedExperiment} parentExperiment={parentExperiment} />

            {/* Segmented Prompt Inspector */}
            <PredictorPromptInspector
                promptContent={selectedExperiment.prompt_content}
                variantTag={selectedExperiment.variant_tag}
            />
        </div>
    );
}

export function PredictorAutoresearchTab({
    experimentsList,
    predictions = [],
    initialTrack = 'all',
}: PredictorAutoresearchTabProps) {
    const [activeTrack, setActiveTrack] = useState<SectorTrackId>(initialTrack);
    const [selectedExpId, setSelectedExpId] = useState<string | null>(null);

    const availableTracks = useMemo(() => getAvailableTracks(experimentsList), [experimentsList]);

    const trackSummaries = useMemo(
        () => computeModelTrackSummaries(experimentsList),
        [experimentsList],
    );

    const filteredExperiments = useMemo(
        () => filterExperimentsByTrack(experimentsList, activeTrack),
        [experimentsList, activeTrack],
    );

    const trackPredictions = useMemo(
        () => filterPredictionsByTrack(predictions, activeTrack),
        [predictions, activeTrack],
    );

    const selectedExperiment = useMemo(() => {
        if (selectedExpId) {
            const found = filteredExperiments.find((e) => e.id === selectedExpId);
            if (found) return found;
        }
        return filteredExperiments.length > 0 ? filteredExperiments[0] : null;
    }, [filteredExperiments, selectedExpId]);

    const parentExperiment = useMemo(() => {
        if (!selectedExperiment?.parent_tag) return null;
        return experimentsList.find((e) => e.variant_tag === selectedExperiment.parent_tag) || null;
    }, [selectedExperiment, experimentsList]);

    const activeTrackConfig = useMemo(() => {
        if (activeTrack === 'all') return null;
        if (activeTrack === 'legacy') return LEGACY_TRACK_CONFIG;
        return SECTOR_MODEL_TRACKS.find((t) => t.id === activeTrack) || null;
    }, [activeTrack]);

    const trackBaselineScore = useMemo(
        () => calculateTrackBaselineScore(filteredExperiments),
        [filteredExperiments],
    );

    const trackActiveVariant = useMemo(
        () => findTrackActiveVariant(filteredExperiments),
        [filteredExperiments],
    );

    const numericBaselineScore = useMemo(() => {
        return trackBaselineScore !== 'N/A' ? Number.parseFloat(trackBaselineScore) : null;
    }, [trackBaselineScore]);

    const handleSelectTrack = (trackId: SectorTrackId) => {
        setActiveTrack(trackId);
        const newFiltered = filterExperimentsByTrack(experimentsList, trackId);
        setSelectedExpId(newFiltered.length > 0 ? newFiltered[0].id : null);
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-300">
            {/* Model Track Selector Tabs */}
            <PredictorTrackTabs
                tracks={availableTracks}
                activeTrack={activeTrack}
                onSelectTrack={handleSelectTrack}
                experiments={experimentsList}
            />

            {/* Model-specific vs Multi-model Overview Cards */}
            {activeTrack === 'all' ? (
                <PredictorModelOverviewGrid
                    summaries={trackSummaries}
                    onSelectTrack={handleSelectTrack}
                />
            ) : (
                <PredictorTrackHeaderCards
                    trackConfig={activeTrackConfig}
                    baselineScore={trackBaselineScore}
                    activeVariant={trackActiveVariant}
                />
            )}

            <Card className="p-6 bg-slate-800/20 border-slate-700/50 space-y-4">
                <SectionHeading className="text-slate-200 text-lg">
                    Sector Ratchet Scoring Formula
                </SectionHeading>
                <p className="text-slate-400 text-sm leading-relaxed">
                    Evaluates weekly sector calls across 11 S&P sectors, rewarding relative
                    percentile ranking and benchmark outperformance while docking uncalibrated
                    probability confidence:
                </p>
                <div className="py-4 px-6 bg-boxel-trough border border-boxel-bevel-hi rounded-none flex flex-col items-center justify-center gap-2">
                    <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        Ratchet Baseline Formula
                    </div>
                    <div className="text-lg font-mono font-bold text-boxel-ink text-center leading-relaxed">
                        Score = Base Percentile + S&amp;P Alpha Bonus − (Mean Brier × 50.0)
                    </div>
                </div>
            </Card>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                {/* Sidebar: List of Experiments */}
                <div className="xl:col-span-4 flex flex-col gap-6">
                    <div className="flex items-center justify-between px-2">
                        <SectionHeading className="text-boxel-ink">
                            {activeTrack === 'all'
                                ? 'All Experiments'
                                : `${activeTrackConfig?.shortLabel ?? ''} History`}
                        </SectionHeading>
                        <span className="text-xs font-normal text-boxel-muted uppercase tracking-widest">
                            {filteredExperiments.length} Experiments
                        </span>
                    </div>
                    <div className="bg-boxel-trough border border-boxel-bevel-hi rounded-none overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow isHoverable={false} className="border-slate-800">
                                    {activeTrack === 'all' && (
                                        <TableHead className="text-slate-300">Model</TableHead>
                                    )}
                                    <TableHead className="text-slate-300">Variant</TableHead>
                                    <TableHead className="text-slate-300">Type</TableHead>
                                    <TableHead className="text-slate-300">Score</TableHead>
                                    <TableHead className="text-slate-300">Period</TableHead>
                                    <TableHead className="text-slate-300">Status</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredExperiments.map((exp) => (
                                    <PredictorExperimentRow
                                        key={exp.id}
                                        exp={exp}
                                        isSelected={selectedExperiment?.id === exp.id}
                                        onSelect={setSelectedExpId}
                                        showModelBadge={activeTrack === 'all'}
                                    />
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </div>

                {/* Details View */}
                <div className="xl:col-span-8 space-y-6">
                    <PredictorExperimentDetailsPane
                        selectedExperiment={selectedExperiment}
                        parentExperiment={parentExperiment}
                        trackPredictions={trackPredictions}
                        numericBaselineScore={numericBaselineScore}
                    />
                </div>
            </div>
        </div>
    );
}
