import { Badge } from '@llm-market-bench/ui-design-system';
import type { LLMExecutionTrace } from '../types';

interface TraceInspectorBlockProps {
    prompt?: string;
    trace?: LLMExecutionTrace | null;
    toolCalls?: string[];
    fullOutput?: string;
    outputExcerpt?: string;
}

export function TraceInspectorBlock({
    prompt,
    trace,
    toolCalls = [],
    fullOutput,
    outputExcerpt,
}: TraceInspectorBlockProps) {
    const rounds = trace?.rounds ?? [];
    const finalOutput = fullOutput || outputExcerpt || '(Empty model output)';

    return (
        <div className="flex flex-col gap-4 min-w-0">
            {prompt && (
                <div className="flex flex-col gap-2 min-w-0">
                    <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                        Hydrated Prompt
                    </span>
                    <div className="voxel-trough bg-boxel-canvas border border-boxel-bevel-lo p-3 min-w-0">
                        <pre className="text-xs font-normal font-mono text-boxel-ink whitespace-pre-wrap break-words">
                            {prompt}
                        </pre>
                    </div>
                </div>
            )}

            {rounds.length > 0 ? (
                <div className="flex flex-col gap-3 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                            LLM Execution Trace ({rounds.length}{' '}
                            {rounds.length === 1 ? 'Round' : 'Rounds'})
                        </span>
                        {trace?.forced_final_synthesis && (
                            <Badge variant="outline" colorScheme="warning" size="xs">
                                Forced Final Synthesis
                            </Badge>
                        )}
                    </div>
                    {rounds.map((round) => (
                        <div
                            key={`round-${round.round}`}
                            className="voxel-trough bg-boxel-canvas border border-boxel-bevel-lo p-3 flex flex-col gap-2 min-w-0"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-boxel-bevel-lo pb-1">
                                <span className="text-xs font-bold font-mono text-boxel-ink">
                                    Round {round.round}
                                </span>
                                <span className="text-xs font-normal font-mono text-boxel-muted">
                                    {round.tool_calls.length} tool{' '}
                                    {round.tool_calls.length === 1 ? 'call' : 'calls'}
                                </span>
                            </div>

                            {round.reasoning && (
                                <div className="flex flex-col gap-1 min-w-0">
                                    <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                                        Reasoning / Thinking
                                    </span>
                                    <pre className="text-xs font-normal font-mono text-boxel-ink whitespace-pre-wrap break-words">
                                        {round.reasoning}
                                    </pre>
                                </div>
                            )}

                            {round.tool_calls.length > 0 && (
                                <div className="flex flex-col gap-2 min-w-0">
                                    <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                                        Tool Calls &amp; Results
                                    </span>
                                    {(() => {
                                        const seen = new Map<string, number>();
                                        return round.tool_calls.map((tc) => {
                                            const sig = `${round.round}-${tc.name}-${JSON.stringify(tc.args)}`;
                                            const count = (seen.get(sig) ?? 0) + 1;
                                            seen.set(sig, count);
                                            return (
                                                <div
                                                    key={`${sig}#${count}`}
                                                    className="bg-boxel-trough border border-boxel-bevel-lo p-2 flex flex-col gap-1 min-w-0"
                                                >
                                                    <code className="text-xs font-normal font-mono text-info break-all">
                                                        {tc.name}({JSON.stringify(tc.args)})
                                                    </code>
                                                    {tc.result && (
                                                        <pre className="text-xs font-normal font-mono text-boxel-muted whitespace-pre-wrap break-words">
                                                            {tc.result}
                                                        </pre>
                                                    )}
                                                </div>
                                            );
                                        });
                                    })()}
                                </div>
                            )}

                            {round.assistant_text &&
                                round.round < rounds.length &&
                                round.assistant_text !== finalOutput && (
                                    <div className="flex flex-col gap-1 min-w-0">
                                        <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                                            Assistant Notes
                                        </span>
                                        <pre className="text-xs font-normal font-mono text-boxel-ink whitespace-pre-wrap break-words">
                                            {round.assistant_text}
                                        </pre>
                                    </div>
                                )}
                        </div>
                    ))}
                </div>
            ) : (
                toolCalls.length > 0 && (
                    <div className="flex flex-col gap-2 min-w-0">
                        <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                            Tools Called
                        </span>
                        <div className="flex flex-col gap-2">
                            {(() => {
                                const seen = new Map<string, number>();
                                return toolCalls.map((tc) => {
                                    const count = (seen.get(tc) ?? 0) + 1;
                                    seen.set(tc, count);
                                    return (
                                        <code
                                            key={`${tc}#${count}`}
                                            className="text-xs font-normal font-mono text-info break-all"
                                        >
                                            {tc}
                                        </code>
                                    );
                                });
                            })()}
                        </div>
                    </div>
                )
            )}

            <div className="flex flex-col gap-2 min-w-0">
                <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                    Model Decision Output
                </span>
                <div className="voxel-trough bg-boxel-canvas border border-boxel-bevel-lo p-3 min-w-0">
                    <pre className="text-xs font-normal font-mono text-boxel-ink whitespace-pre-wrap break-words">
                        {finalOutput}
                    </pre>
                </div>
            </div>
        </div>
    );
}
