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
import type {
    EvaluationAuditData,
    EvaluationAuditItem,
    SectorPrediction,
} from '../api/fetch-predictions';
import { AIPredictionChart } from '../components/AIPredictionChart';
import { AIPredictionsTable } from '../components/AIPredictionsTable';

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

function getModelMetrics(items: SectorPrediction[]) {
    const evaluated = items.filter(
        (i) =>
            i.status === 'evaluated' &&
            i.sector_percentile_score != null &&
            i.pair_percentile_score != null,
    );
    const pending = items.filter((i) => i.status === 'pending');
    if (evaluated.length === 0) {
        return {
            avgScore: 'N/A',
            topQuartileRate: '0%',
            evaluatedCount: 0,
            pendingCount: pending.length,
        };
    }
    const sum = evaluated.reduce((acc, curr) => {
        const scores = [
            curr.sector_percentile_score,
            curr.worst_sector_percentile_score,
            curr.pair_percentile_score,
        ].filter((s): s is number => s != null);
        const base = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
        const spDiff =
            curr.sector_sp_diff ??
            (curr.predicted_sector_return != null && curr.benchmark_spy_return != null
                ? curr.predicted_sector_return - curr.benchmark_spy_return
                : 0);
        const alphaBonus = Math.max(0, spDiff);
        return acc + (base + alphaBonus);
    }, 0);

    const topQuartileCalls = evaluated.filter((i) => (i.sector_percentile_score || 0) >= 75).length;

    return {
        avgScore: (sum / evaluated.length).toFixed(1),
        topQuartileRate: `${Math.round((topQuartileCalls / evaluated.length) * 100)}%`,
        evaluatedCount: evaluated.length,
        pendingCount: pending.length,
    };
}

function filterFeedPredictions(
    data: SectorPrediction[],
    statusFilter: 'all' | 'active' | 'past',
    timeframeFilter: '7d' | '30d' | '60d' | '90d' | 'all',
): SectorPrediction[] {
    return data.filter((d) => {
        const matchesStatus =
            statusFilter === 'all' ||
            (statusFilter === 'active' && d.status === 'pending') ||
            (statusFilter === 'past' && d.status === 'evaluated');
        const matchesTimeframe = timeframeFilter === 'all' || d.timeframe === timeframeFilter;
        return matchesStatus && matchesTimeframe;
    });
}

function calculateBaselineScore(experimentsList: PromptExperiment[]): string {
    const scores = experimentsList
        .map((exp) => exp.metrics?.score)
        .filter((s): s is number => s !== undefined && s !== null);
    if (scores.length === 0) return 'N/A';
    return Math.max(...scores).toFixed(4);
}

function findActiveVariant(experimentsList: PromptExperiment[]): string {
    return experimentsList.find((exp) => exp.status === 'active')?.variant_tag || 'N/A';
}

function findSelectedExperiment(
    experimentsList: PromptExperiment[],
    selectedExpId: string | null,
): PromptExperiment | null {
    if (selectedExpId) {
        return experimentsList.find((e) => e.id === selectedExpId) || null;
    }
    return experimentsList.length > 0 ? experimentsList[0] : null;
}

function findParentExperiment(
    experimentsList: PromptExperiment[],
    selectedExperiment: PromptExperiment | null,
): PromptExperiment | null {
    if (!selectedExperiment?.parent_tag) return null;
    return experimentsList.find((e) => e.variant_tag === selectedExperiment.parent_tag) || null;
}

function filterChartData(
    evaluatedPredictions: SectorPrediction[],
    timeframeFilter: '7d' | '30d' | '60d' | '90d' | 'all',
): SectorPrediction[] {
    return timeframeFilter === 'all'
        ? evaluatedPredictions
        : evaluatedPredictions.filter((d) => d.timeframe === timeframeFilter);
}

