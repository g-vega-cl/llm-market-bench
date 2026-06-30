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
import { diffLines } from '~/features/autoresearch/utils/diff';
import type { SectorPrediction } from '../api/fetch-predictions';
import { AIPredictionChart } from '../components/AIPredictionChart';

function formatStableDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    const parts = dateStr.split('T')[0].split('-');
    if (parts.length === 3) {
        const year = parts[0];
        const monthStr = parts[1];
        const dayStr = parts[2];
        const months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ];
        const monthIndex = parseInt(monthStr, 10) - 1;
        if (monthIndex >= 0 && monthIndex < 12) {
            const day = parseInt(dayStr, 10);
            return `${months[monthIndex]} ${day}, ${year}`;
        }
    }
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        timeZone: 'America/New_York',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
    });
}

export interface AIPredictionsPageProps {
    initialData: SectorPrediction[];
    experiments: PromptExperiment[];
    refreshFn: () => Promise<{ predictions: SectorPrediction[]; experiments: PromptExperiment[] }>;
}

export function AIPredictionsPage({ initialData, experiments, refreshFn }: AIPredictionsPageProps) {
    const [data, setData] = useState<SectorPrediction[]>(initialData);
    const [experimentsList, setExperimentsList] = useState<PromptExperiment[]>(experiments);
    const [loading, setLoading] = useState(false);
    const [timeframeFilter, setTimeframeFilter] = useState<'7d' | '30d' | '60d' | '90d' | 'all'>(
        '7d',
    );
    const [activeTab, setActiveTab] = useState<'arena' | 'autoresearch'>('arena');
    const [selectedExpId, setSelectedExpId] = useState<string | null>(null);

    const handleRefresh = async () => {
        setLoading(true);
        try {
            const newData = await refreshFn();
            setData(newData.predictions);
            setExperimentsList(newData.experiments);
        } finally {
            setLoading(false);
        }
    };

    // Calculate aggregated metrics
    const deepSeekData = data.filter((d) => d.model_name.startsWith('deepseek'));
    const miniMaxData = data.filter((d) => d.model_name === 'MiniMax-M3');

    const avgScore = (items: SectorPrediction[]) => {
        const evaluated = items.filter(
            (i) =>
                i.status === 'evaluated' &&
                i.sector_percentile_score != null &&
                i.pair_percentile_score != null,
        );
        if (evaluated.length === 0) return 0;
        const sum = evaluated.reduce((acc, curr) => {
            const avg =
                ((curr.sector_percentile_score || 0) + (curr.pair_percentile_score || 0)) / 2;
            return acc + avg;
        }, 0);
        return (sum / evaluated.length).toFixed(1);
    };

    const chartFilteredData =
        timeframeFilter === 'all' ? data : data.filter((d) => d.timeframe === timeframeFilter);

    // Auto-Research computations
    const baselineScore = useMemo(() => {
        const scores = experimentsList
            .map((exp) => exp.metrics?.score)
            .filter((s): s is number => s !== undefined && s !== null);
        if (scores.length === 0) return 'N/A';
        return Math.max(...scores).toFixed(4);
    }, [experimentsList]);

    const activeVariant = useMemo(() => {
        return experimentsList.find((exp) => exp.status === 'active')?.variant_tag || 'N/A';
    }, [experimentsList]);

    const selectedExperiment = useMemo(() => {
        if (selectedExpId) {
            return experimentsList.find((e) => e.id === selectedExpId) || null;
        }
        return experimentsList.length > 0 ? experimentsList[0] : null;
    }, [experimentsList, selectedExpId]);

    const parentExperiment = useMemo(() => {
        if (!selectedExperiment?.parent_tag) return null;
        return experimentsList.find((e) => e.variant_tag === selectedExperiment.parent_tag) || null;
    }, [selectedExperiment, experimentsList]);

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                        AI Sector Predictions Arena
                    </h1>
                    <p className="text-slate-400 mt-2 text-lg">
                        DeepSeek Flash vs MiniMax-M3: Predicting the best sectors and uncorrelated
                        pairs.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={handleRefresh}
                    disabled={loading}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-semibold"
                >
                    {loading ? 'Refreshing...' : 'Refresh Data'}
                </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-slate-700/60">
                <button
                    type="button"
                    onClick={() => setActiveTab('arena')}
                    className={`py-3 px-6 font-semibold border-b-2 text-sm transition-all duration-200 ${
                        activeTab === 'arena'
                            ? 'border-blue-500 text-blue-400'
                            : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                >
                    Arena Dashboard
                </button>
                <button
                    type="button"
                    onClick={() => setActiveTab('autoresearch')}
                    className={`py-3 px-6 font-semibold border-b-2 text-sm transition-all duration-200 ${
                        activeTab === 'autoresearch'
                            ? 'border-emerald-500 text-emerald-400'
                            : 'border-transparent text-slate-400 hover:text-slate-200'
                    }`}
                >
                    Prompt Auto-Research
                </button>
            </div>

            {activeTab === 'arena' ? (
                <div className="space-y-8 animate-in fade-in duration-300">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                            <h2 className="text-xl font-bold text-blue-400 mb-2">
                                DeepSeek Models
                            </h2>
                            <div className="text-3xl font-light text-white mb-1">
                                {avgScore(deepSeekData)}{' '}
                                <span className="text-sm text-slate-400">Avg Percentile</span>
                            </div>
                            <p className="text-slate-400 text-sm">
                                {deepSeekData.length} predictions made
                            </p>
                        </div>
                        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                            <h2 className="text-xl font-bold text-emerald-400 mb-2">MiniMax-M3</h2>
                            <div className="text-3xl font-light text-white mb-1">
                                {avgScore(miniMaxData)}{' '}
                                <span className="text-sm text-slate-400">Avg Percentile</span>
                            </div>
                            <p className="text-slate-400 text-sm">
                                {miniMaxData.length} predictions made
                            </p>
                        </div>
                    </div>

                    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                            <h3 className="text-xl font-bold text-white">
                                Historical Track Record
                            </h3>
                            <div className="flex bg-slate-900/60 p-1 rounded-lg border border-slate-700">
                                {(['7d', '30d', '60d', '90d', 'all'] as const).map((tf) => (
                                    <button
                                        key={tf}
                                        type="button"
                                        onClick={() => setTimeframeFilter(tf)}
                                        className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                                            timeframeFilter === tf
                                                ? 'bg-slate-800 text-white shadow-sm'
                                                : 'text-slate-400 hover:text-slate-200'
                                        }`}
                                    >
                                        {tf.toUpperCase()}
                                    </button>
                                ))}
                            </div>
                        </div>
                        {chartFilteredData.length > 0 ? (
                            <AIPredictionChart data={chartFilteredData} />
                        ) : (
                            <div className="h-[300px] flex items-center justify-center text-slate-400">
                                No predictions available for this timeframe.
                            </div>
                        )}
                    </div>

                    <div className="space-y-4">
                        <h3 className="text-xl font-bold text-white">Recent Predictions</h3>
                        <div className="grid grid-cols-1 gap-4">
                            {data.slice(0, 10).map((pred) => (
                                <div
                                    key={pred.id}
                                    className="bg-slate-800/30 border border-slate-700 rounded-lg p-5"
                                >
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex items-center gap-3">
                                            <span
                                                className={`px-2 py-1 text-xs font-semibold rounded-md ${
                                                    pred.model_name.startsWith('deepseek')
                                                        ? 'bg-blue-500/20 text-blue-400'
                                                        : 'bg-emerald-500/20 text-emerald-400'
                                                }`}
                                            >
                                                {pred.model_name}
                                            </span>
                                            <span className="text-slate-400 text-sm">
                                                Target:{' '}
                                                {new Date(pred.target_date).toLocaleDateString()} (
                                                {pred.timeframe})
                                            </span>
                                        </div>
                                        <span
                                            className={`px-2 py-1 text-xs rounded-full ${
                                                pred.status === 'evaluated'
                                                    ? 'bg-green-500/20 text-green-400'
                                                    : 'bg-yellow-500/20 text-yellow-400'
                                            }`}
                                        >
                                            {pred.status.toUpperCase()}
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div className="bg-slate-900/50 rounded-lg p-3">
                                            <div className="text-sm text-slate-400 mb-1">
                                                Top Sector
                                            </div>
                                            <div className="text-lg font-bold text-white">
                                                {pred.predicted_sector}
                                            </div>
                                            {pred.status === 'evaluated' && (
                                                <div className="text-sm text-emerald-400 mt-1">
                                                    Score:{' '}
                                                    {pred.sector_percentile_score?.toFixed(1)}
                                                </div>
                                            )}
                                        </div>
                                        <div className="bg-slate-900/50 rounded-lg p-3">
                                            <div className="text-sm text-slate-400 mb-1">
                                                Uncorrelated Pair
                                            </div>
                                            <div className="text-lg font-bold text-white">
                                                {pred.predicted_pair.join(' + ')}
                                            </div>
                                            {pred.status === 'evaluated' && (
                                                <div className="text-sm text-emerald-400 mt-1">
                                                    Score: {pred.pair_percentile_score?.toFixed(1)}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div>
                                        <div className="text-sm font-medium text-slate-300 mb-1">
                                            Reasoning
                                        </div>
                                        <p className="text-sm text-slate-400 bg-slate-900/50 p-3 rounded-lg leading-relaxed">
                                            {pred.reasoning}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            ) : (
                <PredictorAutoresearchTab
                    experimentsList={experimentsList}
                    baselineScore={baselineScore}
                    activeVariant={activeVariant}
                    selectedExperiment={selectedExperiment}
                    setSelectedExpId={setSelectedExpId}
                    parentExperiment={parentExperiment}
                />
            )}
        </div>
    );
}

interface PredictorAutoresearchTabProps {
    experimentsList: PromptExperiment[];
    baselineScore: string;
    activeVariant: string;
    selectedExperiment: PromptExperiment | null;
    setSelectedExpId: (id: string | null) => void;
    parentExperiment: PromptExperiment | null;
}

function PredictorAutoresearchTab({
    experimentsList,
    baselineScore,
    activeVariant,
    selectedExperiment,
    setSelectedExpId,
    parentExperiment,
}: PredictorAutoresearchTabProps) {
    return (
        <div className="space-y-8 animate-in fade-in duration-300">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 backdrop-blur-sm">
                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        All-Time Baseline Score
                    </h2>
                    <div className="text-3xl font-black text-emerald-400 font-mono">
                        {baselineScore}
                    </div>
                    <p className="text-slate-400 text-xs mt-2">
                        The highest score achieved by evaluated prompt variants
                    </p>
                </div>
                <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-6 backdrop-blur-sm">
                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Active Prompt
                    </h2>
                    <div className="text-3xl font-black text-blue-400 font-mono">
                        {activeVariant}
                    </div>
                    <p className="text-slate-400 text-xs mt-2">
                        The active prompt variant for the current weekly cycle
                    </p>
                </div>
            </div>

            <Card className="p-6 bg-slate-800/20 border-slate-700/50 space-y-4">
                <SectionHeading className="text-slate-200 text-lg">
                    Predictor Scoring Formula
                </SectionHeading>
                <p className="text-slate-400 text-sm leading-relaxed">
                    Every weekly prediction is evaluated against the actual performance of the
                    sector ETF universe. The score is calculated as the average of the selected
                    sector's percentile return score and the uncorrelated pair's percentile return
                    score:
                </p>
                <div className="py-4 px-6 bg-slate-900/60 border border-slate-700/50 rounded-xl flex flex-col items-center justify-center space-y-2">
                    <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Weekly Predictor Score
                    </div>
                    <div className="text-xl font-mono font-bold text-slate-200 text-center leading-relaxed">
                        Average( Sector Percentile + Pair Percentile )
                    </div>
                </div>
            </Card>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
                {/* Sidebar: List of Experiments */}
                <div className="xl:col-span-4 space-y-6">
                    <div className="flex items-center justify-between px-2">
                        <SectionHeading className="text-slate-200">History</SectionHeading>
                        <span className="text-xs font-medium text-slate-400 uppercase tracking-widest">
                            {experimentsList.length} Experiments
                        </span>
                    </div>
                    <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow isHoverable={false} className="border-slate-800">
                                    <TableHead className="text-slate-300">Variant</TableHead>
                                    <TableHead className="text-slate-300">Type</TableHead>
                                    <TableHead className="text-slate-300">Score</TableHead>
                                    <TableHead className="text-slate-300">Period</TableHead>
                                    <TableHead className="text-slate-300">Status</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {experimentsList.map((exp) => (
                                    <PredictorExperimentRow
                                        key={exp.id}
                                        exp={exp}
                                        isSelected={selectedExperiment?.id === exp.id}
                                        onSelect={setSelectedExpId}
                                    />
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </div>

                {/* Details View */}
                <div className="xl:col-span-8 space-y-6">
                    {selectedExperiment ? (
                        <div className="space-y-6">
                            <div className="flex items-center space-x-4 px-2">
                                <SectionHeading className="text-slate-200">
                                    Experiment Details
                                </SectionHeading>
                                <div className="h-px flex-1 bg-slate-800" />
                                <span className="text-sm font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                    {selectedExperiment.variant_tag}
                                </span>
                            </div>

                            <Card className="p-6 bg-slate-800/20 border-slate-700/50 space-y-6">
                                {/* Metadata Row */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-900/40 rounded-xl border border-slate-800/50 text-xs">
                                    <div>
                                        <div className="text-slate-500 font-semibold uppercase tracking-wider mb-1">
                                            Experiment Type
                                        </div>
                                        <Badge
                                            variant={
                                                selectedExperiment.experiment_type === 'baseline'
                                                    ? 'solid'
                                                    : 'soft'
                                            }
                                        >
                                            {selectedExperiment.experiment_type}
                                        </Badge>
                                    </div>
                                    <div>
                                        <div className="text-slate-500 font-semibold uppercase tracking-wider mb-1">
                                            Active Period
                                        </div>
                                        <div className="text-slate-300 font-medium">
                                            {formatStableDate(selectedExperiment.week_start)} -{' '}
                                            {formatStableDate(selectedExperiment.week_end)}
                                        </div>
                                    </div>
                                    {selectedExperiment.parent_tag ? (
                                        <div>
                                            <div className="text-slate-500 font-semibold uppercase tracking-wider mb-1">
                                                Parent Variant
                                            </div>
                                            <div className="text-slate-300 font-mono font-medium">
                                                {selectedExperiment.parent_tag}
                                            </div>
                                        </div>
                                    ) : (
                                        <div>
                                            <div className="text-slate-500 font-semibold uppercase tracking-wider mb-1">
                                                Parent Variant
                                            </div>
                                            <div className="text-slate-500 italic">None (Root)</div>
                                        </div>
                                    )}
                                    <div>
                                        <div className="text-slate-500 font-semibold uppercase tracking-wider mb-1">
                                            Created At
                                        </div>
                                        <div className="text-slate-300 font-medium">
                                            {formatStableDate(selectedExperiment.created_at)}
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <SubHeading className="text-slate-300">
                                        Change Description
                                    </SubHeading>
                                    <p className="text-slate-400 italic text-sm">
                                        "
                                        {selectedExperiment.change_description ||
                                            'No description provided.'}
                                        "
                                    </p>
                                </div>

                                {selectedExperiment.research_output?.hypothesis && (
                                    <div className="space-y-2">
                                        <SubHeading className="text-slate-300">
                                            Hypothesis
                                        </SubHeading>
                                        <div className="p-4 bg-slate-900/60 rounded-lg text-sm text-slate-300 border border-slate-800">
                                            {selectedExperiment.research_output.hypothesis}
                                        </div>
                                    </div>
                                )}

                                {selectedExperiment.research_output?.thought_process && (
                                    <div className="space-y-2">
                                        <SubHeading className="text-slate-300">
                                            Meta-Researcher Logic
                                        </SubHeading>
                                        <div className="whitespace-pre-wrap text-sm text-slate-400 bg-slate-900/40 p-4 rounded-lg leading-relaxed border border-slate-800/50">
                                            {selectedExperiment.research_output.thought_process}
                                        </div>
                                    </div>
                                )}
                            </Card>

                            <PredictorPromptChanges
                                experiment={selectedExperiment}
                                parentExperiment={parentExperiment}
                            />

                            <Card className="p-6 bg-slate-800/20 border-slate-700/50 space-y-4">
                                <SectionHeading className="text-slate-200">
                                    The Predictor Prompt
                                </SectionHeading>
                                <div className="relative group">
                                    <pre className="p-4 bg-slate-950 text-slate-300 rounded-xl overflow-x-auto text-xs font-mono leading-relaxed border border-slate-850 max-h-[500px] overflow-y-auto">
                                        {selectedExperiment.prompt_content}
                                    </pre>
                                </div>
                            </Card>
                        </div>
                    ) : (
                        <div className="h-full flex items-center justify-center p-12 border-2 border-dashed border-slate-800 rounded-3xl text-slate-500">
                            Select an experiment to view details
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

interface PredictorExperimentRowProps {
    exp: PromptExperiment;
    isSelected: boolean;
    onSelect: (id: string) => void;
}

function PredictorExperimentRow({ exp, isSelected, onSelect }: PredictorExperimentRowProps) {
    const score = exp.metrics?.score;
    const formattedScore = score !== undefined && score !== null ? score.toFixed(3) : 'N/A';
    return (
        <TableRow
            onClick={() => onSelect(exp.id)}
            className={`cursor-pointer border-slate-800 hover:bg-slate-800/30 ${
                isSelected ? 'bg-slate-800/50' : ''
            }`}
        >
            <TableCell className="font-mono text-slate-200 font-medium text-xs break-all max-w-[120px]">
                {exp.variant_tag}
            </TableCell>
            <TableCell>
                <Badge variant={exp.experiment_type === 'baseline' ? 'solid' : 'soft'}>
                    {exp.experiment_type}
                </Badge>
            </TableCell>
            <TableCell
                className={`font-bold ${
                    formattedScore === 'N/A'
                        ? 'text-slate-500 font-medium'
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

function PredictorStatusBadge({ status }: { status: string }) {
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

interface PredictorPromptChangesProps {
    experiment: PromptExperiment;
    parentExperiment: PromptExperiment | null;
}

function PredictorPromptChanges({ experiment, parentExperiment }: PredictorPromptChangesProps) {
    const [showChangesOnly, setShowChangesOnly] = useState(true);

    const diffResult = useMemo(() => {
        if (!parentExperiment) return [];
        return diffLines(parentExperiment.prompt_content, experiment.prompt_content);
    }, [parentExperiment, experiment.prompt_content]);

    const hasChanges = useMemo(() => {
        return diffResult.some((item) => item.added || item.removed);
    }, [diffResult]);

    const filteredChanges = useMemo(() => {
        if (!showChangesOnly) return diffResult;
        return diffResult.filter((item) => item.added || item.removed);
    }, [diffResult, showChangesOnly]);

    if (!parentExperiment) {
        const isBaseline = experiment.experiment_type === 'baseline';
        return (
            <Card className="p-6 bg-slate-800/10 border-dashed border-slate-800">
                <div className="flex flex-col items-center justify-center text-center space-y-2 py-4">
                    <span className="text-xl">🌱</span>
                    <h3 className="font-bold text-slate-300">
                        {isBaseline ? 'Initial baseline prompt' : 'No parent prompt'}
                    </h3>
                    <p className="text-slate-500 text-xs max-w-md">
                        {isBaseline
                            ? 'This is the starting point of the sector predictor auto-research loop. No previous variant is available to compare.'
                            : 'This experiment does not have a registered parent variant to compare against.'}
                    </p>
                </div>
            </Card>
        );
    }

    return (
        <Card className="p-6 bg-slate-800/20 border-slate-700/50 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                    <SectionHeading className="text-slate-200">Prompt Changes</SectionHeading>
                    <p className="text-xs text-slate-500">
                        Comparing{' '}
                        <span className="font-mono text-emerald-400">
                            v{parentExperiment.variant_tag}
                        </span>{' '}
                        (old) →{' '}
                        <span className="font-mono text-emerald-400">
                            v{experiment.variant_tag}
                        </span>{' '}
                        (new)
                    </p>
                </div>

                {hasChanges && (
                    <button
                        type="button"
                        onClick={() => setShowChangesOnly(!showChangesOnly)}
                        className="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs rounded-md transition-colors"
                    >
                        {showChangesOnly ? 'Show Full Prompt Diff' : 'Show Changes Only'}
                    </button>
                )}
            </div>

            <div className="relative group">
                <div className="relative font-mono text-[11px] leading-relaxed max-h-[350px] overflow-y-auto bg-slate-950 border border-slate-850 rounded-xl p-4 md:p-6 space-y-[2px]">
                    {!hasChanges ? (
                        <div className="text-center text-slate-500 py-6 text-xs">
                            ✨ No prompt text changes detected between these variants.
                        </div>
                    ) : showChangesOnly && filteredChanges.length === 0 ? (
                        <div className="text-center text-slate-500 py-6 text-xs">
                            No added or removed lines to show.
                        </div>
                    ) : (
                        filteredChanges.map((change, idx) => {
                            let prefix = '  ';
                            let classes = 'text-slate-500 px-2 py-0.5 opacity-60';

                            if (change.added) {
                                prefix = '+ ';
                                classes =
                                    'bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-500 px-2 py-0.5';
                            } else if (change.removed) {
                                prefix = '- ';
                                classes =
                                    'bg-rose-500/10 text-rose-400 border-l-2 border-rose-500 px-2 py-0.5 line-through decoration-rose-500/30';
                            }

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
