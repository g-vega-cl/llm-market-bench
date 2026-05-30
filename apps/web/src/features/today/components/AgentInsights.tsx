import type { Memory } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { formatEasternDateTime, formatEasternShortDate } from '~/utils/date';
import { getAgentInfo } from '../lib/agent-info';

interface AgentInsightsProps {
    memories: Memory[];
}

export function AgentInsights({ memories }: AgentInsightsProps) {
    const consensus = memories.filter((m) => m.memory_type === 'MARKET_EVENT');
    const lessons = memories.filter((m) =>
        ['LESSON_LEARNED', 'POST_MORTEM', 'ACADEMIC_PAPER'].includes(m.memory_type || ''),
    );
    const incentives = memories.filter((m) => m.memory_type === 'GOVERNMENT_INCENTIVE');

    if (!consensus.length && !lessons.length && !incentives.length) return null;

    // Calculate consensus strength
    const consensusStrength =
        consensus.length > 0 ? Math.min(100, (consensus.length / 3) * 100) : 0;

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="ai">AI Cognitive Synthesis</SectionHeading>

                {/* Consensus Meter */}
                {consensus.length > 0 && (
                    <div className="flex items-center gap-4 px-6 py-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-md">
                        <span className="text-xs font-black text-zinc-400 uppercase tracking-widest">
                            Consensus
                        </span>
                        <div className="flex items-center gap-2">
                            <div className="w-32 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden shadow-inner">
                                <div
                                    className="h-full gradient-ai transition-all duration-1000 shadow-lg"
                                    style={{ width: `${consensusStrength}%` }}
                                />
                            </div>
                            <span className="text-sm font-black text-deep-purple-500 tabular-nums">
                                {Math.round(consensusStrength)}%
                            </span>
                        </div>
                    </div>
                )}
            </div>

            <div className="space-y-6">
                {/* Market Consensus - Priority Display */}
                {consensus.map((m, idx) => {
                    const agents = extractAgents(m);
                    return (
                        <Card
                            key={m.id}
                            isHoverable
                            padding="lg"
                            className="relative bg-gradient-to-br from-deep-purple-50/50 via-electric-blue-50/30 to-transparent dark:from-deep-purple-950/20 dark:via-electric-blue-950/10 border-l-4 border-l-deep-purple-500 hover:shadow-deep-purple-500/10 animate-slide-up sm:p-8"
                            style={{ animationDelay: `${idx * 100}ms` }}
                        >
                            {/* Glow Effect on Hover */}
                            <div className="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-deep-purple-500/0 via-transparent to-electric-blue-500/0 group-hover:from-deep-purple-500/5 group-hover:to-electric-blue-500/5 transition-all duration-500 pointer-events-none" />

                            {/* Agent Participation */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 relative">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <Badge severity="medium" variant="soft" radius="lg" size="sm">
                                        Market Consensus
                                    </Badge>
                                    {agents.length > 0 && (
                                        <div className="flex items-center gap-1 flex-wrap">
                                            {agents.slice(0, 4).map((agent, i) => (
                                                <div
                                                    key={i}
                                                    className={`w-7 h-7 rounded-full ${agent.bgColor} flex items-center justify-center text-xs border-2 border-white dark:border-zinc-900 shadow-md hover:scale-110 transition-transform cursor-help`}
                                                    title={agent.name}
                                                >
                                                    {agent.emoji}
                                                </div>
                                            ))}
                                            {agents.length > 4 && (
                                                <div className="w-7 h-7 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-[9px] font-bold text-zinc-600 dark:text-zinc-300 border-2 border-white dark:border-zinc-900 shadow-md">
                                                    +{agents.length - 4}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                    {m.created_at ? formatEasternDateTime(m.created_at) : 'Pending'}
                                </span>
                            </div>

                            {/* Content */}
                            <p className="text-lg text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic border-l-4 border-deep-purple-300 dark:border-deep-purple-700 pl-4 relative">
                                <span className="absolute -top-3 -left-2 text-4xl text-deep-purple-200 dark:text-deep-purple-800">
                                    "
                                </span>
                                {m.content}
                                <span className="absolute -bottom-6 -right-2 text-4xl text-deep-purple-200 dark:text-deep-purple-800">
                                    "
                                </span>
                            </p>

                            {/* Metadata */}
                            {m.metadata?.importance_score && (
                                <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-deep-purple-500 rounded-full shadow-lg" />
                                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                            Importance: {m.metadata.importance_score}/10
                                        </span>
                                    </div>
                                    {m.metadata?.tickers && m.metadata.tickers.length > 0 && (
                                        <div className="flex gap-2 flex-wrap">
                                            {m.metadata.tickers
                                                .slice(0, 5)
                                                .map((ticker: string, i: number) => (
                                                    <span
                                                        key={i}
                                                        className="px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-[9px] font-bold rounded-md uppercase tracking-wide border border-zinc-200 dark:border-zinc-700 hover:border-deep-purple-400 transition-colors"
                                                    >
                                                        {ticker}
                                                    </span>
                                                ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </Card>
                    );
                })}

                {/* Government Incentives */}
                {incentives.map((m, idx) => (
                    <Card
                        key={m.id}
                        isHoverable
                        padding="lg"
                        className="bg-gradient-to-br from-emerald-50/50 via-cyber-yellow-50/20 to-transparent dark:from-emerald-950/20 dark:via-cyber-yellow-950/10 border-l-4 border-l-emerald-500 hover:shadow-emerald-500/10 animate-slide-up sm:p-8"
                        style={{ animationDelay: `${(consensus.length + idx) * 100}ms` }}
                    >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                            <div className="flex items-center gap-2 flex-wrap">
                                <Badge colorScheme="success" variant="soft" radius="lg" size="sm">
                                    Government Incentive
                                </Badge>
                                <span className="text-[10px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest flex items-center gap-1">
                                    <span>💰</span> Policy Alert
                                </span>
                            </div>
                            <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                {m.created_at ? formatEasternShortDate(m.created_at) : 'Pending'}
                            </span>
                        </div>
                        <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">
                            {m.content}
                        </p>
                        {m.metadata?.budget && (
                            <div className="mt-4 flex items-center gap-2">
                                <span className="px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-black uppercase tracking-wider rounded-lg border border-emerald-200 dark:border-emerald-800">
                                    Budget: {m.metadata.budget}
                                </span>
                            </div>
                        )}
                    </Card>
                ))}

                {/* Lessons Learned */}
                {lessons.map((m, idx) => (
                    <Card
                        key={m.id}
                        isHoverable
                        padding="lg"
                        className="bg-gradient-to-br from-amber-50/50 via-alert-red-50/20 to-transparent dark:from-amber-950/20 dark:via-alert-red-950/10 border-l-4 border-l-amber-500 hover:shadow-amber-500/10 animate-slide-up sm:p-8"
                        style={{
                            animationDelay: `${(consensus.length + incentives.length + idx) * 100}ms`,
                        }}
                    >
                        {(() => {
                            const lessonAgent = getAgentInfo(m.metadata?.model_name);
                            return (
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <Badge severity="high" variant="soft" radius="lg" size="sm">
                                            Lesson Learned
                                        </Badge>
                                        <span className="text-[10px] font-black text-amber-600 dark:text-amber-400 uppercase tracking-widest flex items-center gap-1">
                                            <span>📝</span> Post-Analysis
                                        </span>
                                        {lessonAgent.name !== 'Unknown' && (
                                            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                                                {lessonAgent.name}
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                        {m.created_at
                                            ? formatEasternShortDate(m.created_at)
                                            : 'Pending'}
                                    </span>
                                </div>
                            );
                        })()}
                        <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic bg-amber-50/50 dark:bg-amber-950/10 p-4 rounded-xl border border-amber-100 dark:border-amber-900/30">
                            "{m.content}"
                        </p>
                        {m.metadata?.related_trade && (
                            <div className="mt-4 flex items-center gap-2">
                                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                    Related Trade: {m.metadata.related_trade}
                                </span>
                            </div>
                        )}
                    </Card>
                ))}
            </div>
        </section>
    );
}

// Helper to extract agent information from memory
function extractAgents(memory: Memory) {
    const agents = [];

    // Try to extract from metadata
    if (
        memory.metadata?.participating_agents &&
        Array.isArray(memory.metadata.participating_agents)
    ) {
        for (const agentId of memory.metadata.participating_agents) {
            const info = getAgentInfo(agentId);
            agents.push(info);
        }
    }

    // Try to extract from content or model_name if available
    const modelName = memory.metadata?.model_name;
    if (modelName) {
        const info = getAgentInfo(modelName);
        if (!agents.find((a) => a.name === info.name)) {
            agents.push(info);
        }
    }

    return agents;
}
