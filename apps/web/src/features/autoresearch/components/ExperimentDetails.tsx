import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card, MetricTile, SectionHeading } from '@llm-market-bench/ui-design-system';
import { isExperimentColdStart } from '../utils/coldStart';
import { splitPromptSections } from '../utils/promptSections';
import { BacktestTradesAudit } from './BacktestTradesAudit';
import { CognitiveToolboxCard } from './CognitiveToolboxCard';
import { DailyScoreDisplay } from './DailyScoreDisplay';
import { PromptBlocksCard } from './PromptBlocksCard';
import { PromptChanges } from './PromptChanges';
import { ResearchRationaleCard } from './ResearchRationaleCard';
import { ScoreBreakdown } from './ScoreBreakdown';
import { formatTrackLabel } from './TrackTabs';
import { VolatilityCalculation } from './VolatilityCalculation';

interface ExperimentDetailsProps {
    experiment: PromptExperiment;
    parentExperiment?: PromptExperiment | null;
}

export function ExperimentDetails({ experiment, parentExperiment }: ExperimentDetailsProps) {
    const metrics = experiment.metrics || {};
    const researchOutput = experiment.research_output || {};

    const trackLabel = formatTrackLabel(experiment.track_id);
    const isCold = isExperimentColdStart(experiment);

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
        <div className="flex flex-col gap-6 animate-slide-up">
            <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-none voxel-trough border border-boxel-bevel-hi">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                        Optimization Track:
                    </span>
                    <Badge colorScheme="accent" variant="soft">
                        {trackLabel}
                    </Badge>
                    {isCold && (
                        <Badge colorScheme="warning" variant="soft" size="sm">
                            From 0
                        </Badge>
                    )}
                </div>

                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold uppercase tracking-wider text-boxel-muted">
                        Experiment Type:
                    </span>
                    <Badge variant="soft" size="sm">
                        {experiment.experiment_type}
                    </Badge>
                </div>
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch">
                <MetricTile label="Excess Return" value={excessReturnVal} />
                <MetricTile icon="📊" label="Volatility" value={volatilityVal} />
                <MetricTile icon="📉" label="Max Drawdown" value={maxDrawdownVal} />
            </div>

            <DailyScoreDisplay experiment={experiment} />

            <ScoreBreakdown experiment={experiment} />

            <VolatilityCalculation experiment={experiment} />

            <BacktestTradesAudit experiment={experiment} />

            <CognitiveToolboxCard
                selectedTools={(researchOutput as { selected_tools?: string[] }).selected_tools}
                parentSelectedTools={
                    (parentExperiment?.research_output as { selected_tools?: string[] })
                        ?.selected_tools
                }
                title="Weekly Toolbox Configuration"
                subtitle="The meta-researcher dynamically selects which cognitive tools are exposed to the trading agent."
            />

            <PromptBlocksCard
                selectedBlocks={
                    (researchOutput as { selected_prompt_blocks?: string[] })
                        ?.selected_prompt_blocks
                }
                parentSelectedBlocks={
                    (parentExperiment?.research_output as { selected_prompt_blocks?: string[] })
                        ?.selected_prompt_blocks
                }
            />

            <ResearchRationaleCard experiment={experiment} />

            <PromptChanges experiment={experiment} parentExperiment={parentExperiment} />

            {(() => {
                const { header, mutable, footer, isSplit } = splitPromptSections(
                    experiment.prompt_content,
                );

                if (!isSplit) {
                    return (
                        <Card className="p-6 flex flex-col gap-4">
                            <div className="flex items-center justify-between">
                                <SectionHeading>The Trading Prompt</SectionHeading>
                                <Badge variant="outline">v{experiment.variant_tag}</Badge>
                            </div>
                            <div className="relative group">
                                <pre className="p-6 bg-boxel-canvas text-boxel-ink rounded-none overflow-x-auto text-xs font-mono font-normal leading-relaxed border border-boxel-bevel-hi max-h-[600px] overflow-y-auto">
                                    {experiment.prompt_content}
                                </pre>
                            </div>
                        </Card>
                    );
                }

                return (
                    <Card className="p-6 flex flex-col gap-6">
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="flex flex-col gap-1">
                                <SectionHeading>The Trading Prompt</SectionHeading>
                                <p className="text-xs font-normal text-boxel-muted">
                                    System breakdown of engine constraints vs. prompt strategies
                                    mutated by autoresearch.
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="outline">v{experiment.variant_tag}</Badge>
                            </div>
                        </div>

                        <div className="flex flex-col gap-6">
                            {/* Section 1: Engine Constraints & Tool Protocols (FROZEN) */}
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-boxel-ink">
                                            🔒 1. Engine Constraints & Tool Protocols
                                        </span>
                                        <span className="text-xs font-normal text-boxel-muted font-mono">
                                            (Header)
                                        </span>
                                    </div>
                                    <Badge
                                        variant="solid"
                                        className="bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase"
                                    >
                                        Frozen / System Managed
                                    </Badge>
                                </div>
                                <p className="text-xs font-normal text-boxel-muted">
                                    Unchangeable system rules (price injection rules, tool
                                    requirements, RAG/memory protocols). Autoresearch cannot edit
                                    this.
                                </p>
                                <pre className="p-4 bg-boxel-trough text-boxel-muted rounded-none overflow-x-auto text-xs font-mono font-normal leading-relaxed border border-amber-500/20 max-h-[250px] overflow-y-auto">
                                    {header}
                                </pre>
                            </div>

                            {/* Section 2: Trading Strategy & Analysis Rules (MUTABLE) */}
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-boxel-ink">
                                            ⚡ 2. Trading Strategy & Analysis Rules
                                        </span>
                                        <span className="text-xs font-normal text-emerald-400 font-mono">
                                            (Evolved Target)
                                        </span>
                                    </div>
                                    <Badge
                                        variant="solid"
                                        className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase"
                                    >
                                        Mutable / Evolved by Autoresearch
                                    </Badge>
                                </div>
                                <p className="text-xs font-normal text-boxel-muted">
                                    Trading philosophy, reasoning frameworks, entry/exit logic, and
                                    portfolio management rules. This section is iteratively tested
                                    and optimized by autoresearch.
                                </p>
                                <pre className="p-4 bg-boxel-canvas text-boxel-ink rounded-none overflow-x-auto text-xs font-mono font-normal leading-relaxed border border-emerald-500/30 ring-1 ring-emerald-500/20 max-h-[400px] overflow-y-auto">
                                    {mutable}
                                </pre>
                            </div>

                            {/* Section 3: Risk Rules & Output JSON Format (FROZEN) */}
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-bold text-boxel-ink">
                                            🔒 3. Risk Rules & Output JSON Schema
                                        </span>
                                        <span className="text-xs font-normal text-boxel-muted font-mono">
                                            (Footer)
                                        </span>
                                    </div>
                                    <Badge
                                        variant="solid"
                                        className="bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase"
                                    >
                                        Frozen / System Managed
                                    </Badge>
                                </div>
                                <p className="text-xs font-normal text-boxel-muted">
                                    SMA margin rules, trade signal definitions, and mandatory
                                    structured JSON output schema. Autoresearch cannot edit this.
                                </p>
                                <pre className="p-4 bg-boxel-trough text-boxel-muted rounded-none overflow-x-auto text-xs font-mono font-normal leading-relaxed border border-amber-500/20 max-h-[250px] overflow-y-auto">
                                    {footer}
                                </pre>
                            </div>
                        </div>
                    </Card>
                );
            })()}
        </div>
    );
}
