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
        <div className="flex items-center gap-2 bg-voxel-trough border border-voxel-bevel-hi px-3 py-1.5 rounded-none">
            <span className="text-sm uppercase font-bold text-voxel-muted">Conviction:</span>
            <div className="w-24 bg-voxel-canvas h-2 rounded-none overflow-hidden">
                <div className={`h-full rounded-none transition-all ${color}`} style={{ width }} />
            </div>
            <span className="font-mono text-sm font-bold text-voxel-ink">{confidence}%</span>
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
        <Card className="p-5 space-y-6 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <SectionHeading>Meta-Researcher Rationale & Conviction</SectionHeading>
                {confidence !== null && <ConvictionGauge confidence={confidence} />}
            </div>

            <div className="space-y-6 min-w-0">
                {/* Change Summary */}
                <div className="space-y-2">
                    <SubHeading>Change Summary</SubHeading>
                    <p className="text-voxel-muted italic text-sm break-words">
                        "{experiment.change_description || 'No description provided.'}"
                    </p>
                    <Badge
                        variant={experiment.experiment_type === 'baseline' ? 'solid' : 'soft'}
                        colorScheme={
                            experiment.experiment_type === 'baseline' ? 'accent' : 'neutral'
                        }
                    >
                        {experiment.experiment_type}
                    </Badge>
                </div>

                {/* Hypothesis */}
                {hypothesis && (
                    <div className="flex flex-col gap-2">
                        <SubHeading>Hypothesis</SubHeading>
                        <div className="p-4 bg-voxel-trough rounded-none text-xs font-normal text-voxel-ink border border-voxel-bevel-hi break-words">
                            {hypothesis}
                        </div>
                    </div>
                )}

                {/* Meta-Researcher Reasoning / Logic */}
                {reasoning && (
                    <div className="flex flex-col gap-2">
                        <SubHeading>Meta-Researcher Analytical Reasoning</SubHeading>
                        <div className="whitespace-pre-wrap break-words text-xs font-normal text-voxel-muted leading-relaxed bg-voxel-trough p-4 rounded-none border border-voxel-bevel-hi font-sans">
                            {reasoning}
                        </div>
                    </div>
                )}

                {/* Durable Institutional Memory / Insight */}
                {insight && (
                    <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-none flex flex-col gap-2 break-words">
                        <div className="flex items-center gap-2">
                            <span className="text-emerald-500 text-sm">💾</span>
                            <span className="text-sm font-bold uppercase tracking-wider text-success">
                                Durable Memory Saved for this Track
                            </span>
                        </div>
                        <p className="text-xs font-normal text-voxel-ink italic">"{insight}"</p>
                    </div>
                )}
            </div>
        </Card>
    );
}
