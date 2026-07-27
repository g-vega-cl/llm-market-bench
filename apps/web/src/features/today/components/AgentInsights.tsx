import type { Memory } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import { getAgentInfo } from '../lib/agent-info';

interface AgentInsightsProps {
    memories: (Memory & { formattedDateTime?: string; formattedShortDate?: string })[];
}

const PAGE_SIZE = 5;

export function AgentInsights({ memories }: AgentInsightsProps) {
    const [viewMode, setViewMode] = React.useState<'list' | 'cards'>('list');
    const [currentPage, setCurrentPage] = React.useState(1);

    const consensus = memories.filter((m) => m.memory_type === 'MARKET_EVENT');
    const lessons = memories.filter((m) =>
        ['LESSON_LEARNED', 'POST_MORTEM', 'ACADEMIC_PAPER'].includes(m.memory_type || ''),
    );
    const incentives = memories.filter((m) => m.memory_type === 'GOVERNMENT_INCENTIVE');

    // Flat ordered array used for pagination (consensus → incentives → lessons)
    const allItems = [
        ...consensus.map((m) => ({ ...m, _kind: 'consensus' as const })),
        ...incentives.map((m) => ({ ...m, _kind: 'incentive' as const })),
        ...lessons.map((m) => ({ ...m, _kind: 'lesson' as const })),
    ];

    const totalInsights = allItems.length;
    const totalPages = Math.ceil(totalInsights / PAGE_SIZE);
    const isPaginated = totalPages > 1;

    const paginatedItems = allItems.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

    // Reconstruct per-type arrays from the current page slice
    const pageConsensus = paginatedItems.filter((m) => m._kind === 'consensus');
    const pageIncentives = paginatedItems.filter((m) => m._kind === 'incentive');
    const pageLessons = paginatedItems.filter((m) => m._kind === 'lesson');

    function handleSetViewMode(mode: 'list' | 'cards') {
        setViewMode(mode);
        setCurrentPage(1);
    }

    if (!totalInsights) {
        return (
            <section className="space-y-8 animate-slide-up">
                <SectionHeading gradient="ai">AI Cognitive Synthesis</SectionHeading>
                <div className="flex flex-col items-center justify-center py-12 rounded-3xl border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 text-center gap-3">
                    <span className="text-3xl">🧠</span>
                    <p className="text-sm font-medium text-zinc-400 dark:text-zinc-500">
                        No insights synthesized yet today
                    </p>
                </div>
            </section>
        );
    }

    return (
        <section className="space-y-6 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="ai">AI Cognitive Synthesis</SectionHeading>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-deep-purple-50 dark:bg-deep-purple-950/20 border border-deep-purple-200 dark:border-deep-purple-900/30 rounded-xl shadow-xs">
                        <span className="text-[10px] font-black text-deep-purple-600 dark:text-deep-purple-400 uppercase tracking-widest">
                            🧠 {totalInsights} Insight{totalInsights !== 1 ? 's' : ''}
                        </span>
                    </div>

                    {/* View Toggle Switch */}
                    <div className="inline-flex items-center p-1 bg-zinc-100 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700/60 rounded-xl">
                        <button
                            type="button"
                            data-active={viewMode === 'list'}
                            onClick={() => handleSetViewMode('list')}
                            className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                                viewMode === 'list'
                                    ? 'bg-white dark:bg-zinc-900 text-deep-purple-600 dark:text-deep-purple-400 shadow-xs'
                                    : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
                            }`}
                        >
                            ≡ List
                        </button>
                        <button
                            type="button"
                            data-active={viewMode === 'cards'}
                            onClick={() => handleSetViewMode('cards')}
                            className={`px-3 py-1 text-xs font-bold rounded-lg transition-all ${
                                viewMode === 'cards'
                                    ? 'bg-white dark:bg-zinc-900 text-deep-purple-600 dark:text-deep-purple-400 shadow-xs'
                                    : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300'
                            }`}
                        >
                            ⊞ Cards
                        </button>
                    </div>
                </div>
            </div>

            {viewMode === 'list' ? (
                /* High-Density Header List View */
                <div className="space-y-3">
                    {/* Market Consensus */}
                    {pageConsensus.map((m, idx) => {
                        const agents = extractAgents(m);
                        return (
                            <Link
                                key={m.id}
                                to="/memories/chain/$memoryId"
                                params={{ memoryId: m.id }}
                                className="block group/card-link no-underline text-inherit cursor-pointer hover:no-underline"
                            >
                                <Card
                                    isHoverable
                                    padding="sm"
                                    className="relative bg-gradient-to-r from-deep-purple-50/40 via-electric-blue-50/20 to-transparent dark:from-deep-purple-950/20 dark:via-electric-blue-950/10 border-l-4 border-l-deep-purple-500 hover:shadow-deep-purple-500/10 animate-slide-up p-4"
                                    style={{ animationDelay: `${idx * 50}ms` }}
                                >
                                    <div className="flex flex-col gap-2">
                                        <div className="flex items-center justify-between gap-2 flex-wrap">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <Badge
                                                    severity="medium"
                                                    variant="soft"
                                                    radius="lg"
                                                    size="sm"
                                                >
                                                    Market Consensus
                                                </Badge>
                                                {agents.length > 0 && (
                                                    <span className="flex items-center gap-1 text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                                                        <span>•</span>
                                                        <span>Agreed:</span>
                                                        <span className="text-zinc-600 dark:text-zinc-300">
                                                            {agents.map((a) => a.name).join(', ')}
                                                        </span>
                                                    </span>
                                                )}
                                            </div>
                                            <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                                {m.formattedDateTime
                                                    ? m.formattedDateTime
                                                    : 'Pending'}
                                            </span>
                                        </div>

                                        <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 line-clamp-2 italic leading-snug">
                                            "{m.content}"
                                        </p>

                                        <div className="flex items-center justify-between pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 text-[10px]">
                                            <div className="flex items-center gap-3 flex-wrap">
                                                {m.metadata?.importance_score && (
                                                    <span className="font-bold text-zinc-400 uppercase tracking-wider">
                                                        Importance: {m.metadata.importance_score}/10
                                                    </span>
                                                )}
                                                {m.metadata?.tickers &&
                                                    m.metadata.tickers.length > 0 && (
                                                        <div className="flex gap-1.5 flex-wrap">
                                                            {m.metadata.tickers
                                                                .slice(0, 4)
                                                                .map(
                                                                    (ticker: string, i: number) => (
                                                                        <span
                                                                            key={i}
                                                                            className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-bold rounded-md uppercase border border-zinc-200 dark:border-zinc-700"
                                                                        >
                                                                            {ticker}
                                                                        </span>
                                                                    ),
                                                                )}
                                                        </div>
                                                    )}
                                            </div>
                                            <span className="text-xs font-semibold text-deep-purple-600 dark:text-deep-purple-400 flex items-center gap-1 group-hover/card-link:translate-x-0.5 transition-transform">
                                                View event chain →
                                            </span>
                                        </div>
                                    </div>
                                </Card>
                            </Link>
                        );
                    })}

                    {/* Government Incentives */}
                    {pageIncentives.map((m, idx) => (
                        <Link
                            key={m.id}
                            to="/memories/chain/$memoryId"
                            params={{ memoryId: m.id }}
                            className="block group/card-link no-underline text-inherit cursor-pointer hover:no-underline"
                        >
                            <Card
                                isHoverable
                                padding="sm"
                                className="bg-gradient-to-r from-emerald-50/40 via-cyber-yellow-50/20 to-transparent dark:from-emerald-950/20 dark:via-cyber-yellow-950/10 border-l-4 border-l-emerald-500 hover:shadow-emerald-500/10 animate-slide-up p-4"
                                style={{ animationDelay: `${(pageConsensus.length + idx) * 50}ms` }}
                            >
                                <div className="flex flex-col gap-2">
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <Badge
                                                colorScheme="success"
                                                variant="soft"
                                                radius="lg"
                                                size="sm"
                                            >
                                                Government Incentive
                                            </Badge>
                                            <span className="text-[10px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest flex items-center gap-1">
                                                <span>💰</span> Policy Alert
                                            </span>
                                        </div>
                                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                            {m.formattedShortDate
                                                ? m.formattedShortDate
                                                : 'Pending'}
                                        </span>
                                    </div>

                                    <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 line-clamp-2 leading-snug">
                                        {m.content}
                                    </p>

                                    <div className="flex items-center justify-between pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 text-[10px]">
                                        <div>
                                            {m.metadata?.budget && (
                                                <span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-bold uppercase rounded border border-emerald-200 dark:border-emerald-800">
                                                    Budget: {m.metadata.budget}
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 group-hover/card-link:translate-x-0.5 transition-transform">
                                            View event chain →
                                        </span>
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    ))}

                    {/* Lessons Learned */}
                    {pageLessons.map((m, idx) => (
                        <Link
                            key={m.id}
                            to="/memories/chain/$memoryId"
                            params={{ memoryId: m.id }}
                            className="block group/card-link no-underline text-inherit cursor-pointer hover:no-underline"
                        >
                            <Card
                                isHoverable
                                padding="sm"
                                className="bg-gradient-to-r from-amber-50/40 via-alert-red-50/20 to-transparent dark:from-amber-950/20 dark:via-alert-red-950/10 border-l-4 border-l-amber-500 hover:shadow-amber-500/10 animate-slide-up p-4"
                                style={{
                                    animationDelay: `${(pageConsensus.length + pageIncentives.length + idx) * 50}ms`,
                                }}
                            >
                                {(() => {
                                    const lessonAgent = getAgentInfo(m.metadata?.model_name);
                                    return (
                                        <div className="flex flex-col gap-2">
                                            <div className="flex items-center justify-between gap-2 flex-wrap">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <Badge
                                                        severity="high"
                                                        variant="soft"
                                                        radius="lg"
                                                        size="sm"
                                                    >
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
                                                    {m.formattedShortDate
                                                        ? m.formattedShortDate
                                                        : 'Pending'}
                                                </span>
                                            </div>

                                            <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200 line-clamp-2 italic leading-snug">
                                                "{m.content}"
                                            </p>

                                            <div className="flex items-center justify-between pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 text-[10px]">
                                                <div>
                                                    {m.metadata?.related_trade && (
                                                        <span className="font-bold text-zinc-400 uppercase tracking-wider">
                                                            Related Trade:{' '}
                                                            {m.metadata.related_trade}
                                                        </span>
                                                    )}
                                                </div>
                                                <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1 group-hover/card-link:translate-x-0.5 transition-transform">
                                                    View event chain →
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })()}
                            </Card>
                        </Link>
                    ))}
                </div>
            ) : (
                /* Compact Cards Grid View (like Daily Intelligence Briefing) */
                <div className="grid grid-cols-1 gap-4">
                    {/* Market Consensus */}
                    {pageConsensus.map((m, idx) => {
                        const agents = extractAgents(m);
                        return (
                            <Link
                                key={m.id}
                                to="/memories/chain/$memoryId"
                                params={{ memoryId: m.id }}
                                className="block group/card-link no-underline text-inherit cursor-pointer hover:no-underline"
                            >
                                <Card
                                    isHoverable
                                    padding="md"
                                    className="relative bg-gradient-to-br from-deep-purple-50/50 via-electric-blue-50/30 to-transparent dark:from-deep-purple-950/20 dark:via-electric-blue-950/10 border-l-4 border-l-deep-purple-500 hover:shadow-deep-purple-500/10 animate-slide-up p-5"
                                    style={{ animationDelay: `${idx * 80}ms` }}
                                >
                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <Badge
                                                severity="medium"
                                                variant="soft"
                                                radius="lg"
                                                size="sm"
                                            >
                                                Market Consensus
                                            </Badge>
                                            {agents.length > 0 && (
                                                <span className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                                                    <span>•</span>
                                                    <span>Agreed:</span>
                                                    <span className="text-zinc-600 dark:text-zinc-300">
                                                        {agents.map((a) => a.name).join(', ')}
                                                    </span>
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                            {m.formattedDateTime ? m.formattedDateTime : 'Pending'}
                                        </span>
                                    </div>

                                    <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic border-l-4 border-deep-purple-300 dark:border-deep-purple-700 pl-3 line-clamp-3">
                                        "{m.content}"
                                    </p>

                                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800 flex-wrap gap-2">
                                        <div className="flex items-center gap-4 flex-wrap">
                                            {m.metadata?.importance_score && (
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2 h-2 bg-deep-purple-500 rounded-full shadow-lg" />
                                                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                                        Importance: {m.metadata.importance_score}/10
                                                    </span>
                                                </div>
                                            )}
                                            {m.metadata?.tickers &&
                                                m.metadata.tickers.length > 0 && (
                                                    <div className="flex gap-2 flex-wrap">
                                                        {m.metadata.tickers
                                                            .slice(0, 5)
                                                            .map((ticker: string, i: number) => (
                                                                <span
                                                                    key={i}
                                                                    className="px-2.5 py-1 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-[9px] font-bold rounded-md uppercase tracking-wide border border-zinc-200 dark:border-zinc-700"
                                                                >
                                                                    {ticker}
                                                                </span>
                                                            ))}
                                                    </div>
                                                )}
                                        </div>
                                        <span className="text-xs font-semibold text-deep-purple-600 dark:text-deep-purple-400 flex items-center gap-1 group-hover/card-link:translate-x-0.5 transition-transform">
                                            View event chain →
                                        </span>
                                    </div>
                                </Card>
                            </Link>
                        );
                    })}

                    {/* Government Incentives */}
                    {pageIncentives.map((m, idx) => (
                        <Link
                            key={m.id}
                            to="/memories/chain/$memoryId"
                            params={{ memoryId: m.id }}
                            className="block group/card-link no-underline text-inherit cursor-pointer hover:no-underline"
                        >
                            <Card
                                isHoverable
                                padding="md"
                                className="bg-gradient-to-br from-emerald-50/50 via-cyber-yellow-50/20 to-transparent dark:from-emerald-950/20 dark:via-cyber-yellow-950/10 border-l-4 border-l-emerald-500 hover:shadow-emerald-500/10 animate-slide-up p-5"
                                style={{ animationDelay: `${(pageConsensus.length + idx) * 80}ms` }}
                            >
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <Badge
                                            colorScheme="success"
                                            variant="soft"
                                            radius="lg"
                                            size="sm"
                                        >
                                            Government Incentive
                                        </Badge>
                                        <span className="text-[10px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest flex items-center gap-1">
                                            <span>💰</span> Policy Alert
                                        </span>
                                    </div>
                                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                        {m.formattedShortDate ? m.formattedShortDate : 'Pending'}
                                    </span>
                                </div>
                                <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed line-clamp-3">
                                    {m.content}
                                </p>

                                <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800 flex-wrap gap-2">
                                    <div>
                                        {m.metadata?.budget && (
                                            <span className="px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 text-[10px] font-black uppercase tracking-wider rounded-lg border border-emerald-200 dark:border-emerald-800">
                                                Budget: {m.metadata.budget}
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1 group-hover/card-link:translate-x-0.5 transition-transform">
                                        View event chain →
                                    </span>
                                </div>
                            </Card>
                        </Link>
                    ))}

                    {/* Lessons Learned */}
                    {pageLessons.map((m, idx) => (
                        <Link
                            key={m.id}
                            to="/memories/chain/$memoryId"
                            params={{ memoryId: m.id }}
                            className="block group/card-link no-underline text-inherit cursor-pointer hover:no-underline"
                        >
                            <Card
                                isHoverable
                                padding="md"
                                className="bg-gradient-to-br from-amber-50/50 via-alert-red-50/20 to-transparent dark:from-amber-950/20 dark:via-alert-red-950/10 border-l-4 border-l-amber-500 hover:shadow-amber-500/10 animate-slide-up p-5"
                                style={{
                                    animationDelay: `${(pageConsensus.length + pageIncentives.length + idx) * 80}ms`,
                                }}
                            >
                                {(() => {
                                    const lessonAgent = getAgentInfo(m.metadata?.model_name);
                                    return (
                                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <Badge
                                                    severity="high"
                                                    variant="soft"
                                                    radius="lg"
                                                    size="sm"
                                                >
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
                                                {m.formattedShortDate
                                                    ? m.formattedShortDate
                                                    : 'Pending'}
                                            </span>
                                        </div>
                                    );
                                })()}
                                <p className="text-base text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed italic bg-amber-50/50 dark:bg-amber-950/10 p-3 rounded-xl border border-amber-100 dark:border-amber-900/30 line-clamp-3">
                                    "{m.content}"
                                </p>

                                <div className="flex items-center justify-between mt-3 pt-3 border-t border-zinc-200 dark:border-zinc-800 flex-wrap gap-2">
                                    <div>
                                        {m.metadata?.related_trade && (
                                            <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest">
                                                Related Trade: {m.metadata.related_trade}
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1 group-hover/card-link:translate-x-0.5 transition-transform">
                                        View event chain →
                                    </span>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}

            {/* Pagination controls */}
            {isPaginated && (
                <div className="flex items-center justify-between pt-2 mt-1">
                    {currentPage > 1 ? (
                        <button
                            type="button"
                            onClick={() => setCurrentPage((p) => p - 1)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-deep-purple-600 dark:text-deep-purple-400 bg-deep-purple-50 dark:bg-deep-purple-950/20 border border-deep-purple-200 dark:border-deep-purple-900/30 rounded-xl hover:bg-deep-purple-100 dark:hover:bg-deep-purple-950/40 transition-colors"
                        >
                            ← Prev
                        </button>
                    ) : (
                        <span />
                    )}

                    <span className="text-[11px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                        Page {currentPage} of {totalPages}
                    </span>

                    {currentPage < totalPages ? (
                        <button
                            type="button"
                            onClick={() => setCurrentPage((p) => p + 1)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-deep-purple-600 dark:text-deep-purple-400 bg-deep-purple-50 dark:bg-deep-purple-950/20 border border-deep-purple-200 dark:border-deep-purple-900/30 rounded-xl hover:bg-deep-purple-100 dark:hover:bg-deep-purple-950/40 transition-colors"
                        >
                            Next →
                        </button>
                    ) : (
                        <span />
                    )}
                </div>
            )}
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
