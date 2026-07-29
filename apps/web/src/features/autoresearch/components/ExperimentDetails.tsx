import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { BacktestTradesAudit } from './BacktestTradesAudit';
import { DailyScoreDisplay } from './DailyScoreDisplay';
import { PromptChanges } from './PromptChanges';
import { ScoreBreakdown } from './ScoreBreakdown';
import { VolatilityCalculation } from './VolatilityCalculation';

interface ExperimentDetailsProps {
    experiment: PromptExperiment;
    parentExperiment?: PromptExperiment | null;
}

export function ExperimentDetails({ experiment, parentExperiment }: ExperimentDetailsProps) {
    const metrics = experiment.metrics || {};
    const researchOutput = experiment.research_output || {};

    const excessReturnVal =
        metrics.excess_return !== undefined && metrics.excess_return !== null
            ? `${metrics.excess_return.toFixed(2)}%`
            : 'N/A';
    const volatilityVal =
        metrics.volatility !== undefined && metrics.volatility !== null
            ? `${metrics.volatility.toFixed(2)}%`
            : 'N/A';
    const maxDrawdownVal =
        metrics.max_drawdown !== undefined && metrics.max_drawdown !== null
            ? `${metrics.max_drawdown.toFixed(2)}%`
            : 'N/A';

    return (
        <div className="space-y-8 animate-slide-up">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Excess Return" value={excessReturnVal} />
                <MetricTile icon="📊" label="Volatility" value={volatilityVal} />
                <MetricTile icon="📉" label="Max Drawdown" value={maxDrawdownVal} />
            </div>

            <DailyScoreDisplay experiment={experiment} />

            <ScoreBreakdown experiment={experiment} />

            <VolatilityCalculation experiment={experiment} />

            <BacktestTradesAudit experiment={experiment} />

            {/* Weekly Toolbox Configuration & Pivot Delta */}
            {(() => {
                const selectedTools: string[] =
                    (researchOutput as { selected_tools?: string[] }).selected_tools || [];
                const parentSelectedTools: string[] =
                    (parentExperiment?.research_output as { selected_tools?: string[] })
                        ?.selected_tools || [];

                if (selectedTools.length === 0) return null;

                const allToolboxTools = [
                    {
                        name: 'get_portfolio_ledger',
                        desc: 'Pull portfolio ledger XML, cash, SMA & positions',
                    },
                    {
                        name: 'get_todays_news_menu',
                        desc: "Summarized menu of today's news headlines",
                    },
                    {
                        name: 'get_market_feeling',
                        desc: 'Retrieve qualitative daily AI market feeling',
                    },
                    {
                        name: 'search_past_memories',
                        desc: 'Semantic pgvector search of lessons learned',
                    },
                    { name: 'web_search', desc: 'General web search grounding' },
                    { name: 'get_stock_quote', desc: 'Real-time stock price lookup' },
                    { name: 'get_price_history', desc: 'Historical price tracking' },
                    { name: 'get_position_pnl', desc: 'Detailed profit & loss statistics' },
                    { name: 'get_volatility_metrics', desc: 'Calculates asset price volatility' },
                    {
                        name: 'get_sector_alternatives',
                        desc: 'Identifies sector-based alternatives',
                    },
                    { name: 'search_related_tickers', desc: 'Thematic keyword stock searches' },
                    { name: 'run_stock_screener', desc: 'Screens assets by ratios and volumes' },
                    {
                        name: 'find_uncorrelated_assets',
                        desc: 'Screens for uncorrelated portfolio assets',
                    },
                    { name: 'get_key_metrics', desc: 'Financial ratio extraction' },
                    {
                        name: 'get_market_health_barometer',
                        desc: 'Cap-weighted index valuation check',
                    },
                    { name: 'get_earnings_history', desc: 'Earnings calendar events' },
                    { name: 'search_prediction_markets', desc: 'Kalshi/Polymarket event lookup' },
                    {
                        name: 'get_prediction_market_odds',
                        desc: 'Event resolution probability odds',
                    },
                    {
                        name: 'audit_financial_valuation',
                        desc: 'Quarterly financial/DCF audit models',
                    },
                    {
                        name: 'fetch_newsletter_content',
                        desc: 'Fetch full-text of newsletters by source IDs',
                    },
                ];

                const added = selectedTools.filter((t) => !parentSelectedTools.includes(t));
                const removed = parentSelectedTools.filter((t) => !selectedTools.includes(t));
                const hasDelta = added.length > 0 || removed.length > 0;

                return (
                    <Card className="p-8 space-y-6">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="space-y-1">
                                <SectionHeading>Weekly Toolbox Configuration</SectionHeading>
                                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                                    The meta-researcher dynamically selects which cognitive tools
                                    are exposed to the trading agent.
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="outline">
                                    {selectedTools.length} / {allToolboxTools.length} Tools Enabled
                                </Badge>
                            </div>
                        </div>

                        {/* Tool Delta (Pivot Highlights) */}
                        {parentExperiment && hasDelta && (
                            <div className="p-4 bg-zinc-50 dark:bg-zinc-900/50 rounded-xl border border-zinc-200 dark:border-zinc-800 space-y-3">
                                <h4 className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                                    Cognitive Tool Evolution (Pivot Delta)
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                    {added.map((tool) => (
                                        <div
                                            key={tool}
                                            className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-xs font-semibold rounded-full"
                                        >
                                            <span className="font-mono">+ {tool}</span>
                                            <span className="text-[10px] opacity-85">(added)</span>
                                        </div>
                                    ))}
                                    {removed.map((tool) => (
                                        <div
                                            key={tool}
                                            className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 text-xs font-semibold rounded-full line-through"
                                        >
                                            <span className="font-mono">- {tool}</span>
                                            <span className="text-[10px] opacity-85">
                                                (removed)
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Complete Toolbox Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {allToolboxTools.map((tool) => {
                                const isEnabled = selectedTools.includes(tool.name);
                                const wasEnabled = parentSelectedTools.includes(tool.name);
                                const isNewAddition = isEnabled && parentExperiment && !wasEnabled;

                                return (
                                    <div
                                        key={tool.name}
                                        className={`p-4 rounded-xl border transition-all duration-200 flex flex-col justify-between space-y-2 ${
                                            isEnabled
                                                ? 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800'
                                                : 'bg-zinc-100/50 dark:bg-zinc-950/20 border-zinc-200/50 dark:border-zinc-900/40 opacity-40'
                                        } ${isNewAddition ? 'ring-1 ring-emerald-500/30 border-emerald-500/30' : ''}`}
                                    >
                                        <div className="space-y-1">
                                            <div className="flex items-center justify-between">
                                                <span
                                                    className={`font-mono text-xs font-semibold ${isEnabled ? 'text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 dark:text-zinc-600 line-through'}`}
                                                >
                                                    {tool.name}
                                                </span>
                                                {isEnabled ? (
                                                    <span className="text-emerald-500 text-xs font-bold flex items-center gap-1">
                                                        ✓{' '}
                                                        {isNewAddition && (
                                                            <span className="text-[9px] bg-emerald-500 text-white dark:text-zinc-950 px-1 py-0.5 rounded font-sans font-normal uppercase animate-pulse">
                                                                new
                                                            </span>
                                                        )}
                                                    </span>
                                                ) : (
                                                    <span className="text-zinc-400 dark:text-zinc-700 text-xs">
                                                        ✗
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-normal">
                                                {tool.desc}
                                            </p>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </Card>
                );
            })()}

            <Card className="p-8 space-y-6">
                <SectionHeading>Research Progression</SectionHeading>
                <div className="space-y-6">
                    <div className="space-y-2">
                        <SubHeading>Change Summary</SubHeading>
                        <p className="text-zinc-600 dark:text-zinc-400 italic">
                            "{experiment.change_description || 'No description provided.'}"
                        </p>
                        <Badge
                            variant={experiment.experiment_type === 'baseline' ? 'solid' : 'soft'}
                        >
                            {experiment.experiment_type}
                        </Badge>
                    </div>

                    {researchOutput.hypothesis && (
                        <div className="space-y-2">
                            <SubHeading>Hypothesis</SubHeading>
                            <div className="p-4 bg-zinc-50 dark:bg-zinc-900 rounded-lg text-sm text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800">
                                {researchOutput.hypothesis}
                            </div>
                        </div>
                    )}

                    {researchOutput.thought_process && (
                        <div className="space-y-2">
                            <SubHeading>Meta-Researcher Logic</SubHeading>
                            <div className="whitespace-pre-wrap text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                                {researchOutput.thought_process}
                            </div>
                        </div>
                    )}
                </div>
            </Card>

            <PromptChanges experiment={experiment} parentExperiment={parentExperiment} />

            <Card className="p-8 space-y-4">
                <SectionHeading>The Trading Prompt</SectionHeading>
                <div className="relative group">
                    <pre className="p-6 bg-zinc-950 text-zinc-300 rounded-xl overflow-x-auto text-xs font-mono leading-relaxed border border-zinc-800 max-h-[600px] overflow-y-auto">
                        {experiment.prompt_content}
                    </pre>
                    <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                        <div className="px-2 py-1 bg-zinc-800 text-zinc-400 text-[10px] uppercase rounded border border-zinc-700">
                            v{experiment.variant_tag}
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    );
}
