import * as React from 'react'

interface AgentInsightsProps {
    memories: any[]
}

const agentConfig: Record<string, { name: string; color: string; bgColor: string; emoji: string }> = {
    'gpt-5.4-nano': { name: 'OpenAI', color: 'text-emerald-500', bgColor: 'bg-emerald-500', emoji: '🟢' },
    'claude-haiku-4-5': { name: 'Claude', color: 'text-amber-600', bgColor: 'bg-amber-600', emoji: '🟠' },
    'gemini-3.1-flash-lite-preview': { name: 'Gemini', color: 'text-blue-500', bgColor: 'bg-blue-500', emoji: '🔵' },
    'deepseek-reasoner': { name: 'DeepSeek', color: 'text-purple-500', bgColor: 'bg-purple-500', emoji: '🟣' },
    'contrarian_agent': { name: 'Contrarian', color: 'text-rose-500', bgColor: 'bg-rose-500', emoji: '🔴' },
}

function getAgentInfo(ownerId: string) {
    const normalized = ownerId?.toLowerCase().replace(/_/g, '-').replace(/-/g, '-')
    for (const [key, config] of Object.entries(agentConfig)) {
        if (normalized?.includes(key.replace(/-/g, '')) || key.includes(normalized?.replace(/-/g, ''))) {
            return config
        }
    }
    return { name: ownerId || 'Unknown', color: 'text-zinc-500', bgColor: 'bg-zinc-500', emoji: '⚪' }
}

