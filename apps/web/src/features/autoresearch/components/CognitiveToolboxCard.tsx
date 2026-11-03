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
        <Card className="p-5 space-y-6 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-4">
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
                <div className="p-4 bg-boxel-canvas rounded-none border border-boxel-bevel-hi flex flex-col gap-3">
                    <h4 className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        Cognitive Tool Evolution (Pivot Delta)
                    </h4>
                    <div className="flex flex-wrap gap-2">
                        {added.map((tool) => (
                            <div
                                key={tool}
                                className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-normal rounded-none min-w-0"
                            >
                                <span className="font-mono break-all">+ {tool}</span>
                                <span className="text-xs font-normal opacity-85 shrink-0">
                                    (added)
                                </span>
                            </div>
                        ))}
                        {removed.map((tool) => (
                            <div
                                key={tool}
                                className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-normal rounded-none line-through min-w-0"
                            >
                                <span className="font-mono break-all">- {tool}</span>
                                <span className="text-xs font-normal opacity-85 shrink-0">
                                    (removed)
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Complete Toolbox Grid */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,15rem),1fr))] gap-3 items-stretch">
                {allToolboxTools.map((tool) => {
                    const isEnabled = activeTools.includes(tool.name);
                    const wasEnabled = parentTools.includes(tool.name);
                    const isNewAddition = isEnabled && parentTools.length > 0 && !wasEnabled;

                    return (
                        <div
                            key={tool.name}
                            className={`p-4 rounded-none h-full border transition-all duration-200 flex flex-col justify-between gap-2 min-w-0 overflow-hidden ${
                                isEnabled
                                    ? 'bg-boxel-trough border-boxel-bevel-hi'
                                    : 'bg-boxel-canvas/40 border-boxel-bevel-lo opacity-40'
                            } ${isNewAddition ? 'ring-1 ring-emerald-500/30 border-emerald-500/30' : ''}`}
                        >
                            <div className="flex flex-col gap-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                    <span
                                        className={`font-mono text-xs font-normal break-all ${isEnabled ? 'text-boxel-ink' : 'text-boxel-muted line-through'}`}
                                    >
                                        {tool.name}
                                    </span>
                                    {isEnabled ? (
                                        <span className="text-emerald-400 text-xs font-normal flex items-center gap-1 shrink-0">
                                            ✓{' '}
                                            {isNewAddition && (
                                                <span className="text-xs bg-emerald-500 text-boxel-trough px-1 py-0.5 rounded-none font-sans font-normal uppercase animate-pulse">
                                                    new
                                                </span>
                                            )}
                                        </span>
                                    ) : (
                                        <span className="text-boxel-muted text-xs font-normal shrink-0">
                                            ✗
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs font-normal text-boxel-muted leading-normal break-words">
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
