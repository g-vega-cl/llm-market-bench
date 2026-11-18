import { Badge, Button, Card, Skeleton } from '@llm-market-bench/ui-design-system';
import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import * as React from 'react';
import { fetchCauseAndEffectByEventId } from '~/features/cause-and-effect/api/fetch-cause-and-effect';
import { fetchChildResolutionEvent, fetchReferencedNewsletters } from '../api/fetch-memories';
import { memoriesQueries } from '../queries/options';
import { getMemoryCategory, type Memory } from './MemoriesList';

export interface DiscoveredAsset {
    ticker: string;
    name: string;
    reason: string;
    scenario?: string;
}

export interface DebateRecord {
    challenger_critique?: string;
    counter_thesis?: string;
    pre_mortem?: string;
    key_risks?: string[];
    adversary_model?: string;
    arbiter_model?: string;
    stress_tested?: boolean;
}

export interface HistoricalParallelRecord {
    title?: string;
    timeframe?: string;
    precedent?: string;
    market_reaction?: string;
    takeaway?: string;
    affected_assets?: string[];
}

export interface StructuredScenario {
    cleanHeader: string;
    percentage: string | null;
    outcome: string;
    tradingPlan: string | null;
    assets?: DiscoveredAsset[];
    isWinning?: boolean;
}

export function getWinningScenario(
    scenarios: StructuredScenario[],
    memory: Memory,
    activeCe?: { market_outcome: string; analysis?: string } | null,
    childResolution?: Memory | null,
): StructuredScenario | null {
    if (!scenarios || scenarios.length === 0) return null;

    // 1. Explicit metadata setting: memory.metadata.winning_scenario
    const winningMeta = memory.metadata?.winning_scenario;
    if (typeof winningMeta === 'number' && scenarios[winningMeta]) {
        return scenarios[winningMeta];
    }
    if (typeof winningMeta === 'string') {
        const found = scenarios.find(
            (s) =>
                s.cleanHeader.toLowerCase().includes(winningMeta.toLowerCase()) ||
                winningMeta.toLowerCase().includes(s.cleanHeader.toLowerCase()),
        );
        if (found) return found;
    }

    // 2. Explicit scenario flag on scenario object
    const explicitWinning = scenarios.find((s) => s.isWinning);
    if (explicitWinning) return explicitWinning;

    // 3. Fallback matching against cause & effect market outcome or child event content
    const outcomeText = [activeCe?.market_outcome, activeCe?.analysis, childResolution?.content]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

    if (outcomeText) {
        for (const s of scenarios) {
            const headerLower = s.cleanHeader.toLowerCase();
            const scenarioLabel = headerLower.match(/scenario\s+[a-z0-9]+/i);
            if (scenarioLabel && outcomeText.includes(scenarioLabel[0].toLowerCase())) {
                return s;
            }

            const cleanTitle = s.cleanHeader.replace(/^scenario\s+[a-z0-9]+[:\s-]*/i, '').trim();
            if (cleanTitle.length > 3 && outcomeText.includes(cleanTitle.toLowerCase())) {
                return s;
            }
        }
    }

    return null;
}

interface MemoryCardProps {
    memory: Memory;
}

const CATEGORY_BADGE_CONFIG: Record<
    string,
    { label: string; colorScheme: 'accent' | 'success' | 'danger' | 'info' | 'warning' | 'neutral' }
> = {
    MARKET_EVENT: { label: 'Consensus Event', colorScheme: 'accent' },
    CALENDAR_EVENT: { label: 'Calendar Event', colorScheme: 'info' },
    GOVERNMENT_INCENTIVE: { label: 'Gov Policy', colorScheme: 'success' },
    decision_reasoning: { label: 'Decision Reasoning', colorScheme: 'info' },
    POST_MORTEM: { label: 'Post-Mortem', colorScheme: 'warning' },
    ACADEMIC_PAPER: { label: 'Empirical Principle', colorScheme: 'success' },
    LESSON_LEARNED: { label: 'Lesson Learned', colorScheme: 'neutral' },
    // Legacy support keys
    consensus_event: { label: 'Consensus Event', colorScheme: 'accent' },
    calendar_event: { label: 'Calendar Event', colorScheme: 'info' },
    government_incentive: { label: 'Gov Policy', colorScheme: 'success' },
    post_mortem: { label: 'Post-Mortem', colorScheme: 'warning' },
    academic_paper: { label: 'Empirical Principle', colorScheme: 'success' },
    lesson_learned: { label: 'Lesson Learned', colorScheme: 'neutral' },
    other: { label: 'Memory', colorScheme: 'neutral' },
};

