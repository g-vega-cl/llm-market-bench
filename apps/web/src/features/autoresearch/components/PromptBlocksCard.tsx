import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';

export interface PromptBlockInfo {
    id: string;
    title: string;
    desc: string;
}

export const KNOWN_PROMPT_BLOCKS: PromptBlockInfo[] = [
    {
        id: 'let_winners_run',
        title: 'LET WINNERS RUN',
        desc: 'Momentum trailing profit ratchet and scale-in rules to avoid premature liquidation.',
    },
    {
        id: 'cut_losers_fast',
        title: 'CUT LOSERS FAST',
        desc: 'Rapid thesis invalidation and asymmetric stop-loss guardrails to eliminate sunk-cost bias.',
    },
    {
        id: 'catalyst_expiry_timer',
        title: 'CATALYST EXPIRY TIMER',
        desc: 'Enforces strict position duration matching the expected news cycle to free dead capital.',
    },
    {
        id: 'five_whys_causal',
        title: '5 WHYS CAUSAL DEPTH',
        desc: 'Drills down to root supply/demand drivers rather than reacting to superficial headlines.',
    },
    {
        id: 'mece_risk_partition',
        title: 'MECE RISK PARTITIONING',
        desc: 'Partitions risk and macro scenarios into Mutually Exclusive, Collectively Exhaustive buckets.',
    },
    {
        id: 'options_vol_discipline',
        title: 'OPTIONS VOLATILITY CONE',
        desc: 'Bounds expected price targets within the 1-sigma options-implied volatility cone.',
    },
    {
        id: 'macro_regime_routing',
        title: 'MACRO REGIME ROUTING',
        desc: 'Routes portfolio posture based on yield curve inversions, real rates, and dollar liquidity.',
    },
    {
        id: 'disconfirming_evidence_gate',
        title: 'DISCONFIRMING EVIDENCE GATE',
        desc: 'Mandates active search for counter-theses and falsifying data before trade execution.',
    },
    {
        id: 'catalyst_radar_discipline',
        title: 'CATALYST RADAR DISCIPLINE',
        desc: 'Aligns execution timing with calendar earnings, FDA dates, and investor days.',
    },
    {
        id: 'ticker_news_verification',
        title: 'TICKER NEWS VERIFICATION',
        desc: 'Ensures news catalysts are recent, authoritative, and material to the underlying asset.',
    },
];

export interface PromptBlocksCardProps {
    selectedBlocks?: string[] | null;
    parentSelectedBlocks?: string[] | null;
}

export function PromptBlocksCard({
    selectedBlocks = [],
    parentSelectedBlocks = [],
}: PromptBlocksCardProps) {
    const activeBlocks = selectedBlocks || [];
    const parentBlocks = parentSelectedBlocks || [];

    if (activeBlocks.length === 0) {
        return null;
    }

    const knownIds = new Set(KNOWN_PROMPT_BLOCKS.map((b) => b.id));
    const extraBlocks: PromptBlockInfo[] = activeBlocks
        .filter((id) => !knownIds.has(id))
        .map((id) => ({
            id,
            title: id.replace(/_/g, ' ').toUpperCase(),
            desc: 'Custom modular reasoning block selected by autoresearcher.',
        }));

    const allBlocks = [...KNOWN_PROMPT_BLOCKS, ...extraBlocks];

    const added = activeBlocks.filter((id) => !parentBlocks.includes(id));
    const removed = parentBlocks.filter((id) => !activeBlocks.includes(id));
    const hasDelta = parentBlocks.length > 0 && (added.length > 0 || removed.length > 0);

    return (
        <Card className="p-5 space-y-6 min-w-0">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="space-y-1">
                    <SectionHeading>Modular Reasoning & Discipline Blocks</SectionHeading>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        Structured trading disciplines dynamically toggled by the meta-researcher to
                        enforce risk control.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Badge variant="outline">
                        {activeBlocks.length} / {allBlocks.length} Blocks Active
                    </Badge>
                </div>
            </div>

            {/* Block Delta */}
            {hasDelta && (
                <div className="p-4 bg-boxel-canvas rounded-none border border-boxel-bevel-hi flex flex-col gap-3">
                    <h4 className="text-sm font-bold text-boxel-muted uppercase tracking-wider">
                        Discipline Evolution (Pivot Delta)
                    </h4>
                    <div className="flex flex-wrap gap-2">
                        {added.map((blockId) => (
                            <div
                                key={blockId}
                                className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-normal rounded-none min-w-0"
                            >
                                <span className="font-mono break-all">+ {blockId}</span>
                                <span className="text-xs font-normal opacity-85 shrink-0">
                                    (enabled)
                                </span>
                            </div>
                        ))}
                        {removed.map((blockId) => (
                            <div
                                key={blockId}
                                className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-normal rounded-none line-through min-w-0"
                            >
                                <span className="font-mono break-all">- {blockId}</span>
                                <span className="text-xs font-normal opacity-85 shrink-0">
                                    (disabled)
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Grid of Blocks */}
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,15rem),1fr))] gap-3 items-stretch">
                {allBlocks.map((block) => {
                    const isEnabled = activeBlocks.includes(block.id);
                    const wasEnabled = parentBlocks.includes(block.id);
                    const isNew = isEnabled && parentBlocks.length > 0 && !wasEnabled;

                    return (
                        <div
                            key={block.id}
                            className={`p-4 rounded-none h-full border transition-all duration-200 flex flex-col justify-between gap-2 min-w-0 overflow-hidden ${
                                isEnabled
                                    ? 'bg-boxel-trough border-boxel-bevel-hi'
                                    : 'bg-boxel-canvas/40 border-boxel-bevel-lo opacity-40'
                            } ${isNew ? 'ring-1 ring-emerald-500/30 border-emerald-500/30' : ''}`}
                        >
                            <div className="flex flex-col gap-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                    <span
                                        className={`font-mono text-sm font-bold break-words ${isEnabled ? 'text-boxel-ink' : 'text-boxel-muted line-through'}`}
                                    >
                                        {block.title}
                                    </span>
                                    {isEnabled ? (
                                        <span className="text-emerald-400 text-xs font-normal flex items-center gap-1 shrink-0">
                                            ✓{' '}
                                            {isNew && (
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
                                    {block.desc}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>
        </Card>
    );
}
