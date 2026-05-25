import type { PromptExperiment } from '@llm-market-bench/database';
import {
    Badge,
    Card,
    MetricTile,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { ScoreBreakdown } from './ScoreBreakdown';

interface ExperimentDetailsProps {
    experiment: PromptExperiment;
}

export function ExperimentDetails({ experiment }: ExperimentDetailsProps) {
    const metrics = experiment.metrics || {};
    const researchOutput = experiment.research_output || {};

    return (
        <div className="space-y-8 animate-slide-up">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricTile label="Excess Return" value={`${metrics.excess_return?.toFixed(2)}%`} />
                <MetricTile
                    icon="📊"
                    label="Volatility"
                    value={`${metrics.volatility?.toFixed(2)}%`}
                />
                <MetricTile
                    icon="📉"
                    label="Max Drawdown"
                    value={`${metrics.max_drawdown?.toFixed(2)}%`}
                />
            </div>

            <ScoreBreakdown experiment={experiment} />

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