export function AgentInsights({ memories }: AgentInsightsProps) {
    const consensus = memories.filter(m => m.memory_type === 'MARKET_EVENT')
    const lessons = memories.filter(m => m.memory_type === 'LESSON_LEARNED')
    const incentives = memories.filter(m => m.memory_type === 'GOVERNMENT_INCENTIVE')

    if (!consensus.length && !lessons.length && !incentives.length) return null

    // Calculate consensus strength
    const consensusStrength = consensus.length > 0
        ? Math.min(100, (consensus.length / 3) * 100)
        : 0

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex items-center justify-between">
                <h2 className="text-3xl font-black text-zinc-900 dark:text-white flex items-center gap-4 text-display">
                    <span className="w-3 h-10 bg-gradient-to-b from-deep-purple-500 to-electric-blue-500 rounded-full" />
                    <span className="text-gradient text-gradient-electric">AI Cognitive Synthesis</span>
                </h2>

                {/* Consensus Meter */}
                {consensus.length > 0 && (
                    <div className="flex items-center gap-4 px-6 py-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                        <span className="text-xs font-black text-zinc-400 uppercase tracking-widest">Consensus</span>
                        <div className="flex items-center gap-2">
                            <div className="w-32 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full gradient-ai transition-all duration-1000"
                                    style={{ width: `${consensusStrength}%` }}
                                />
                            </div>
                            <span className="text-sm font-black text-deep-purple-500">{Math.round(consensusStrength)}%</span>
                        </div>
                    </div>
                )}
            </div>

            <div className="space-y-6">
                {/* Market Consensus - Priority Display */}
                {consensus.map((m, idx) => {
                    const agents = extractAgents(m)
                    return (
                        <div
                            key={m.id}
                            className="group relative p-8 border border-zinc-200 dark:border-zinc-800 rounded-[2rem] bg-gradient-to-br from-deep-purple-50/50 via-electric-blue-50/30 to-transparent dark:from-deep-purple-950/20 dark:via-electric-blue-950/10 border-l-4 border-l-deep-purple-500 shadow-sm hover:shadow-lg transition-all duration-300 card-lift animate-slide-up"
                            style={{ animationDelay: `${idx * 100}ms` }}
                        >
                            {/* Agent Participation */}
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <span className="px-3 py-1 bg-deep-purple-100 dark:bg-deep-purple-900/30 text-deep-purple-600 dark:text-deep-purple-400 text-[9px] font-black uppercase tracking-widest rounded-lg border border-deep-purple-200 dark:border-deep-purple-800">
                                        Market Consensus
                                    </span>
                                    {agents.length > 0 && (
                                        <div className="flex items-center gap-1">
                                            {agents.slice(0, 4).map((agent, i) => (
                                                <div
                                                    key={i}
                                                    className={`w-6 h-6 rounded-full ${agent.bgColor} flex items-center justify-center text-xs border-2 border-white dark:border-zinc-900`}
                                                    title={agent.name}
                                                >
                                                    {agent.emoji}
                                                </div>
                                            ))}
                                            {agents.length > 4 && (
                                                <div className="w-6 h-6 rounded-full bg-zinc-200 dark:bg-zinc-700 flex items-center justify-center text-[9px] font-bold text-zinc-600 dark:text-zinc-300 border-2 border-white dark:border-zinc-900">
                                                    +{agents.length - 4}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                    {new Date(m.created_at).toLocaleDateString('en-US', {
                                        month: 'short',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit'
                                    })}
                                </span>
                            </div>

                            {/* Content */}
                            <p className="text-lg text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic border-l-4 border-deep-purple-300 dark:border-deep-purple-700 pl-4">
                                "{m.content}"
                            </p>

                            {/* Metadata */}
                            {m.metadata?.importance_score && (
                                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-800">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 bg-deep-purple-500 rounded-full" />
                                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                            Importance: {m.metadata.importance_score}/10
                                        </span>
                                    </div>
                                    {m.metadata?.tickers && (
                                        <div className="flex gap-2">
                                            {m.metadata.tickers.slice(0, 5).map((ticker: string, i: number) => (
                                                <span
                                                    key={i}
                                                    className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-[9px] font-bold rounded uppercase"
                                                >
                                                    {ticker}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )
                })}

                {/* Government Incentives */}
                {incentives.map((m, idx) => (
                    <div
                        key={m.id}
                        className="group p-8 border border-zinc-200 dark:border-zinc-800 rounded-[2rem] bg-gradient-to-br from-emerald-50/50 via-cyber-yellow-50/20 to-transparent dark:from-emerald-950/20 dark:via-cyber-yellow-950/10 border-l-4 border-l-emerald-500 shadow-sm hover:shadow-lg transition-all duration-300 card-lift animate-slide-up"
                        style={{ animationDelay: `${(consensus.length + idx) * 100}ms` }}
                    >
                        <div className="flex items-center justify-between mb-4">
                            <span className="px-3 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 text-[9px] font-black uppercase tracking-widest rounded-lg border border-emerald-200 dark:border-emerald-800">
                                Government Incentive
                            </span>
                            <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                {new Date(m.created_at).toLocaleDateString('en-US', {
                                    month: 'short',
                                    day: 'numeric'
                                })}
                            </span>
                        </div>

                        <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">
                            {m.content}
                        </p>

                        {m.metadata?.budget && (
                            <div className="mt-4 flex items-center gap-2">
                                <span className="text-[10px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest">
                                    Budget: {m.metadata.budget}
                                </span>
                            </div>
                        )}
                    </div>
                ))}

                {/* Lessons Learned */}
                {lessons.map((m, idx) => (
                    <div
                        key={m.id}
                        className="group p-8 border border-zinc-200 dark:border-zinc-800 rounded-[2rem] bg-gradient-to-br from-amber-50/50 via-alert-red-50/20 to-transparent dark:from-amber-950/20 dark:via-alert-red-950/10 border-l-4 border-l-amber-500 shadow-sm hover:shadow-lg transition-all duration-300 card-lift animate-slide-up"
                        style={{ animationDelay: `${(consensus.length + incentives.length + idx) * 100}ms` }}
                    >
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <span className="px-3 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 text-[9px] font-black uppercase tracking-widest rounded-lg border border-amber-200 dark:border-amber-800">
                                    Lesson Learned
                                </span>
                                <span className="text-[10px] font-black text-amber-600 dark:text-amber-400 uppercase tracking-widest flex items-center gap-1">
                                    <span>📝</span> Post-Analysis
                                </span>
                            </div>
                            <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                {new Date(m.created_at).toLocaleDateString('en-US', {
                                    month: 'short',
                                    day: 'numeric'
                                })}
                            </span>
                        </div>

                        <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic">
                            "{m.content}"
                        </p>

                        {m.metadata?.related_trade && (
                            <div className="mt-4 flex items-center gap-2">
                                <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                    Related: {m.metadata.related_trade}
                                </span>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </section>
    )
}

// Helper to extract agent information from memory
function extractAgents(memory: any) {
    const agents = []

    // Try to extract from metadata
    if (memory.metadata?.participating_agents) {
        for (const agentId of memory.metadata.participating_agents) {
            const info = getAgentInfo(agentId)
            agents.push(info)
        }
    }

    // Try to extract from content or model_name if available
    if (memory.model_name) {
        const info = getAgentInfo(memory.model_name)
        if (!agents.find(a => a.name === info.name)) {
            agents.push(info)
        }
    }

    return agents
}