interface ArenaTabContentProps {
    deepSeekMetrics: ReturnType<typeof getModelMetrics>;
    miniMaxMetrics: ReturnType<typeof getModelMetrics>;
    geminiMetrics: ReturnType<typeof getModelMetrics>;
    openAiMetrics: ReturnType<typeof getModelMetrics>;
    data: SectorPrediction[];
    pendingPredictions: SectorPrediction[];
    evaluatedPredictions: SectorPrediction[];
    chartFilteredData: SectorPrediction[];
    feedFilteredData: SectorPrediction[];
    statusFilter: 'all' | 'active' | 'past';
    setStatusFilter: (status: 'all' | 'active' | 'past') => void;
    timeframeFilter: '7d' | '30d' | '60d' | '90d' | 'all';
    setTimeframeFilter: (tf: '7d' | '30d' | '60d' | '90d' | 'all') => void;
    feedViewMode: 'table' | 'cards';
    setFeedViewMode: (mode: 'table' | 'cards') => void;
}

function ArenaTabContent({
    deepSeekMetrics,
    miniMaxMetrics,
    geminiMetrics,
    openAiMetrics,
    data,
    pendingPredictions,
    evaluatedPredictions,
    chartFilteredData,
    feedFilteredData,
    statusFilter,
    setStatusFilter,
    timeframeFilter,
    setTimeframeFilter,
    feedViewMode,
    setFeedViewMode,
}: ArenaTabContentProps) {
    return (
        <div className="space-y-8 animate-in fade-in duration-300">
            {/* SECTION 1: Head-to-Head Scoreboard (4 Models) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* DeepSeek */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                    <div className="flex justify-between items-start mb-2">
                        <h2 className="text-xl font-bold text-blue-400">DeepSeek Models</h2>
                        <Badge colorScheme="accent" variant="soft">
                            {deepSeekMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div>
                            <div className="text-3xl font-light text-white mb-1">
                                {deepSeekMetrics.avgScore}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Avg Percentile Score
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-light text-emerald-400 mb-1">
                                {deepSeekMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Top-Quartile Call Rate
                            </div>
                        </div>
                    </div>
                </div>

                {/* MiniMax */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                    <div className="flex justify-between items-start mb-2">
                        <h2 className="text-xl font-bold text-emerald-400">MiniMax-M3</h2>
                        <Badge colorScheme="neutral" variant="soft">
                            {miniMaxMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div>
                            <div className="text-3xl font-light text-white mb-1">
                                {miniMaxMetrics.avgScore}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Avg Percentile Score
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-light text-emerald-400 mb-1">
                                {miniMaxMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Top-Quartile Call Rate
                            </div>
                        </div>
                    </div>
                </div>

                {/* Gemini */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                    <div className="flex justify-between items-start mb-2">
                        <h2 className="text-xl font-bold text-amber-400">Gemini 3.5</h2>
                        <Badge colorScheme="accent" variant="soft">
                            {geminiMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div>
                            <div className="text-3xl font-light text-white mb-1">
                                {geminiMetrics.avgScore}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Avg Percentile Score
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-light text-emerald-400 mb-1">
                                {geminiMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Top-Quartile Call Rate
                            </div>
                        </div>
                    </div>
                </div>

                {/* OpenAI / GPT */}
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                    <div className="flex justify-between items-start mb-2">
                        <h2 className="text-xl font-bold text-purple-400">OpenAI GPT-5.6</h2>
                        <Badge colorScheme="neutral" variant="soft">
                            {openAiMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div>
                            <div className="text-3xl font-light text-white mb-1">
                                {openAiMetrics.avgScore}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Avg Percentile Score
                            </div>
                        </div>
                        <div>
                            <div className="text-3xl font-light text-emerald-400 mb-1">
                                {openAiMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wider">
                                Top-Quartile Call Rate
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* SECTION 2: Historical Accuracy Trend Chart (Placed on Top) */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                    <div>
                        <h3 className="text-xl font-bold text-white">Historical Accuracy Trend</h3>
                        <p className="text-xs text-slate-400 mt-1">
                            Model percentile scores evaluated against benchmark market ETF returns
                            over time.
                        </p>
                    </div>
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
                    <div className="h-[300px] flex items-center justify-center text-slate-400 text-sm">
                        No evaluated predictions available for this timeframe.
                    </div>
                )}
            </div>

            {/* SECTION 3: Unified Predictions Table & Feed */}
            <div className="space-y-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-slate-900/40 p-4 rounded-xl border border-slate-800">
                    <div>
                        <h3 className="text-xl font-bold text-white">All Sector Predictions</h3>
                        <p className="text-xs text-slate-400 mt-0.5">
                            Interactive view for tracking prediction performance, Alpha vs S&P 500,
                            and target dates across all models.
                        </p>
                    </div>

                    {/* View Switcher: Table vs Detailed Cards */}
                    <div className="flex items-center gap-3">
                        <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
                            <button
                                type="button"
                                onClick={() => setFeedViewMode('table')}
                                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                                    feedViewMode === 'table'
                                        ? 'bg-blue-600 text-white shadow-sm'
                                        : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                <span>📊 Data Table</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setFeedViewMode('cards')}
                                className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                                    feedViewMode === 'cards'
                                        ? 'bg-blue-600 text-white shadow-sm'
                                        : 'text-slate-400 hover:text-slate-200'
                                }`}
                            >
                                <span>🎴 Feed Cards</span>
                            </button>
                        </div>
                    </div>
                </div>

                {feedViewMode === 'table' ? (
                    <AIPredictionsTable predictions={data} />
                ) : (
                    <div className="space-y-6">
                        <div className="flex flex-wrap items-center gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                            {/* Status Segmented Filter */}
                            <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
                                <button
                                    type="button"
                                    onClick={() => setStatusFilter('all')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                        statusFilter === 'all'
                                            ? 'bg-slate-800 text-white shadow-sm'
                                            : 'text-slate-400 hover:text-slate-200'
                                    }`}
                                >
                                    All Forecasts ({data.length})
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setStatusFilter('active')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                        statusFilter === 'active'
                                            ? 'bg-blue-600/80 text-white shadow-sm'
                                            : 'text-slate-400 hover:text-slate-200'
                                    }`}
                                >
                                    🔮 Active ({pendingPredictions.length})
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setStatusFilter('past')}
                                    className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                                        statusFilter === 'past'
                                            ? 'bg-emerald-600/80 text-white shadow-sm'
                                            : 'text-slate-400 hover:text-slate-200'
                                    }`}
                                >
                                    🎯 Past Outcomes ({evaluatedPredictions.length})
                                </button>
                            </div>

                            {/* Timeframe Segmented Filter */}
                            <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
                                {(['7d', '30d', '60d', '90d', 'all'] as const).map((tf) => (
                                    <button
                                        key={tf}
                                        type="button"
                                        onClick={() => setTimeframeFilter(tf)}
                                        className={`px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors ${
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

                        {/* Predictions Grid */}
                        <div className="grid grid-cols-1 gap-4">
                            {feedFilteredData.length > 0 ? (
                                feedFilteredData.map((pred) => (
                                    <PredictionFeedCard key={pred.id} pred={pred} />
                                ))
                            ) : (
                                <div className="p-8 bg-slate-800/30 border border-dashed border-slate-700/60 rounded-xl text-center text-slate-400 text-sm">
                                    No predictions match the selected status and timeframe filters.
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export function AIPredictionsPage({ initialData, experiments, refreshFn }: AIPredictionsPageProps) {
    const [data, setData] = useState<SectorPrediction[]>(initialData);
    const [experimentsList, setExperimentsList] = useState<PromptExperiment[]>(experiments);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'past'>('all');
    const [timeframeFilter, setTimeframeFilter] = useState<'7d' | '30d' | '60d' | '90d' | 'all'>(
        '7d',
    );
    const [activeTab, setActiveTab] = useState<'arena' | 'autoresearch'>('arena');
    const [feedViewMode, setFeedViewMode] = useState<'table' | 'cards'>('table');
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
    const deepSeekData = data.filter((d) => d.model_name.toLowerCase().includes('deepseek'));
    const miniMaxData = data.filter((d) => d.model_name.toLowerCase().includes('minimax'));
    const geminiData = data.filter((d) => d.model_name.toLowerCase().includes('gemini'));
    const openAiData = data.filter(
        (d) =>
            d.model_name.toLowerCase().includes('gpt') ||
            d.model_name.toLowerCase().includes('openai'),
    );

    const pendingPredictions = useMemo(() => data.filter((d) => d.status === 'pending'), [data]);
    const evaluatedPredictions = useMemo(
        () => data.filter((d) => d.status === 'evaluated'),
        [data],
    );

    const deepSeekMetrics = useMemo(() => getModelMetrics(deepSeekData), [deepSeekData]);
    const miniMaxMetrics = useMemo(() => getModelMetrics(miniMaxData), [miniMaxData]);
    const geminiMetrics = useMemo(() => getModelMetrics(geminiData), [geminiData]);
    const openAiMetrics = useMemo(() => getModelMetrics(openAiData), [openAiData]);

    const chartFilteredData = useMemo(
        () => filterChartData(evaluatedPredictions, timeframeFilter),
        [evaluatedPredictions, timeframeFilter],
    );

    const feedFilteredData = useMemo(
        () => filterFeedPredictions(data, statusFilter, timeframeFilter),
        [data, statusFilter, timeframeFilter],
    );

    // Auto-Research computations
    const baselineScore = useMemo(() => calculateBaselineScore(experimentsList), [experimentsList]);

    const activeVariant = useMemo(() => findActiveVariant(experimentsList), [experimentsList]);

    const selectedExperiment = useMemo(
        () => findSelectedExperiment(experimentsList, selectedExpId),
        [experimentsList, selectedExpId],
    );

    const parentExperiment = useMemo(
        () => findParentExperiment(experimentsList, selectedExperiment),
        [selectedExperiment, experimentsList],
    );

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
                        AI Sector Predictions Arena
                    </h1>
                    <p className="text-slate-400 mt-2 text-lg">
                        Multi-Model Arena: DeepSeek, MiniMax-M3, Gemini 3.5 & OpenAI GPT-5.6
                        predicting top-performing sectors and uncorrelated pairs.
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
                <ArenaTabContent
                    deepSeekMetrics={deepSeekMetrics}
                    miniMaxMetrics={miniMaxMetrics}
                    geminiMetrics={geminiMetrics}
                    openAiMetrics={openAiMetrics}
                    data={data}
                    pendingPredictions={pendingPredictions}
                    evaluatedPredictions={evaluatedPredictions}
                    chartFilteredData={chartFilteredData}
                    feedFilteredData={feedFilteredData}
                    statusFilter={statusFilter}
                    setStatusFilter={setStatusFilter}
                    timeframeFilter={timeframeFilter}
                    setTimeframeFilter={setTimeframeFilter}
                    feedViewMode={feedViewMode}
                    setFeedViewMode={setFeedViewMode}
                />
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

interface PredictionFeedCardProps {
    pred: SectorPrediction;
}

function PredictionOutcomeBadge({ pred }: { pred: SectorPrediction }) {
    if (pred.status === 'pending') {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/40 flex items-center gap-1">
                <span>🔮</span> Active Forecast (Pending)
            </span>
        );
    }

    const sectorScore = pred.sector_percentile_score ?? 0;
    if (sectorScore >= 75) {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                🎯 Top-Quartile Call ({sectorScore.toFixed(0)}th percentile)
            </span>
        );
    }

    if (sectorScore >= 50) {
        return (
            <span className="px-3 py-1 text-xs font-bold rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/40">
                🟢 Above Benchmark ({sectorScore.toFixed(0)}th percentile)
            </span>
        );
    }

    return (
        <span className="px-3 py-1 text-xs font-bold rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40">
            🔴 Below Benchmark ({sectorScore.toFixed(0)}th percentile)
        </span>
    );
}

function getModelBadgeStyle(modelName: string): string {
    const lower = modelName.toLowerCase();
    if (lower.includes('deepseek')) return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
    if (lower.includes('minimax'))
        return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
    if (lower.includes('gemini'))
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
    if (lower.includes('gpt') || lower.includes('openai'))
        return 'bg-purple-500/20 text-purple-400 border border-purple-500/30';
    return 'bg-slate-500/20 text-slate-400 border border-slate-500/30';
}

function computeCompositeScore(pred: SectorPrediction) {
    const components = [
        pred.sector_percentile_score,
        pred.worst_sector_percentile_score,
        pred.pair_percentile_score,
    ].filter((s): s is number => s != null);
    const baseScore =
        components.length > 0 ? components.reduce((a, b) => a + b, 0) / components.length : 0;

    const spDiff =
        pred.sector_sp_diff ??
        (pred.predicted_sector_return != null && pred.benchmark_spy_return != null
            ? pred.predicted_sector_return - pred.benchmark_spy_return
            : 0);
    const alphaBonus = Math.max(0, spDiff);
    const compositeScore = (baseScore + alphaBonus).toFixed(1);

    return { components, alphaBonus, compositeScore };
}

function CompositeScoreBanner({ pred }: { pred: SectorPrediction }) {
    const { components, alphaBonus, compositeScore } = computeCompositeScore(pred);

    return (
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-xs space-y-1">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1">
                <span className="text-slate-200 font-semibold flex items-center gap-1.5">
                    <span>🏆</span> Composite Predictor Score:{' '}
                    <strong className="text-emerald-400 font-mono text-sm">
                        {compositeScore} / 100
                    </strong>
                </span>
                <span className="text-slate-400 font-mono text-[11px]">
                    Formula: ({components.map((c) => c.toFixed(1)).join(' + ')}) ÷{' '}
                    {components.length}
                    {alphaBonus > 0 ? ` + ${alphaBonus.toFixed(1)} S&P Alpha` : ''}
                </span>
            </div>
        </div>
    );
}

function ScoreConstituentsGrid({
    pred,
    isPending,
}: {
    pred: SectorPrediction;
    isPending: boolean;
}) {
    const hasWorst = Boolean(
        pred.predicted_worst_sector && pred.predicted_worst_sector !== 'UNKNOWN',
    );
    const sectorScore = pred.sector_percentile_score ?? 0;
    const worstSectorScore = pred.worst_sector_percentile_score;
    const pairScore = pred.pair_percentile_score ?? 0;

    return (
        <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Score Constituents Breakdown
            </div>
            <div
                className={`grid grid-cols-1 ${
                    hasWorst ? 'md:grid-cols-3' : 'md:grid-cols-2'
                } gap-4`}
            >
                <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800 space-y-1">
                    <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-slate-300">1️⃣ Best Sector Call</span>
                        <span className="text-slate-500 font-mono text-[10px]">
                            Best Sector Score
                        </span>
                    </div>
                    <div className="text-lg font-bold text-white flex items-center gap-2">
                        {pred.predicted_sector}
                        {!isPending && (
                            <span className="text-xs font-semibold text-emerald-400">
                                ({sectorScore.toFixed(1)} score)
                            </span>
                        )}
                    </div>
                    {!isPending && (
                        <div className="text-[11px] text-slate-400">
                            vs S&P Sector ETF Median (50th %ile)
                        </div>
                    )}
                </div>

                {hasWorst && (
                    <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800 space-y-1">
                        <div className="flex justify-between items-center text-xs">
                            <span className="font-semibold text-slate-300">
                                2️⃣ Worst Sector Call
                            </span>
                            <span className="text-slate-500 font-mono text-[10px]">
                                Worst Sector Score
                            </span>
                        </div>
                        <div className="text-lg font-bold text-rose-400 flex items-center gap-2">
                            {pred.predicted_worst_sector}
                            {!isPending && worstSectorScore != null && (
                                <span className="text-xs font-semibold text-rose-300">
                                    ({worstSectorScore.toFixed(1)} score)
                                </span>
                            )}
                        </div>
                        {!isPending && (
                            <div className="text-[11px] text-slate-400">
                                Bottom sector performance rank
                            </div>
                        )}
                    </div>
                )}

                <div className="bg-slate-900/60 rounded-lg p-3 border border-slate-800 space-y-1">
                    <div className="flex justify-between items-center text-xs">
                        <span className="font-semibold text-slate-300">
                            {hasWorst ? '3️⃣ Uncorrelated Pair' : '2️⃣ Uncorrelated Pair'}
                        </span>
                        <span className="text-slate-500 font-mono text-[10px]">Pair Score</span>
                    </div>
                    <div className="text-lg font-bold text-white flex items-center gap-2">
                        {pred.predicted_pair.join(' + ')}
                        {!isPending && (
                            <span className="text-xs font-semibold text-emerald-400">
                                ({pairScore.toFixed(1)} score)
                            </span>
                        )}
                    </div>
                    {!isPending && (
                        <div className="text-[11px] text-slate-400">
                            Multi-asset uncorrelation basket rank
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function PredictionFeedCard({ pred }: PredictionFeedCardProps) {
    const isPending = pred.status === 'pending';
    const hasBenchmarkData =
        pred.benchmark_spy_return != null && pred.predicted_sector_return != null;

    return (
        <div
            className={`border rounded-xl p-5 space-y-4 transition-colors ${
                isPending
                    ? 'bg-slate-800/60 border-blue-500/40 shadow-sm'
                    : 'bg-slate-800/40 border-slate-700/80 hover:border-slate-600'
            }`}
        >
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                <div className="flex items-center gap-3 flex-wrap">
                    <span
                        className={`px-2.5 py-1 text-xs font-bold rounded-md ${getModelBadgeStyle(
                            pred.model_name,
                        )}`}
                    >
                        {pred.model_name}
                    </span>
                    <span className="text-slate-400 text-sm font-medium">
                        Target: {formatStableDate(pred.target_date)} ({pred.timeframe})
                    </span>
                </div>

                <div>
                    <PredictionOutcomeBadge pred={pred} />
                </div>
            </div>

            {/* S&P 500 Benchmark Window Return Comparison Block */}
            {!isPending && hasBenchmarkData && <BenchmarkComparisonBlock pred={pred} />}

            {/* Data Audit & Price Verification Block */}
            {!isPending && pred.evaluation_audit_data && (
                <DataAuditBlock auditData={pred.evaluation_audit_data} />
            )}

            {/* Evaluated Composite Score Formula Banner */}
            {!isPending && <CompositeScoreBanner pred={pred} />}

            {/* Score Constituents Breakdown */}
            <ScoreConstituentsGrid pred={pred} isPending={isPending} />

            <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    AI Rationale
                </div>
                <p className="text-xs text-slate-300 bg-slate-900/50 p-3 rounded-lg leading-relaxed border border-slate-850">
                    {pred.reasoning}
                </p>
            </div>
        </div>
    );
}

function BenchmarkComparisonBlock({ pred }: { pred: SectorPrediction }) {
    const spyReturn = pred.benchmark_spy_return ?? 0;
    const sectorReturn = pred.predicted_sector_return ?? 0;
    const pairReturn = pred.predicted_pair_return ?? 0;

    const sectorAlpha = sectorReturn - spyReturn;
    const pairAlpha = pairReturn - spyReturn;

    const formatReturn = (val: number) => (val >= 0 ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`);

    return (
        <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-3">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1 border-b border-slate-800 pb-2">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>🎯</span> Prediction vs S&P 500 Benchmark ({pred.timeframe} Window)
                </span>
                <span className="text-xs font-mono text-slate-300">
                    S&P 500 (SPY): {formatReturn(spyReturn)}
                </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                        Sector Call: {pred.predicted_sector}
                    </div>
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm font-bold text-white">
                            Return: {formatReturn(sectorReturn)}
                        </span>
                        <span
                            className={`font-semibold font-mono text-xs ${
                                sectorAlpha >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {formatReturn(sectorAlpha)} vs S&P 500
                        </span>
                    </div>
                </div>

                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80 space-y-1">
                    <div className="text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
                        Pair Call: {pred.predicted_pair.join(' + ')}
                    </div>
                    <div className="flex justify-between items-baseline">
                        <span className="text-sm font-bold text-white">
                            Return: {formatReturn(pairReturn)}
                        </span>
                        <span
                            className={`font-semibold font-mono text-xs ${
                                pairAlpha >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                        >
                            {formatReturn(pairAlpha)} vs S&P 500
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}

function DataAuditBlock({ auditData }: { auditData: EvaluationAuditData }) {
    const spy = auditData.spy;
    const sector = auditData.sector;
    const pairs = auditData.pair || [];

    const formatPrice = (p: number) => `$${p.toFixed(2)}`;
    const formatRet = (val: number) => (val >= 0 ? `+${val.toFixed(1)}%` : `${val.toFixed(1)}%`);

    return (
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-3 text-xs space-y-2">
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-1 text-slate-300 font-semibold text-[11px] border-b border-slate-800 pb-1.5">
                <span className="flex items-center gap-1">
                    <span>🔍</span> Data Audit & Price Verification
                </span>
                <span className="text-slate-400 font-mono text-[10px]">
                    Window: {auditData.start_date} ➔ {auditData.end_date}
                </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                {spy && (
                    <div className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono">
                        <span className="text-slate-400 font-sans">S&P 500 (SPY):</span>
                        <span className="text-slate-200">
                            {formatPrice(spy.start_price)} ➔ {formatPrice(spy.end_price)}{' '}
                            <span
                                className={
                                    spy.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }
                            >
                                ({formatRet(spy.return_pct)})
                            </span>
                        </span>
                    </div>
                )}

                {sector && (
                    <div className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono">
                        <span className="text-slate-400 font-sans">
                            Best Sector ({sector.ticker}):
                        </span>
                        <span className="text-slate-200">
                            {formatPrice(sector.start_price)} ➔ {formatPrice(sector.end_price)}{' '}
                            <span
                                className={
                                    sector.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }
                            >
                                ({formatRet(sector.return_pct)})
                            </span>
                        </span>
                    </div>
                )}

                {auditData.worst_sector && (
                    <div className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono">
                        <span className="text-rose-400 font-sans">
                            Worst Sector ({auditData.worst_sector.ticker}):
                        </span>
                        <span className="text-slate-200">
                            {formatPrice(auditData.worst_sector.start_price)} ➔{' '}
                            {formatPrice(auditData.worst_sector.end_price)}{' '}
                            <span
                                className={
                                    auditData.worst_sector.return_pct <= 0
                                        ? 'text-emerald-400'
                                        : 'text-rose-400'
                                }
                            >
                                ({formatRet(auditData.worst_sector.return_pct)})
                            </span>
                        </span>
                    </div>
                )}

                {pairs.map((item: EvaluationAuditItem) => (
                    <div
                        key={item.ticker}
                        className="flex justify-between items-center bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-850 font-mono"
                    >
                        <span className="text-slate-400 font-sans">
                            Pair Asset ({item.ticker}):
                        </span>
                        <span className="text-slate-200">
                            {formatPrice(item.start_price)} ➔ {formatPrice(item.end_price)}{' '}
                            <span
                                className={
                                    item.return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }
                            >
                                ({formatRet(item.return_pct)})
                            </span>
                        </span>
                    </div>
                ))}
            </div>
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
