import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Button } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';

import type { DailyPrediction } from '../api/fetch-daily-predictions';
import { AutoresearchHistoryArena } from '../components/AutoresearchHistoryArena';
import { AutoresearchMilestoneCards } from '../components/AutoresearchMilestoneCards';
import { CuratedManifestCard } from '../components/CuratedManifestCard';
import { DailyMetricsOverview } from '../components/DailyMetricsOverview';
import { HeroPredictionCard } from '../components/HeroPredictionCard';
import { PredictionsTable } from '../components/PredictionsTable';
import {
    computeDailyPredictionStats,
    DEFAULT_DAILY_PREDICTOR_TOOLS,
    getPredictorModelsForTicker,
    PREDICTOR_MODELS,
    parseCuratedManifest,
    resolveActiveDailyPrompt,
    type SupportedDailyTicker,
} from '../utils/daily-predictions-helpers';

// Re-export for backwards compatibility with DailyPredictionsBacktestPage
export { DEFAULT_DAILY_PREDICTOR_TOOLS };

export interface DailyPredictionsPageProps {
    initialPredictions: DailyPrediction[];
    experiments: PromptExperiment[];
    initialTicker?: SupportedDailyTicker;
    refreshFn?: () => Promise<{ predictions: DailyPrediction[]; experiments: PromptExperiment[] }>;
}

interface AssetSwitcherProps {
    selectedTicker: SupportedDailyTicker;
    onSelectTicker: (ticker: SupportedDailyTicker) => void;
    spyCount: number;
    tltCount: number;
}

function AssetSwitcher({ selectedTicker, onSelectTicker, spyCount, tltCount }: AssetSwitcherProps) {
    return (
        <div className="flex flex-wrap items-center gap-2 mb-6 p-1 bg-zinc-100 dark:bg-zinc-800/60 rounded-2xl w-fit border border-zinc-200 dark:border-zinc-800">
            <Button
                type="button"
                variant={selectedTicker === 'SPY' ? 'solid' : 'ghost'}
                size="sm"
                onClick={() => onSelectTicker('SPY')}
                className={`rounded-xl font-bold text-xs uppercase tracking-wider transition-all px-4 py-2 ${
                    selectedTicker === 'SPY'
                        ? 'bg-blue-600 dark:bg-blue-500 text-white shadow-sm'
                        : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-100'
                }`}
            >
                <span className="flex items-center gap-1.5">
                    <span>📈 S&P 500 (SPY)</span>
                    <Badge variant="soft" size="xs" colorScheme="neutral">
                        {spyCount}
                    </Badge>
                </span>
            </Button>
            <Button
                type="button"
                variant={selectedTicker === 'TLT' ? 'solid' : 'ghost'}
                size="sm"
                onClick={() => onSelectTicker('TLT')}
                className={`rounded-xl font-bold text-xs uppercase tracking-wider transition-all px-4 py-2 ${
                    selectedTicker === 'TLT'
                        ? 'bg-blue-600 dark:bg-blue-500 text-white shadow-sm'
                        : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800 dark:hover:text-zinc-100'
                }`}
            >
                <span className="flex items-center gap-1.5">
                    <span>🏛️ 20+ Year Treasuries (TLT)</span>
                    <Badge variant="soft" size="xs" colorScheme="neutral">
                        {tltCount}
                    </Badge>
                </span>
            </Button>
        </div>
    );
}

function PredictorHeader({ selectedTicker }: { selectedTicker: SupportedDailyTicker }) {
    const isBond = selectedTicker === 'TLT';
    return (
        <div className="mb-6">
            <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-100 mb-2">
                {isBond ? 'Daily 20+ Year Treasury Bond Predictor' : 'Daily S&P Market Predictor'}
            </h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 m-0">
                {isBond
                    ? '9:15 AM ET Intraday (Open to Close) Directional Fixed Income Predictions on TLT powered by GPT-5.6 Luna, DeepSeek Flash & Jev.'
                    : '9:15 AM ET Intraday (Open to Close) Directional AI Predictions powered by DeepSeek Flash & MiniMax.'}
            </p>
        </div>
    );
}

export function DailyPredictionsPage({
    initialPredictions,
    experiments,
    initialTicker = 'SPY',
}: DailyPredictionsPageProps) {
    const [predictions] = useState<DailyPrediction[]>(initialPredictions);
    const [promptExperiments] = useState<PromptExperiment[]>(experiments);
    const [selectedTicker, setSelectedTicker] = useState<SupportedDailyTicker>(
        initialTicker === 'TLT' ? 'TLT' : 'SPY',
    );
    const currentModels = getPredictorModelsForTicker(selectedTicker);
    const [selectedModelId, setSelectedModelId] = useState<string>(
        (initialTicker === 'TLT'
            ? getPredictorModelsForTicker('TLT')[0]?.id
            : PREDICTOR_MODELS[0]?.id) || currentModels[0].id,
    );
    const [viewMode, setViewMode] = useState<'predictions' | 'autoresearch'>('predictions');
    const [selectedExpId, setSelectedExpId] = useState<string | null>(null);

    // Filter out simulated backtest predictions from live daily predictor view
    const livePredictions = predictions.filter(
        (p) => !p.prompt_variant_tag?.toLowerCase().includes('backtest'),
    );

    // Filter predictions by selected asset/ticker (defaulting missing ticker to SPY)
    const tickerPredictions = livePredictions.filter((p) => {
        const t = (p.ticker || 'SPY').toUpperCase();
        return t === selectedTicker;
    });

    const spyCount = livePredictions.filter(
        (p) => (p.ticker || 'SPY').toUpperCase() === 'SPY',
    ).length;
    const tltCount = livePredictions.filter((p) => (p.ticker || '').toUpperCase() === 'TLT').length;

    // Identify dynamic or configured models for current asset
    const activeModelCfg = currentModels.find((m) => m.id === selectedModelId) || currentModels[0];

    const modelPredictions = tickerPredictions.filter((p) => activeModelCfg.matches(p.model_name));
    const modelExperiments = promptExperiments.filter((e) =>
        e.track_id ? activeModelCfg.matches(e.track_id) : true,
    );

    const latestPrediction = modelPredictions.length > 0 ? modelPredictions[0] : null;
    const { correctCount, totalEvaluated, accuracyPct, intradayHitPct, avgBrier } =
        computeDailyPredictionStats(modelPredictions);

    const { activePrompt } = resolveActiveDailyPrompt(modelExperiments);
    const curatedManifest = parseCuratedManifest(activePrompt?.prompt_content);

    const handleSelectTicker = (newTicker: SupportedDailyTicker) => {
        if (newTicker === selectedTicker) return;
        setSelectedTicker(newTicker);
        const newModels = getPredictorModelsForTicker(newTicker);
        setSelectedModelId(newModels[0].id);
        try {
            if (typeof window !== 'undefined' && window.location) {
                const url = new URL(window.location.href);
                url.searchParams.set('ticker', newTicker);
                window.history.replaceState({}, '', url.toString());
            }
        } catch {
            // Ignore in test or non-browser environments
        }
    };

    return (
        <div className="w-full max-w-7xl mx-auto min-w-0 overflow-x-hidden p-6 font-sans">
            <AssetSwitcher
                selectedTicker={selectedTicker}
                onSelectTicker={handleSelectTicker}
                spyCount={spyCount}
                tltCount={tltCount}
            />

            <PredictorHeader selectedTicker={selectedTicker} />

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
                    {currentModels.map((model) => {
                        const count = tickerPredictions.filter((p) =>
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

                    {curatedManifest && <CuratedManifestCard manifest={curatedManifest} />}

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
