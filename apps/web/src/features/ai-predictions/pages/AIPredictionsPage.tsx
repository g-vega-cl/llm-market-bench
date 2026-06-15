import { useState } from 'react';
import type { SectorPrediction } from '../api/fetch-predictions';
import { AIPredictionChart } from '../components/AIPredictionChart';

export interface AIPredictionsPageProps {
    initialData: SectorPrediction[];
    refreshFn: () => Promise<SectorPrediction[]>;
}

export function AIPredictionsPage({ initialData, refreshFn }: AIPredictionsPageProps) {
    const [data, setData] = useState<SectorPrediction[]>(initialData);
    const [loading, setLoading] = useState(false);
    const [timeframeFilter, setTimeframeFilter] = useState<'7d' | '30d' | '60d' | '90d' | 'all'>(
        '7d',
    );

    const handleRefresh = async () => {
        setLoading(true);
        try {
            const newData = await refreshFn();
            setData(newData);
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

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
            <div className="flex justify-between items-center">
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
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors flex items-center gap-2"
                >
                    {loading ? 'Refreshing...' : 'Refresh Data'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                    <h2 className="text-xl font-bold text-blue-400 mb-2">DeepSeek Models</h2>
                    <div className="text-3xl font-light text-white mb-1">
                        {avgScore(deepSeekData)}{' '}
                        <span className="text-sm text-slate-400">Avg Percentile</span>
                    </div>
                    <p className="text-slate-400 text-sm">{deepSeekData.length} predictions made</p>
                </div>
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                    <h2 className="text-xl font-bold text-emerald-400 mb-2">MiniMax-M3</h2>
                    <div className="text-3xl font-light text-white mb-1">
                        {avgScore(miniMaxData)}{' '}
                        <span className="text-sm text-slate-400">Avg Percentile</span>
                    </div>
                    <p className="text-slate-400 text-sm">{miniMaxData.length} predictions made</p>
                </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
                    <h3 className="text-xl font-bold text-white">Historical Track Record</h3>
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
                                        Target: {new Date(pred.target_date).toLocaleDateString()} (
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
                                    <div className="text-sm text-slate-400 mb-1">Top Sector</div>
                                    <div className="text-lg font-bold text-white">
                                        {pred.predicted_sector}
                                    </div>
                                    {pred.status === 'evaluated' && (
                                        <div className="text-sm text-emerald-400 mt-1">
                                            Score: {pred.sector_percentile_score?.toFixed(1)}
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
    );
}
