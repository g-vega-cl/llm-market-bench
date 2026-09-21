import { Badge } from '@llm-market-bench/ui-design-system';

export interface ExecutionTraceData {
    active_source_ids?: string[];
    newsletters?: {
        source_id: string;
        sender?: string | null;
        subject?: string | null;
    }[];
    tools_called?: {
        tool: string;
        // biome-ignore lint/suspicious/noExplicitAny: Arguments dictionary from tool loop
        args?: Record<string, any>;
        ticker?: string | null;
    }[];
    captured_at?: string;
}

interface ExecutionTraceViewProps {
    trace?: ExecutionTraceData | null;
}

export function ExecutionTraceView({ trace }: ExecutionTraceViewProps) {
    if (!trace) return null;

    const hasTools = Boolean(trace.tools_called && trace.tools_called.length > 0);
    const hasNewsletters = Boolean(trace.newsletters && trace.newsletters.length > 0);

    if (!hasTools && !hasNewsletters) return null;

    return (
        <div className="space-y-3 pt-2">
            <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full shadow-lg" />
                <span className="text-xs font-black text-zinc-400 uppercase tracking-widest">
                    Execution Provenance & Grounding
                </span>
            </div>

            <div className="bg-zinc-50 dark:bg-zinc-950/50 p-4 rounded-2xl border border-zinc-100 dark:border-zinc-900 space-y-3 text-xs">
                {hasTools && (
                    <div>
                        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block mb-1.5">
                            Tools Executed
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                            {trace.tools_called?.map((t) => {
                                const toolKey = `${t.tool}:${t.ticker ?? ''}:${JSON.stringify(t.args ?? {})}`;
                                return (
                                    <Badge
                                        key={toolKey}
                                        size="xs"
                                        variant="outline"
                                        colorScheme="neutral"
                                        radius="md"
                                    >
                                        {t.tool}
                                        {t.ticker ? `: ${t.ticker}` : ''}
                                    </Badge>
                                );
                            })}
                        </div>
                    </div>
                )}

                {hasNewsletters && (
                    <div>
                        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block mb-1.5">
                            Active Ingest Context ({trace.newsletters?.length} Newsletters)
                        </span>
                        <ul className="space-y-1 text-zinc-600 dark:text-zinc-400">
                            {trace.newsletters?.map((n) => (
                                <li key={n.source_id} className="truncate">
                                    <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                                        {n.sender || 'Newsletter'}:
                                    </span>{' '}
                                    {n.subject || n.source_id}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
}
