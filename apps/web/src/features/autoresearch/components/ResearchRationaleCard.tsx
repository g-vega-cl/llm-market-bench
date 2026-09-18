import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading, SubHeading } from '@llm-market-bench/ui-design-system';

interface ResearchRationaleCardProps {
    experiment: PromptExperiment;
}

function getConfidenceColor(confidence: number): string {
    if (confidence >= 75) return 'bg-emerald-500';
    if (confidence >= 50) return 'bg-amber-500';
    return 'bg-rose-500';
}

function ConvictionGauge({ confidence }: { confidence: number }) {
    const color = getConfidenceColor(confidence);
    const width = `${Math.min(100, Math.max(0, confidence))}%`;
    return (
        <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-xl">
            <span className="text-[10px] uppercase font-bold text-zinc-400">Conviction:</span>
            <div className="w-24 bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all ${color}`} style={{ width }} />
            </div>
            <span className="font-mono text-xs font-bold text-zinc-200">{confidence}%</span>
        </div>
    );
}

export function ResearchRationaleCard({ experiment }: ResearchRationaleCardProps) {
    const researchOutput = (experiment.research_output || {}) as Record<string, unknown>;
    const reasoning =
        (researchOutput.research_reasoning as string) ||
        (researchOutput.thought_process as string) ||
        null;
    const hypothesis = (researchOutput.hypothesis as string) || null;
    const insight = (researchOutput.research_insight as string) || null;
    const rawConfidence =
        typeof researchOutput.confidence === 'number'
            ? (researchOutput.confidence as number)
            : null;
    const confidence =
        rawConfidence !== null
            ? rawConfidence <= 1.0
                ? Math.round(rawConfidence * 100)
                : Math.round(rawConfidence)
            : null;

    return (
        <Card className="p-8 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading>Meta-Researcher Rationale & Conviction</SectionHeading>
                {confidence !== null && <ConvictionGauge confidence={confidence} />}
            </div>

            <div className="space-y-6">
                {/* Change Summary */}
                <div className="space-y-2">
                    <SubHeading>Change Summary</SubHeading>
                    <p className="text-zinc-600 dark:text-zinc-400 italic text-sm">
                        "{experiment.change_description || 'No description provided.'}"
                    </p>
                    <Badge variant={experiment.experiment_type === 'baseline' ? 'solid' : 'soft'}>
                        {experiment.experiment_type}
                    </Badge>
                </div>

                {/* Hypothesis */}
                {hypothesis && (
                    <div className="space-y-2">
                        <SubHeading>Hypothesis</SubHeading>
                        <div className="p-4 bg-zinc-50 dark:bg-zinc-900 rounded-lg text-sm text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800">
                            {hypothesis}
                        </div>
                    </div>
                )}

                {/* Meta-Researcher Reasoning / Logic */}
                {reasoning && (
                    <div className="space-y-2">
                        <SubHeading>Meta-Researcher Analytical Reasoning</SubHeading>
                        <div className="whitespace-pre-wrap text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed bg-zinc-50 dark:bg-zinc-900/50 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 font-sans">
                            {reasoning}
                        </div>
                    </div>
                )}

                {/* Durable Institutional Memory / Insight */}
                {insight && (
                    <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl space-y-2">
                        <div className="flex items-center gap-2">
                            <span className="text-emerald-500 text-sm">💾</span>
                            <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                                Durable Memory Saved for this Track
                            </span>
                        </div>
                        <p className="text-sm text-zinc-700 dark:text-zinc-300 italic">
                            "{insight}"
                        </p>
                    </div>
                )}
            </div>
        </Card>
    );
}
