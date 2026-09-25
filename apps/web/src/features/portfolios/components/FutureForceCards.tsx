import type { PositionWithReasoning } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import type { FutureForce } from '../api/fetch-portfolios';

interface FutureForceCardsProps {
    forces: FutureForce[];
    positions: PositionWithReasoning[];
}

function getArchetypeDetails(archetype: string): {
    emoji: string;
    label: string;
    colorScheme: 'accent' | 'info' | 'warning' | 'danger' | 'success';
} {
    switch (archetype.toLowerCase()) {
        case 'geopolitical_chokepoint':
            return { emoji: '🌍', label: 'Geopolitical Chokepoint', colorScheme: 'danger' };
        case 'government_agenda':
            return { emoji: '⚔️', label: 'Government Agenda', colorScheme: 'warning' };
        case 'sleeping_giant':
            return { emoji: '⚡', label: 'Sleeping Giant', colorScheme: 'accent' };
        case 'distribution_turnon':
            return { emoji: '📲', label: 'Distribution Turn-On', colorScheme: 'info' };
        case 'secular_tollroad':
            return { emoji: '🛡️', label: 'AI Threat Toll Road', colorScheme: 'accent' };
        case 'tam_explosion':
            return { emoji: '🚀', label: 'TAM Explosion', colorScheme: 'success' };
        case 'mega_event':
            return { emoji: '⚽', label: 'Fixed Mega-Event', colorScheme: 'info' };
        default:
            return { emoji: '🔮', label: 'Forward Catalyst', colorScheme: 'accent' };
    }
}

export function FutureForceCards({ forces, positions }: FutureForceCardsProps) {
    if (!forces || forces.length === 0) return null;

    // Total invested cash in the portfolio
    const totalInvestedCash = positions.reduce(
        (sum, pos) => sum + (pos.quantity ?? 0) * (pos.average_cost_basis ?? 0),
        0,
    );

    return (
        <section className="space-y-4">
            <div className="flex items-center justify-between">
                <SectionHeading gradient="electric">Active Multi-Horizon Forces</SectionHeading>
                <Badge variant="soft" size="sm" colorScheme="accent">
                    2 to 24 Months Horizon
                </Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {forces.map((force) => {
                    const { emoji, label, colorScheme } = getArchetypeDetails(force.archetype);
                    const forceTickers = new Set(
                        (Array.isArray(force.tickers) ? force.tickers : []).map((t) =>
                            String(t).toUpperCase(),
                        ),
                    );

                    // Compute force aggregate stats
                    const forcePositions = positions.filter(
                        (p) => p.ticker && forceTickers.has(p.ticker.toUpperCase()),
                    );

                    const forceInvested = forcePositions.reduce(
                        (sum, p) => sum + (p.quantity ?? 0) * (p.average_cost_basis ?? 0),
                        0,
                    );
                    const forcePnlUsd = forcePositions.reduce(
                        (sum, p) => sum + (p.unrealized_pnl_usd ?? 0),
                        0,
                    );
                    const forceWeightPct =
                        totalInvestedCash > 0 ? (forceInvested / totalInvestedCash) * 100 : 0;
                    const forcePnlPct = forceInvested > 0 ? (forcePnlUsd / forceInvested) * 100 : 0;

                    const isPendingLiquidation = force.status === 'pending_liquidation';

                    return (
                        <Card
                            key={force.force_title}
                            variant="outlined"
                            padding="md"
                            className="bg-zinc-900/40 border-zinc-800 flex flex-col justify-between hover:border-zinc-700 transition-colors"
                        >
                            <div className="space-y-3">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                            <Badge
                                                variant="soft"
                                                size="sm"
                                                colorScheme={colorScheme}
                                            >
                                                {emoji} {label}
                                            </Badge>
                                            <Badge variant="outline" size="sm">
                                                {force.horizon_months}m Horizon
                                            </Badge>
                                            {isPendingLiquidation && (
                                                <Badge
                                                    variant="solid"
                                                    size="sm"
                                                    colorScheme="danger"
                                                >
                                                    Pending Market Open
                                                </Badge>
                                            )}
                                        </div>
                                        <h4 className="text-base font-semibold text-zinc-100 mt-1">
                                            {force.force_title}
                                        </h4>
                                    </div>
                                    <Badge variant="soft" size="sm" colorScheme="accent">
                                        Conviction {force.conviction_score}/5
                                    </Badge>
                                </div>

                                <p className="text-xs text-zinc-400 line-clamp-3 leading-relaxed">
                                    {force.thesis}
                                </p>

                                <div className="text-xs text-zinc-500 bg-zinc-950/50 p-2.5 rounded border border-zinc-800/60 space-y-1.5">
                                    <div>
                                        <span className="font-semibold text-zinc-400">
                                            Milestone:{' '}
                                        </span>
                                        {force.catalyst_event}
                                    </div>
                                    <div>
                                        <span className="font-semibold text-rose-400">
                                            Invalidation Trigger:{' '}
                                        </span>
                                        <span className="text-zinc-400">
                                            {force.invalidation_triggers}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="mt-4 pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="text-zinc-500">Tickers:</span>
                                    {Array.isArray(force.tickers) &&
                                        force.tickers.map((t) => (
                                            <span
                                                key={t}
                                                className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-200 font-mono font-medium"
                                            >
                                                {t}
                                            </span>
                                        ))}
                                </div>

                                {forcePositions.length > 0 && (
                                    <div className="flex items-center gap-3">
                                        <span className="text-zinc-400">
                                            Weight:{' '}
                                            <strong className="text-zinc-200">
                                                {forceWeightPct.toFixed(1)}%
                                            </strong>
                                        </span>
                                        <span
                                            className={`font-semibold ${
                                                forcePnlPct >= 0
                                                    ? 'text-emerald-400'
                                                    : 'text-rose-400'
                                            }`}
                                        >
                                            {forcePnlPct >= 0 ? '+' : ''}
                                            {forcePnlPct.toFixed(1)}%
                                        </span>
                                    </div>
                                )}
                            </div>
                        </Card>
                    );
                })}
            </div>
        </section>
    );
}
