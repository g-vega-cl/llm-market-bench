import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import toolsConfig from '@repo/config/tools.json';

export interface CognitiveToolboxCardProps {
    selectedTools?: string[] | null;
    parentSelectedTools?: string[] | null;
    title?: string;
    subtitle?: string;
    emptyFallbackText?: string;
}

export function CognitiveToolboxCard({
    selectedTools = [],
    parentSelectedTools = [],
    title = 'Cognitive Toolbox Configuration',
    subtitle = 'The meta-researcher dynamically selects which cognitive tools are exposed to the agent.',
    emptyFallbackText = 'No specific cognitive tools were configured for this experiment.',
}: CognitiveToolboxCardProps) {
    const activeTools = selectedTools || [];
    const parentTools = parentSelectedTools || [];

    if (activeTools.length === 0) {
        return (
            <Card className="p-6 space-y-3 bg-zinc-50/50 dark:bg-zinc-900/30 border-zinc-200 dark:border-zinc-800">
                <div className="flex items-center justify-between">
                    <SectionHeading>{title}</SectionHeading>
                    <Badge variant="soft" size="sm">
                        0 Tools
                    </Badge>
                </div>
                <p className="text-xs text-zinc-500 italic">{emptyFallbackText}</p>
            </Card>
        );
    }

    const catalogTools: { name: string; desc: string }[] = toolsConfig;
    const knownToolNames = new Set(catalogTools.map((t) => t.name));

    // Dynamically absorb any unknown or newly introduced tools in the experiment
    const extraTools = activeTools
        .filter((name) => !knownToolNames.has(name))
        .map((name) => ({
            name,
            desc: 'Trading agent cognitive tool',
        }));

    const allToolboxTools = [...catalogTools, ...extraTools];

    const added = activeTools.filter((t) => !parentTools.includes(t));
    const removed = parentTools.filter((t) => !activeTools.includes(t));
    const hasDelta = (parentTools.length > 0 && (added.length > 0 || removed.length > 0)) || false;

    return (
        <Card className="p-8 space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <SectionHeading>{title}</SectionHeading>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">{subtitle}</p>
                </div>
                <div className="flex items-center gap-2">
                    <Badge variant="outline">
                        {activeTools.length} / {allToolboxTools.length} Tools Enabled
                    </Badge>
                </div>
            </div>

            {/* Tool Delta (Pivot Highlights) */}
            {hasDelta && (
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
                                <span className="text-[10px] opacity-85">(removed)</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Complete Toolbox Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {allToolboxTools.map((tool) => {
                    const isEnabled = activeTools.includes(tool.name);
                    const wasEnabled = parentTools.includes(tool.name);
                    const isNewAddition = isEnabled && parentTools.length > 0 && !wasEnabled;

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
}
