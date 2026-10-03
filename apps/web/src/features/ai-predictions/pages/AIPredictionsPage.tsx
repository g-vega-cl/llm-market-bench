import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge } from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import type { SectorPrediction } from '../api/fetch-predictions';
import { AIPredictionChart } from '../components/AIPredictionChart';
import { AIPredictionsTable } from '../components/AIPredictionsTable';
import { PredictionFeedCard } from '../components/PredictionFeedCard';
import {
    DEFAULT_SECTOR_PREDICTOR_TOOLS,
    PredictorAutoresearchTab,
} from '../components/PredictorAutoresearchTab';

export { DEFAULT_SECTOR_PREDICTOR_TOOLS };

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

            {/* SECTION 2: Historical Accuracy Trend Chart */}
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
                                {(['all', '7d', '30d', '60d', '90d'] as const).map((tf) => (
                                    <button
                                        key={tf}
                                        type="button"
                                        onClick={() => setTimeframeFilter(tf)}
                                        className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${
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

                        {/* Cards Feed */}
                        <div className="space-y-4">
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
                <PredictorAutoresearchTab experimentsList={experimentsList} predictions={data} />
            )}
        </div>
    );
}
