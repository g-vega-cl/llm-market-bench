import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card } from '@llm-market-bench/ui-design-system';
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
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-6 items-stretch">
                {/* DeepSeek */}
                <Card
                    isHoverable
                    padding="md"
                    className="h-full flex flex-col justify-between gap-4"
                >
                    <div className="flex justify-between items-start gap-2">
                        <h2 className="text-sm font-bold text-boxel-ink">DeepSeek Models</h2>
                        <Badge colorScheme="accent" variant="soft" size="xs">
                            {deepSeekMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-auto pt-2 border-t border-boxel-bevel-hi">
                        <div>
                            <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                                {deepSeekMetrics.avgScore}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Avg Percentile
                            </div>
                        </div>
                        <div>
                            <div className="text-lg font-bold font-mono text-success tabular-nums">
                                {deepSeekMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Top-Quartile
                            </div>
                        </div>
                    </div>
                </Card>

                {/* MiniMax */}
                <Card
                    isHoverable
                    padding="md"
                    className="h-full flex flex-col justify-between gap-4"
                >
                    <div className="flex justify-between items-start gap-2">
                        <h2 className="text-sm font-bold text-boxel-ink">MiniMax-M3</h2>
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            {miniMaxMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-auto pt-2 border-t border-boxel-bevel-hi">
                        <div>
                            <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                                {miniMaxMetrics.avgScore}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Avg Percentile
                            </div>
                        </div>
                        <div>
                            <div className="text-lg font-bold font-mono text-success tabular-nums">
                                {miniMaxMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Top-Quartile
                            </div>
                        </div>
                    </div>
                </Card>

                {/* Gemini */}
                <Card
                    isHoverable
                    padding="md"
                    className="h-full flex flex-col justify-between gap-4"
                >
                    <div className="flex justify-between items-start gap-2">
                        <h2 className="text-sm font-bold text-boxel-ink">Gemini 3.5</h2>
                        <Badge colorScheme="accent" variant="soft" size="xs">
                            {geminiMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-auto pt-2 border-t border-boxel-bevel-hi">
                        <div>
                            <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                                {geminiMetrics.avgScore}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Avg Percentile
                            </div>
                        </div>
                        <div>
                            <div className="text-lg font-bold font-mono text-success tabular-nums">
                                {geminiMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Top-Quartile
                            </div>
                        </div>
                    </div>
                </Card>

                {/* OpenAI / GPT */}
                <Card
                    isHoverable
                    padding="md"
                    className="h-full flex flex-col justify-between gap-4"
                >
                    <div className="flex justify-between items-start gap-2">
                        <h2 className="text-sm font-bold text-boxel-ink">OpenAI GPT-5.6</h2>
                        <Badge colorScheme="neutral" variant="soft" size="xs">
                            {openAiMetrics.evaluatedCount} Evaluated
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-auto pt-2 border-t border-boxel-bevel-hi">
                        <div>
                            <div className="text-lg font-bold font-mono text-boxel-ink tabular-nums">
                                {openAiMetrics.avgScore}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Avg Percentile
                            </div>
                        </div>
                        <div>
                            <div className="text-lg font-bold font-mono text-success tabular-nums">
                                {openAiMetrics.topQuartileRate}
                            </div>
                            <div className="text-xs font-normal text-boxel-muted uppercase tracking-wider">
                                Top-Quartile
                            </div>
                        </div>
                    </div>
                </Card>
            </div>

            {/* SECTION 2: Historical Accuracy Trend Chart */}
            <div className="bg-slate-800/50 border border-slate-700 rounded-none p-6 backdrop-blur-sm shadow-sm">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                    <div>
                        <h3 className="text-lg font-bold font-display uppercase tracking-wider text-white">
                            Historical Accuracy Trend
                        </h3>
                        <p className="text-xs font-normal text-slate-400">
                            Model percentile scores evaluated against benchmark market ETF returns
                            over time.
                        </p>
                    </div>
                    <div className="flex bg-slate-900/60 p-1 rounded-none border border-slate-700 shadow-sm">
                        {(['7d', '30d', '60d', '90d', 'all'] as const).map((tf) => (
                            <button
                                key={tf}
                                type="button"
                                onClick={() => setTimeframeFilter(tf)}
                                className={`px-3 py-1 text-sm font-bold rounded-none transition-colors ${
                                    timeframeFilter === tf
                                        ? 'bg-boxel-elevated text-boxel-ink shadow-sm'
                                        : 'text-boxel-muted hover:text-boxel-ink'
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
                    <div className="h-[300px] flex items-center justify-center text-boxel-muted text-xs font-normal">
                        No evaluated predictions available for this timeframe.
                    </div>
                )}
            </div>

            {/* SECTION 3: Unified Predictions Table & Feed */}
            <div className="flex flex-col gap-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-boxel-trough p-4 rounded-none border border-boxel-bevel-hi">
                    <div>
                        <h3 className="text-lg font-bold text-boxel-ink">All Sector Predictions</h3>
                        <p className="text-xs font-normal text-boxel-muted mt-0.5">
                            Interactive view for tracking prediction performance, Alpha vs S&P 500,
                            and target dates across all models.
                        </p>
                    </div>

                    {/* View Switcher: Table vs Detailed Cards */}
                    <div className="flex items-center gap-3">
                        <div className="flex bg-boxel-canvas p-1 rounded-none border border-boxel-bevel-hi">
                            <button
                                type="button"
                                onClick={() => setFeedViewMode('table')}
                                className={`px-3 py-1.5 text-sm font-bold rounded-none transition-colors flex items-center gap-1.5 ${
                                    feedViewMode === 'table'
                                        ? 'bg-accent text-accent-ink shadow-sm'
                                        : 'text-boxel-muted hover:text-boxel-ink'
                                }`}
                            >
                                <span>📊 Data Table</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setFeedViewMode('cards')}
                                className={`px-3 py-1.5 text-sm font-bold rounded-none transition-colors flex items-center gap-1.5 ${
                                    feedViewMode === 'cards'
                                        ? 'bg-accent text-accent-ink shadow-sm'
                                        : 'text-boxel-muted hover:text-boxel-ink'
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
                    <div className="flex flex-col gap-6">
                        <div className="flex flex-wrap items-center gap-3 bg-boxel-trough p-3 rounded-none border border-boxel-bevel-hi">
                            {/* Status Segmented Filter */}
                            <div className="flex bg-boxel-canvas p-1 rounded-none border border-boxel-bevel-hi">
                                <button
                                    type="button"
                                    onClick={() => setStatusFilter('all')}
                                    className={`px-3 py-1.5 text-sm font-bold rounded-none transition-colors ${
                                        statusFilter === 'all'
                                            ? 'bg-boxel-elevated text-boxel-ink shadow-sm'
                                            : 'text-boxel-muted hover:text-boxel-ink'
                                    }`}
                                >
                                    All Forecasts ({data.length})
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setStatusFilter('active')}
                                    className={`px-3 py-1.5 text-sm font-bold rounded-none transition-colors ${
                                        statusFilter === 'active'
                                            ? 'bg-accent text-accent-ink shadow-sm'
                                            : 'text-boxel-muted hover:text-boxel-ink'
                                    }`}
                                >
                                    🔮 Active ({pendingPredictions.length})
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setStatusFilter('past')}
                                    className={`px-3 py-1.5 text-sm font-bold rounded-none transition-colors ${
                                        statusFilter === 'past'
                                            ? 'bg-emerald-600/80 text-white shadow-sm'
                                            : 'text-boxel-muted hover:text-boxel-ink'
                                    }`}
                                >
                                    🎯 Past Outcomes ({evaluatedPredictions.length})
                                </button>
                            </div>

                            {/* Timeframe Segmented Filter */}
                            <div className="flex bg-boxel-canvas p-1 rounded-none border border-boxel-bevel-hi">
                                {(['all', '7d', '30d', '60d', '90d'] as const).map((tf) => (
                                    <button
                                        key={tf}
                                        type="button"
                                        onClick={() => setTimeframeFilter(tf)}
                                        className={`px-3 py-1.5 text-sm font-bold rounded-none transition-colors ${
                                            timeframeFilter === tf
                                                ? 'bg-boxel-elevated text-boxel-ink shadow-sm'
                                                : 'text-boxel-muted hover:text-boxel-ink'
                                        }`}
                                    >
                                        {tf.toUpperCase()}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Cards Feed */}
                        <div className="flex flex-col gap-4">
                            {feedFilteredData.length > 0 ? (
                                feedFilteredData.map((pred) => (
                                    <PredictionFeedCard key={pred.id} pred={pred} />
                                ))
                            ) : (
                                <div className="p-8 bg-slate-800/30 border border-dashed border-slate-700/60 rounded-none text-center text-slate-400 text-xs font-normal shadow-sm">
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
        <div className="p-8 max-w-7xl mx-auto flex flex-col gap-6 animate-in fade-in duration-500">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex flex-col gap-1">
                    <h1 className="text-lg font-bold tracking-tight text-boxel-ink uppercase">
                        AI Sector Predictions Arena
                    </h1>
                    <p className="text-boxel-muted text-xs font-normal">
                        Multi-Model Arena: DeepSeek, MiniMax-M3, Gemini 3.5 & OpenAI GPT-5.6
                        predicting top-performing sectors and uncorrelated pairs.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={handleRefresh}
                    disabled={loading}
                    className="voxel-btn px-4 py-2 bg-boxel-surface hover:bg-boxel-elevated border border-boxel-bevel-hi text-boxel-ink rounded-none transition-colors flex items-center gap-2 text-sm font-bold"
                >
                    {loading ? 'Refreshing...' : 'Refresh Data'}
                </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-boxel-bevel-hi">
                <button
                    type="button"
                    onClick={() => setActiveTab('arena')}
                    className={`py-3 px-6 font-bold border-b-2 text-sm transition-all duration-200 ${
                        activeTab === 'arena'
                            ? 'border-accent text-accent'
                            : 'border-transparent text-boxel-muted hover:text-boxel-ink'
                    }`}
                >
                    Arena Dashboard
                </button>
                <button
                    type="button"
                    onClick={() => setActiveTab('autoresearch')}
                    className={`py-3 px-6 font-bold border-b-2 text-sm transition-all duration-200 ${
                        activeTab === 'autoresearch'
                            ? 'border-accent text-accent'
                            : 'border-transparent text-boxel-muted hover:text-boxel-ink'
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