export function MemoryCard({ memory }: MemoryCardProps) {
    const [isExpanded, setIsExpanded] = React.useState(false);
    const [selectedAsset, setSelectedAsset] = React.useState<DiscoveredAsset | null>(null);

    const scenarios = React.useMemo<StructuredScenario[]>(() => {
        if (memory.metadata?.scenarios && Array.isArray(memory.metadata.scenarios)) {
            return memory.metadata.scenarios;
        }
        return [];
    }, [memory.metadata]);

    const remainingAssets = React.useMemo(() => {
        const allAssets = memory.metadata?.discovered_assets || [];
        if (scenarios.length === 0) return allAssets;

        const scenarioTickers = new Set<string>();
        for (const s of scenarios) {
            if (s.assets) {
                for (const a of s.assets) {
                    scenarioTickers.add(a.ticker.toUpperCase());
                }
            }
        }
        return allAssets.filter(
            (a: DiscoveredAsset) => !scenarioTickers.has(a.ticker.toUpperCase()),
        );
    }, [memory.metadata?.discovered_assets, scenarios]);

    const sourceIds = React.useMemo<string[]>(() => {
        if (
            memory.metadata &&
            typeof memory.metadata === 'object' &&
            !Array.isArray(memory.metadata)
        ) {
            const meta = memory.metadata as Record<string, unknown>;
            if (Array.isArray(meta.source_ids)) {
                return meta.source_ids.filter((id): id is string => typeof id === 'string');
            }
            if (typeof meta.source_id === 'string') {
                return [meta.source_id];
            }
        }
        return [];
    }, [memory.metadata]);

    const {
        data: sources,
        isLoading: isSourcesLoading,
        error: sourcesError,
    } = useQuery({
        ...memoriesQueries.sources({
            id: memory.id,
            sourceIds,
            fetchFn: fetchReferencedNewsletters,
        }),
        enabled: isExpanded && sourceIds.length > 0,
    });

    const isResolved = memory.status === 'RESOLVED';

    const { data: childResolution } = useQuery({
        ...memoriesQueries.resolutionChild({
            parentId: memory.id,
            fetchFn: () => fetchChildResolutionEvent(memory.id),
        }),
        enabled: isExpanded && isResolved,
    });

    const { data: parentCauseAndEffect } = useQuery({
        ...memoriesQueries.causeAndEffect({
            eventId: memory.id,
            fetchFn: () => fetchCauseAndEffectByEventId(memory.id),
        }),
        enabled: isExpanded,
    });

    const { data: childCauseAndEffect } = useQuery({
        ...memoriesQueries.causeAndEffect({
            eventId: childResolution?.id || '',
            fetchFn: () => fetchCauseAndEffectByEventId(childResolution?.id || ''),
        }),
        enabled: isExpanded && !!childResolution?.id,
    });

    const activeCe = childCauseAndEffect || parentCauseAndEffect;

    const winningScenario = React.useMemo(
        () => getWinningScenario(scenarios, memory, activeCe, childResolution),
        [scenarios, memory, activeCe, childResolution],
    );

    const category = getMemoryCategory(memory);
    const badgeConfig = CATEGORY_BADGE_CONFIG[category] || CATEGORY_BADGE_CONFIG.other;

    return (
        <Card
            variant="default"
            padding="md"
            id={memory.id}
            className="group w-full transition-colors rounded-none"
        >
            {/* Header */}
            <div className="flex flex-wrap items-start gap-3 mb-4">
                <div className="flex flex-wrap gap-2 items-center">
                    <Badge variant="soft" colorScheme={badgeConfig.colorScheme} size="sm">
                        {badgeConfig.label}
                    </Badge>

                    {memory.status && memory.status !== 'ACTIVE' && (
                        <Badge
                            variant={memory.status === 'RESOLVED' ? 'solid' : 'soft'}
                            colorScheme={memory.status === 'RESOLVED' ? 'neutral' : 'warning'}
                            size="sm"
                        >
                            {memory.status}
                        </Badge>
                    )}

                    {isResolved && winningScenario && (
                        <Badge variant="solid" colorScheme="success" size="sm">
                            🏆 Winning Scenario: {winningScenario.cleanHeader}
                        </Badge>
                    )}

                    {memory.parent_id && (
                        <Badge variant="soft" colorScheme="info" size="sm">
                            {memory.relationship_type || 'Related'}
                        </Badge>
                    )}

                    {memory.importance_score != null && (
                        <Badge variant="soft" colorScheme="neutral" size="sm">
                            Score: {memory.importance_score}/10
                        </Badge>
                    )}

                    {memory.similarity != null && (
                        <Badge variant="solid" colorScheme="accent" size="sm">
                            Match: {Math.round(memory.similarity * 100)}%
                        </Badge>
                    )}

                    {memory.metadata?.debate?.stress_tested && (
                        <Badge variant="soft" colorScheme="warning" size="sm">
                            🛡️ Stress-Tested
                        </Badge>
                    )}
                </div>

                <div className="ml-auto flex items-center gap-3">
                    <Link
                        to="/chat"
                        search={{
                            q: memory.metadata?.ticker
                                ? `Should I invest in ${memory.metadata.ticker} based on this memory: "${memory.content.slice(0, 120)}..."?`
                                : `Analyze this market memory thesis and recent trades: "${memory.content.slice(0, 120)}..."`,
                            ticker:
                                typeof memory.metadata?.ticker === 'string'
                                    ? memory.metadata.ticker
                                    : undefined,
                        }}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-none text-sm font-bold bg-voxel-trough hover:bg-voxel-elevated text-voxel-ink border border-voxel-bevel-hi transition-colors shadow-xs"
                        title="Discuss this memory in AI Chat Gateway"
                    >
                        <span>💬</span>
                        <span>Discuss in Chat</span>
                    </Link>

                    <span className="text-xs text-voxel-muted font-mono">
                        {memory.created_at
                            ? new Date(memory.created_at).toLocaleString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                  year: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                              })
                            : '-'}
                    </span>
                </div>
            </div>

            {/* Content */}
            <p
                className={`text-xs text-voxel-ink leading-relaxed mb-4 ${
                    memory.status === 'RESOLVED' ? 'opacity-60 line-through' : ''
                }`}
            >
                {memory.content}
            </p>

            {/* Metadata Tags */}
            {memory.metadata && Object.keys(memory.metadata).length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                    {memory.metadata.ticker && (
                        <Badge variant="soft" colorScheme="info" size="sm">
                            ${memory.metadata.ticker}
                        </Badge>
                    )}

                    {memory.metadata.impact && (
                        <Badge
                            variant="soft"
                            colorScheme={
                                memory.metadata.impact === 'BULLISH'
                                    ? 'success'
                                    : memory.metadata.impact === 'BEARISH'
                                      ? 'danger'
                                      : 'neutral'
                            }
                            size="sm"
                        >
                            {memory.metadata.impact}
                        </Badge>
                    )}

                    {memory.metadata.model_name &&
                        memory.metadata.model_name.trim().toLowerCase() !== 'unknown' && (
                            <Badge variant="soft" colorScheme="neutral" size="sm">
                                {memory.metadata.model_name}
                            </Badge>
                        )}

                    {memory.metadata.is_regret !== undefined && (
                        <Badge
                            variant="soft"
                            colorScheme={memory.metadata.is_regret ? 'warning' : 'success'}
                            size="sm"
                        >
                            {memory.metadata.is_regret ? 'Regret' : 'Success'}
                        </Badge>
                    )}
                </div>
            )}

            {(memory.metadata?.scenario_analysis ||
                scenarios.length > 0 ||
                sourceIds.length > 0 ||
                isResolved ||
                !!childResolution ||
                !!parentCauseAndEffect ||
                !!childCauseAndEffect ||
                !!memory.metadata?.debate ||
                !!memory.metadata?.historical_parallel) && (
                <div className="mt-4 pt-4 border-t border-voxel-bevel-hi">
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="flex items-center gap-2"
                    >
                        <svg
                            className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <title>SVG</title>
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 9l-7 7-7-7"
                            />
                        </svg>
                        {isExpanded ? 'Hide Analysis' : 'Show Analysis'}
                    </Button>

                    {isExpanded && (
                        <div className="mt-4 p-4 rounded-none bg-voxel-trough border border-voxel-bevel-hi">
                            {/* Resolution & Performance Analysis Section */}
                            {(isResolved || childResolution || activeCe || winningScenario) && (
                                <div className="mb-6 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-none flex flex-col gap-4">
                                    <div className="flex items-center gap-2">
                                        <span className="text-emerald-500 text-lg">⚡</span>
                                        <h4 className="text-sm font-bold text-voxel-ink uppercase tracking-wider">
                                            Resolution & Market Performance
                                        </h4>
                                    </div>

                                    {/* What Resolved Section */}
                                    <div className="flex flex-col gap-1">
                                        <span className="text-sm font-bold text-success uppercase tracking-wide">
                                            What Resolved:
                                        </span>
                                        <p className="text-xs font-normal text-voxel-ink">
                                            {memory.content.split('|')[0].trim()}
                                        </p>

                                        {childResolution && (
                                            <p className="text-xs font-normal text-voxel-muted mt-1">
                                                Resolved by:{' '}
                                                <Link
                                                    to="/memories/chain/$memoryId"
                                                    params={{ memoryId: childResolution.id }}
                                                    className="text-info hover:underline font-bold"
                                                >
                                                    {childResolution.content
                                                        .split('|')[0]
                                                        .replace('MARKET EVENT:', '')
                                                        .trim()}
                                                </Link>
                                            </p>
                                        )}
                                    </div>

                                    {/* Winning Scenario Summary Banner */}
                                    {winningScenario && (
                                        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-none flex flex-col gap-1">
                                            <div className="flex items-center gap-2">
                                                <Badge
                                                    colorScheme="success"
                                                    variant="solid"
                                                    size="xs"
                                                >
                                                    🏆 WINNING SCENARIO
                                                </Badge>
                                                <span className="text-sm font-bold text-success">
                                                    {winningScenario.cleanHeader}
                                                </span>
                                            </div>
                                            {winningScenario.outcome && (
                                                <p className="text-xs font-normal text-voxel-ink mt-1 leading-relaxed">
                                                    {winningScenario.outcome}
                                                </p>
                                            )}
                                        </div>
                                    )}

                                    {/* Why It Resolved Section */}
                                    {activeCe && (
                                        <div className="flex flex-col gap-3 pt-3 border-t border-emerald-500/10">
                                            <div>
                                                <span className="text-sm font-bold text-success uppercase tracking-wide block mb-1">
                                                    Why It Resolved (Market Outcome & Confidence:{' '}
                                                    {activeCe.confidence}%)
                                                </span>
                                                <div className="p-3 bg-voxel-surface border border-voxel-bevel-hi rounded-none text-sm text-voxel-ink font-bold leading-relaxed">
                                                    {activeCe.market_outcome}
                                                </div>
                                            </div>

                                            <div>
                                                <span className="text-sm font-bold text-voxel-muted uppercase tracking-wide block mb-1">
                                                    Causal Analysis & Learning Playbook
                                                </span>
                                                <p className="text-xs font-normal text-voxel-muted leading-relaxed whitespace-pre-wrap font-sans bg-voxel-surface p-3 rounded-none border border-voxel-bevel-hi">
                                                    {activeCe.analysis}
                                                </p>
                                            </div>

                                            {activeCe.tags && activeCe.tags.length > 0 && (
                                                <div className="flex flex-wrap gap-1.5 pt-1">
                                                    {activeCe.tags.map((tag) => (
                                                        <span
                                                            key={tag}
                                                            className="px-3 py-1 bg-zinc-800 text-zinc-400 text-sm uppercase font-bold rounded-none border border-zinc-700"
                                                        >
                                                            {tag}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Adversarial Red-Team Stress-Test Section */}
                            {memory.metadata?.debate && (
                                <div className="mb-6 p-4 bg-amber-500/5 border border-amber-500/20 rounded-none flex flex-col gap-3">
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                        <div className="flex items-center gap-2">
                                            <span className="text-amber-500 text-lg">🛡️</span>
                                            <h4 className="text-sm font-bold text-voxel-ink uppercase tracking-wider">
                                                Adversarial Red-Team Stress-Test
                                            </h4>
                                        </div>
                                        {memory.metadata.debate.adversary_model && (
                                            <Badge variant="soft" colorScheme="neutral" size="xs">
                                                Challenger: {memory.metadata.debate.adversary_model}
                                            </Badge>
                                        )}
                                    </div>

                                    {memory.metadata.debate.counter_thesis && (
                                        <div className="flex flex-col gap-1">
                                            <span className="text-sm font-bold text-accent uppercase tracking-wide">
                                                Counter-Thesis:
                                            </span>
                                            <p className="text-xs font-normal text-voxel-ink leading-relaxed">
                                                {memory.metadata.debate.counter_thesis}
                                            </p>
                                        </div>
                                    )}

                                    {memory.metadata.debate.pre_mortem && (
                                        <div className="flex flex-col gap-1 pt-2 border-t border-amber-500/10">
                                            <span className="text-sm font-bold text-danger uppercase tracking-wide">
                                                Pre-Mortem Failure Mode:
                                            </span>
                                            <p className="text-xs font-normal text-voxel-ink leading-relaxed font-mono bg-voxel-surface p-2.5 rounded-none border border-voxel-bevel-hi">
                                                {memory.metadata.debate.pre_mortem}
                                            </p>
                                        </div>
                                    )}

                                    {memory.metadata.debate.key_risks &&
                                        memory.metadata.debate.key_risks.length > 0 && (
                                            <div className="flex flex-col gap-1 pt-2 border-t border-amber-500/10">
                                                <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider block">
                                                    Key Unaddressed Risks:
                                                </span>
                                                <ul className="list-disc list-inside text-xs font-normal text-voxel-muted space-y-0.5">
                                                    {memory.metadata.debate.key_risks.map(
                                                        (risk: string, rIdx: number) => (
                                                            <li key={rIdx}>{risk}</li>
                                                        ),
                                                    )}
                                                </ul>
                                            </div>
                                        )}

                                    {!memory.metadata.debate.counter_thesis &&
                                        memory.metadata.debate.challenger_critique && (
                                            <p className="text-xs font-normal text-voxel-ink leading-relaxed whitespace-pre-wrap">
                                                {memory.metadata.debate.challenger_critique}
                                            </p>
                                        )}
                                </div>
                            )}

                            {/* Historical Precedent / Parallel Section */}
                            {memory.metadata?.historical_parallel && (
                                <div className="mb-6 p-4 bg-indigo-500/5 border border-indigo-500/20 rounded-none flex flex-col gap-3">
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="text-indigo-500 text-lg">📜</span>
                                            <h4 className="text-sm font-bold text-voxel-ink uppercase tracking-wider flex items-center gap-2 flex-wrap">
                                                <span>Historical Precedent:</span>
                                                {typeof memory.metadata.historical_parallel ===
                                                    'object' &&
                                                    memory.metadata.historical_parallel.title && (
                                                        <span className="font-bold normal-case text-info">
                                                            {
                                                                memory.metadata.historical_parallel
                                                                    .title
                                                            }
                                                        </span>
                                                    )}
                                            </h4>
                                        </div>
                                        {typeof memory.metadata.historical_parallel === 'object' &&
                                            memory.metadata.historical_parallel.timeframe && (
                                                <Badge
                                                    variant="soft"
                                                    colorScheme="neutral"
                                                    size="xs"
                                                >
                                                    {memory.metadata.historical_parallel.timeframe}
                                                </Badge>
                                            )}
                                    </div>

                                    {typeof memory.metadata.historical_parallel === 'string' ? (
                                        <p className="text-xs font-normal text-voxel-ink leading-relaxed">
                                            {memory.metadata.historical_parallel}
                                        </p>
                                    ) : (
                                        <>
                                            {memory.metadata.historical_parallel.precedent && (
                                                <div className="space-y-1">
                                                    <span className="text-sm font-bold text-voxel-muted uppercase tracking-wide">
                                                        Precedent:
                                                    </span>
                                                    <p className="text-xs font-normal text-voxel-ink leading-relaxed">
                                                        {
                                                            memory.metadata.historical_parallel
                                                                .precedent
                                                        }
                                                    </p>
                                                </div>
                                            )}

                                            {memory.metadata.historical_parallel
                                                .market_reaction && (
                                                <div className="space-y-1 pt-2 border-t border-indigo-500/10">
                                                    <span className="text-sm font-bold text-accent uppercase tracking-wide">
                                                        Market Reaction:
                                                    </span>
                                                    <p className="text-xs font-normal text-voxel-ink leading-relaxed font-mono bg-voxel-surface p-2.5 rounded-none border border-voxel-bevel-hi">
                                                        {
                                                            memory.metadata.historical_parallel
                                                                .market_reaction
                                                        }
                                                    </p>
                                                </div>
                                            )}

                                            {memory.metadata.historical_parallel.takeaway && (
                                                <div className="space-y-1 pt-2 border-t border-indigo-500/10">
                                                    <span className="text-sm font-bold text-success uppercase tracking-wide">
                                                        Key Takeaway & Playbook:
                                                    </span>
                                                    <p className="text-xs font-normal text-voxel-ink leading-relaxed">
                                                        {
                                                            memory.metadata.historical_parallel
                                                                .takeaway
                                                        }
                                                    </p>
                                                </div>
                                            )}

                                            {memory.metadata.historical_parallel.affected_assets &&
                                                memory.metadata.historical_parallel.affected_assets
                                                    .length > 0 && (
                                                    <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-indigo-500/10">
                                                        <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                                                            Assets Involved:
                                                        </span>
                                                        {memory.metadata.historical_parallel.affected_assets.map(
                                                            (asset: string, aIdx: number) => (
                                                                <Badge
                                                                    key={aIdx}
                                                                    variant="soft"
                                                                    colorScheme="info"
                                                                    size="xs"
                                                                >
                                                                    ${asset.replace('$', '')}
                                                                </Badge>
                                                            ),
                                                        )}
                                                    </div>
                                                )}

                                            <div className="pt-2 border-t border-indigo-500/10 flex justify-end">
                                                <Link
                                                    to="/chat"
                                                    search={{
                                                        q: `Analyze the historical parallel "${memory.metadata.historical_parallel.title || 'Precedent'}" (${memory.metadata.historical_parallel.timeframe || 'Past'}) for ${memory.metadata?.event_name || 'this event'}. How did ${(memory.metadata.historical_parallel.affected_assets || []).join(', ') || 'markets'} react, and does that playbook apply today?`,
                                                        ticker:
                                                            memory.metadata.historical_parallel.affected_assets?.[0]?.replace(
                                                                '$',
                                                                '',
                                                            ) ||
                                                            (typeof memory.metadata?.ticker ===
                                                            'string'
                                                                ? memory.metadata.ticker
                                                                : undefined),
                                                    }}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-none text-sm font-bold bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 transition-colors border border-indigo-800/60"
                                                    title="Interrogate this historical parallel in AI Chat"
                                                >
                                                    <span>💬</span>
                                                    <span>Interrogate Parallel in AI Chat →</span>
                                                </Link>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            {scenarios.length > 0 && (
                                <>
                                    <div className="flex items-center gap-2 mb-3">
                                        <h4 className="text-sm font-bold text-voxel-ink uppercase tracking-wide">
                                            Scenario Analysis
                                        </h4>
                                    </div>

                                    <div className="flex flex-col space-y-3 text-xs font-normal text-voxel-ink mb-4">
                                        {scenarios.map((scenario, i) => {
                                            const isWinning =
                                                winningScenario &&
                                                (scenario === winningScenario ||
                                                    scenario.cleanHeader ===
                                                        winningScenario.cleanHeader);

                                            return (
                                                <div
                                                    key={i}
                                                    className={`p-3.5 rounded-none transition-all ${
                                                        isWinning
                                                            ? 'bg-emerald-950/30 border-2 border-emerald-500/60 shadow-md ring-1 ring-emerald-500/20'
                                                            : isResolved
                                                              ? 'bg-voxel-surface/60 border border-voxel-bevel-hi opacity-60'
                                                              : 'bg-voxel-surface border border-voxel-bevel-hi'
                                                    }`}
                                                >
                                                    <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
                                                        <div className="flex items-center gap-2">
                                                            {scenario.cleanHeader && (
                                                                <span
                                                                    className={`text-sm font-bold ${
                                                                        isWinning
                                                                            ? 'text-success'
                                                                            : 'text-info'
                                                                    }`}
                                                                >
                                                                    {scenario.cleanHeader}
                                                                </span>
                                                            )}
                                                            {scenario.percentage && (
                                                                <Badge
                                                                    size="xs"
                                                                    variant={
                                                                        isWinning ? 'solid' : 'soft'
                                                                    }
                                                                    colorScheme={
                                                                        isWinning
                                                                            ? 'success'
                                                                            : 'accent'
                                                                    }
                                                                    className="tabular-nums"
                                                                >
                                                                    {scenario.percentage}
                                                                </Badge>
                                                            )}
                                                        </div>

                                                        {isWinning ? (
                                                            <Badge
                                                                colorScheme="success"
                                                                variant="solid"
                                                                size="xs"
                                                            >
                                                                🏆 WINNING SCENARIO
                                                            </Badge>
                                                        ) : isResolved ? (
                                                            <Badge
                                                                colorScheme="neutral"
                                                                variant="soft"
                                                                size="xs"
                                                            >
                                                                Did Not Occur
                                                            </Badge>
                                                        ) : null}
                                                    </div>

                                                    {scenario.outcome && (
                                                        <div className="text-xs font-normal leading-relaxed mb-2">
                                                            {scenario.outcome}
                                                        </div>
                                                    )}
                                                    {scenario.tradingPlan && (
                                                        <div className="mt-2 pt-2 border-t border-voxel-bevel-lo">
                                                            <span className="text-sm font-bold text-success block mb-1">
                                                                Trading Plan:
                                                            </span>
                                                            <p className="text-xs font-normal leading-relaxed text-voxel-muted">
                                                                {scenario.tradingPlan}
                                                            </p>
                                                        </div>
                                                    )}

                                                    {/* Actionable Assets nested directly inside the scenario card */}
                                                    {scenario.assets &&
                                                        scenario.assets.length > 0 && (
                                                            <div className="mt-3 pt-3 border-t border-voxel-bevel-lo">
                                                                <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider block mb-2">
                                                                    Actionable Assets:
                                                                </span>
                                                                <div className="flex flex-wrap gap-2">
                                                                    {scenario.assets.map(
                                                                        (asset, assetIdx) => (
                                                                            <Button
                                                                                type="button"
                                                                                key={assetIdx}
                                                                                variant="outline"
                                                                                colorScheme="info"
                                                                                size="sm"
                                                                                onClick={() =>
                                                                                    setSelectedAsset(
                                                                                        asset,
                                                                                    )
                                                                                }
                                                                                className="inline-flex items-center gap-1.5"
                                                                            >
                                                                                <span>
                                                                                    ${asset.ticker}
                                                                                </span>
                                                                                <span className="text-xs opacity-75 font-normal">
                                                                                    ({asset.name})
                                                                                </span>
                                                                            </Button>
                                                                        ),
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </>
                            )}

                            {/* Global Assets Section (only for remaining assets not listed inside scenarios) */}
                            {remainingAssets.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-voxel-bevel-hi">
                                    <div className="flex items-center gap-2 mb-3">
                                        <h5 className="text-sm font-bold text-voxel-ink uppercase tracking-wide">
                                            Other Investable Assets
                                        </h5>
                                    </div>

                                    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-2 items-stretch">
                                        {remainingAssets
                                            .slice(0, 6)
                                            .map((asset: DiscoveredAsset, idx: number) => (
                                                <Button
                                                    type="button"
                                                    key={idx}
                                                    variant="outline"
                                                    colorScheme="neutral"
                                                    onClick={() => setSelectedAsset(asset)}
                                                    className="flex flex-col items-start justify-between p-3 text-left w-full h-full"
                                                >
                                                    <div className="flex flex-col w-full mb-2">
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-sm font-bold text-voxel-ink">
                                                                ${asset.ticker}
                                                            </span>
                                                            <span className="text-xs text-voxel-muted font-normal">
                                                                {asset.name}
                                                            </span>
                                                        </div>
                                                        <span className="text-xs text-voxel-muted line-clamp-2 mt-1 font-normal">
                                                            {asset.reason}
                                                        </span>
                                                    </div>
                                                    <span className="text-sm font-bold text-info">
                                                        View details →
                                                    </span>
                                                </Button>
                                            ))}
                                    </div>
                                </div>
                            )}

                            {/* Source Citations Section */}
                            {sourceIds.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-voxel-bevel-hi">
                                    <div className="flex items-center gap-2 mb-3">
                                        <h5 className="text-sm font-bold text-voxel-ink uppercase tracking-wide">
                                            Source Citations
                                        </h5>
                                        <Badge variant="soft" colorScheme="neutral" size="sm">
                                            {sourceIds.length}{' '}
                                            {sourceIds.length === 1 ? 'source' : 'sources'}
                                        </Badge>
                                    </div>

                                    {isSourcesLoading ? (
                                        <div className="flex flex-col gap-2" aria-busy="true">
                                            <Skeleton variant="card" lines={2} />
                                        </div>
                                    ) : sourcesError ? (
                                        <div className="p-3 text-xs text-danger bg-red-950/20 rounded-none border border-red-900/30">
                                            Failed to load sources.
                                        </div>
                                    ) : sources && sources.length > 0 ? (
                                        <div className="flex flex-col gap-3">
                                            {sources.map((source, idx) => (
                                                <div
                                                    key={idx}
                                                    className="p-3 rounded-none bg-voxel-surface border border-voxel-bevel-hi"
                                                >
                                                    <div className="flex items-start justify-between gap-4 mb-2">
                                                        <div className="flex flex-col min-w-0">
                                                            <span className="text-sm font-bold text-voxel-ink truncate">
                                                                {source.sender || 'Unknown Sender'}
                                                            </span>
                                                            <span className="text-xs font-normal text-voxel-muted truncate">
                                                                {source.subject || '(No Subject)'}
                                                            </span>
                                                        </div>
                                                        <span className="text-xs font-normal text-voxel-muted font-mono flex-shrink-0 whitespace-nowrap">
                                                            {source.date
                                                                ? new Date(
                                                                      source.date,
                                                                  ).toLocaleDateString('en-US', {
                                                                      month: 'short',
                                                                      day: 'numeric',
                                                                      year: 'numeric',
                                                                      hour: '2-digit',
                                                                      minute: '2-digit',
                                                                  })
                                                                : '-'}
                                                        </span>
                                                    </div>
                                                    <div className="max-h-[150px] overflow-y-auto pr-1 text-xs font-normal text-voxel-muted leading-relaxed whitespace-pre-wrap font-sans bg-voxel-trough p-2 rounded-none border border-voxel-bevel-lo">
                                                        {source.content}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="p-3 text-xs font-normal text-voxel-muted bg-voxel-surface rounded-none border border-voxel-bevel-hi text-center">
                                            No source newsletter snapshots found.
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Parent Memory Link */}
            {memory.parent_id && (
                <div className="mt-4 pt-4 border-t border-voxel-bevel-hi">
                    <div className="flex items-start gap-2 text-voxel-muted">
                        <svg
                            className="w-4 h-4 mt-0.5 flex-shrink-0"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <title>SVG</title>
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M13 7l5 5m0 0l-5 5m5-5H6"
                            />
                        </svg>
                        <div className="flex-1 min-w-0">
                            <span className="text-sm font-bold uppercase tracking-wider block mb-1">
                                {memory.relationship_type || 'Update'}:
                            </span>
                            <Link
                                to="/memories/chain/$memoryId"
                                params={{ memoryId: memory.id }}
                                className="text-xs font-normal text-voxel-muted hover:text-voxel-ink hover:underline block"
                                title="View full event chain"
                            >
                                <span>View event chain →</span>
                            </Link>
                        </div>
                    </div>
                </div>
            )}

            {/* Asset Detail Modal */}
            {selectedAsset && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-black/50"
                    onClick={() => setSelectedAsset(null)}
                >
                    <div
                        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-voxel-surface rounded-none shadow-lg border border-voxel-bevel-hi"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-4 border-b border-voxel-bevel-hi">
                            <div className="flex items-center gap-3">
                                <div>
                                    <h3 className="text-sm font-bold text-voxel-ink">
                                        ${selectedAsset.ticker}
                                    </h3>
                                    <p className="text-xs text-voxel-muted uppercase">
                                        {selectedAsset.name}
                                    </p>
                                </div>
                            </div>
                            <Button
                                type="button"
                                variant="outline"
                                colorScheme="neutral"
                                size="sm"
                                onClick={() => setSelectedAsset(null)}
                            >
                                <svg
                                    className="w-4 h-4 text-voxel-muted"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <title>SVG</title>
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            </Button>
                        </div>

                        {/* Content */}
                        <div className="p-4 md:p-6 flex flex-col gap-3">
                            <div>
                                <h4 className="text-sm font-bold text-voxel-ink uppercase tracking-wide mb-2">
                                    Investment Thesis
                                </h4>
                                <div className="text-xs font-normal text-voxel-ink leading-relaxed whitespace-pre-wrap max-h-[50vh] overflow-y-auto pr-2">
                                    {selectedAsset.reason}
                                </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex flex-col sm:flex-row gap-3 mt-4 pt-4 border-t border-voxel-bevel-hi">
                                <Link
                                    to="/chat"
                                    search={{ ticker: selectedAsset.ticker }}
                                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-accent hover:bg-accent/90 text-voxel-trough text-sm font-bold rounded-none transition-colors shadow-sm"
                                >
                                    Ask AI Gateway (${selectedAsset.ticker}) →
                                </Link>
                                <a
                                    href={`https://finance.yahoo.com/quote/${selectedAsset.ticker}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-voxel-elevated hover:bg-voxel-trough text-voxel-ink border border-voxel-bevel-hi text-sm font-bold rounded-none transition-colors"
                                >
                                    View on Yahoo Finance
                                </a>
                                <Button
                                    type="button"
                                    variant="outline"
                                    colorScheme="neutral"
                                    size="md"
                                    onClick={() => setSelectedAsset(null)}
                                >
                                    Close
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </Card>
    );
}
