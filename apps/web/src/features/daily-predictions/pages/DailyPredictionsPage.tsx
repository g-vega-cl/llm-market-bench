import type { PromptExperiment } from '@llm-market-bench/database';
import { Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';

import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { AutoresearchHistoryArena } from '../components/AutoresearchHistoryArena';
import { AutoresearchMilestoneCards } from '../components/AutoresearchMilestoneCards';
import { DailyMetricsOverview } from '../components/DailyMetricsOverview';
import { HeroPredictionCard } from '../components/HeroPredictionCard';
import { PredictionsTable } from '../components/PredictionsTable';
import {
    computeDailyPredictionStats,
    DEFAULT_DAILY_PREDICTOR_TOOLS,
    PREDICTOR_MODELS,
    resolveActiveDailyPrompt,
} from '../utils/daily-predictions-helpers';

// Re-export for backwards compatibility with DailyPredictionsBacktestPage
export { DEFAULT_DAILY_PREDICTOR_TOOLS };

export interface DailyPredictionsPageProps {
    initialPredictions: DailyPrediction[];
    experiments: PromptExperiment[];
    refreshFn?: () => Promise<{ predictions: DailyPrediction[]; experiments: PromptExperiment[] }>;
}

export function DailyPredictionsPage({
    initialPredictions,
    experiments,
}: DailyPredictionsPageProps) {
    const [predictions] = useState<DailyPrediction[]>(initialPredictions);
    const [promptExperiments] = useState<PromptExperiment[]>(experiments);
    const [selectedModelId, setSelectedModelId] = useState<string>(PREDICTOR_MODELS[0].id);
    const [viewMode, setViewMode] = useState<'predictions' | 'autoresearch'>('predictions');
    const [selectedExpId, setSelectedExpId] = useState<string | null>(null);

    // Filter out simulated backtest predictions from live daily predictor view
    const livePredictions = predictions.filter(
        (p) => !p.prompt_variant_tag?.toLowerCase().includes('backtest'),
    );

    // Identify dynamic or configured models
    const activeModelCfg =
        PREDICTOR_MODELS.find((m) => m.id === selectedModelId) || PREDICTOR_MODELS[0];

    const modelPredictions = livePredictions.filter((p) => activeModelCfg.matches(p.model_name));
    const modelExperiments = promptExperiments.filter((e) =>
        e.track_id ? activeModelCfg.matches(e.track_id) : true,
    );

    const latestPrediction = modelPredictions.length > 0 ? modelPredictions[0] : null;
    const { correctCount, totalEvaluated, accuracyPct, intradayHitPct, avgBrier } =
        computeDailyPredictionStats(modelPredictions);

    const { activePrompt } = resolveActiveDailyPrompt(modelExperiments);

    return (
        <div className="w-full max-w-7xl mx-auto min-w-0 overflow-x-hidden p-6 font-sans">
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
                    Daily S&P Market Predictor
                </h1>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 m-0">
                    9:15 AM ET Intraday (Open to Close) Directional AI Predictions powered by
                    DeepSeek Flash & MiniMax.
                </p>
            </div>

            {/* Model Navigation Tabs and Relocated Backtest Arena Button */}
            <div
                style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '16px',
                }}
                className="border-b-2 border-zinc-200 dark:border-zinc-800 mb-5"
            >
                <div className="flex gap-2">
                    {PREDICTOR_MODELS.map((model) => {
                        const count = livePredictions.filter((p) =>
                            model.matches(p.model_name),
                        ).length;
                        const isSelected = activeModelCfg.id === model.id;
                        return (
                            <button
                                key={model.id}
                                type="button"
                                onClick={() => setSelectedModelId(model.id)}
                                className={`px-5 py-3 border-none bg-transparent font-semibold text-sm cursor-pointer transition-colors -mb-0.5 border-b-2 ${
                                    isSelected
                                        ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                                        : 'text-zinc-500 dark:text-zinc-400 border-transparent hover:text-zinc-700 dark:hover:text-zinc-200'
                                }`}
                            >
                                {model.label} ({count})
                            </button>
                        );
                    })}
                </div>

                <div className="pb-2">
                    <Link
                        to="/daily-predictions-backtest"
                        className="px-4 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 no-underline font-semibold text-sm border border-zinc-300 dark:border-zinc-700 inline-flex items-center gap-1 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                    >
                        Backtest Arena ↗
                    </Link>
                </div>
            </div>

            {/* Sub-view Switcher: Predictions Log vs Autoresearch & Benchmark History */}
            <div className="inline-flex bg-zinc-100 dark:bg-zinc-800/60 p-1 rounded-xl mb-6 gap-1 border border-zinc-200 dark:border-zinc-800">
                <Button
                    type="button"
                    variant={viewMode === 'predictions' ? 'solid' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('predictions')}
                    className={`rounded-lg font-semibold text-xs transition-all ${
                        viewMode === 'predictions'
                            ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm'
                            : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
                    }`}
                >
                    Predictions Log
                </Button>
                <Button
                    type="button"
                    variant={viewMode === 'autoresearch' ? 'solid' : 'ghost'}
                    size="sm"
                    onClick={() => setViewMode('autoresearch')}
                    className={`rounded-lg font-semibold text-xs transition-all ${
                        viewMode === 'autoresearch'
                            ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm'
                            : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200'
                    }`}
                >
                    Autoresearch & Benchmark History
                </Button>
            </div>

            {viewMode === 'predictions' ? (
                <>
                    <DailyMetricsOverview
                        accuracyPct={accuracyPct}
                        intradayHitPct={intradayHitPct}
                        correctCount={correctCount}
                        totalEvaluated={totalEvaluated}
                        avgBrier={avgBrier}
                        totalPredictions={modelPredictions.length}
                        activePromptTag={activePrompt?.variant_tag || 'daily-pred-baseline'}
                    />

                    {latestPrediction && <HeroPredictionCard prediction={latestPrediction} />}

                    <PredictionsTable
                        predictions={modelPredictions}
                        experiments={promptExperiments}
                    />
                </>
            ) : (
                <>
                    <AutoresearchMilestoneCards experiments={modelExperiments} />
                    <AutoresearchHistoryArena
                        experiments={modelExperiments}
                        predictions={modelPredictions}
                        selectedExpId={selectedExpId}
                        activePromptTag={activePrompt?.variant_tag}
                        onSelectExp={(id) => setSelectedExpId(id)}
                    />
                </>
            )}
        </div>
    );
}
