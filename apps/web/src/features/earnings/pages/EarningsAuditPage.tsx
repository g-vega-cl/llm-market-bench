import {
    Badge,
    Card,
    Input,
    PageLayout,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import type { EarningsAlphaSnapshot, SectorBellwetherSignal } from '../api/fetch-earnings-audit';

export interface EarningsAuditPageProps {
    snapshots: EarningsAlphaSnapshot[];
    bellwethers: SectorBellwetherSignal[];
}

function PeadTableRow({ item }: { item: EarningsAlphaSnapshot }) {
    const sueColorClass = useMemo(() => {
        if (item.sue_score === null) return 'text-zinc-400';
        if (item.sue_score >= 2.0) return 'text-emerald-400';
        if (item.sue_score < 0) return 'text-rose-400';
        return 'text-zinc-300';
    }, [item.sue_score]);

    const revBeatClass = useMemo(() => {
        if (item.revenue_surprise_pct === null) return 'text-zinc-400';
        return item.revenue_surprise_pct >= 0 ? 'text-emerald-400' : 'text-rose-400';
    }, [item.revenue_surprise_pct]);

    return (
        <TableRow className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell className="font-semibold text-white">{item.ticker}</TableCell>
            <TableCell className="text-zinc-300">
                <Badge variant="outline" className="text-xs border-zinc-700 text-zinc-300">
                    {item.sector}
                </Badge>
            </TableCell>
            <TableCell className="text-zinc-400 text-xs">{item.report_date || 'N/A'}</TableCell>
            <TableCell className="text-right font-mono text-zinc-200">
                {item.actual_eps !== null ? `$${item.actual_eps.toFixed(2)}` : 'N/A'}
            </TableCell>
            <TableCell className="text-right font-mono text-zinc-400">
                {item.estimated_eps !== null ? `$${item.estimated_eps.toFixed(2)}` : 'N/A'}
            </TableCell>
            <TableCell className={`text-right font-mono font-bold ${sueColorClass}`}>
                {item.sue_score !== null
                    ? item.sue_score >= 0
                        ? `+${item.sue_score.toFixed(2)}`
                        : item.sue_score.toFixed(2)
                    : 'N/A'}
            </TableCell>
            <TableCell className={`text-right font-mono text-xs ${revBeatClass}`}>
                {item.revenue_surprise_pct !== null
                    ? item.revenue_surprise_pct >= 0
                        ? `+${item.revenue_surprise_pct.toFixed(1)}%`
                        : `${item.revenue_surprise_pct.toFixed(1)}%`
                    : 'N/A'}
            </TableCell>
            <TableCell className="text-center">
                {item.is_sloan_accrual_clean ? (
                    <Badge className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs">
                        Clean Cash
                    </Badge>
                ) : (
                    <Badge className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs">
                        High Accrual
                    </Badge>
                )}
            </TableCell>
            <TableCell className="text-center">
                {item.is_top_decile_sue ? (
                    <Badge className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs">
                        Top Decile
                    </Badge>
                ) : (
                    <span className="text-xs text-zinc-500">Standard</span>
                )}
            </TableCell>
        </TableRow>
    );
}

function BellwetherTableRow({ b }: { b: SectorBellwetherSignal }) {
    return (
        <TableRow className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell className="font-semibold text-white">{b.sector}</TableCell>
            <TableCell className="font-mono text-zinc-200">{b.ticker}</TableCell>
            <TableCell className="text-zinc-300 text-xs">
                {b.classification === 'EARLY_BELLWETHER' ? (
                    <Badge className="bg-purple-500/10 text-purple-400 border border-purple-500/20 text-xs">
                        Early Bellwether
                    </Badge>
                ) : (
                    <span className="text-zinc-500">Downstream Peer</span>
                )}
            </TableCell>
            <TableCell className="text-right font-mono text-zinc-400">
                #{b.market_cap_rank || '-'}
            </TableCell>
            <TableCell className="text-zinc-400 text-xs">{b.report_date || 'Upcoming'}</TableCell>
            <TableCell className="text-center">
                {b.is_reported ? (
                    <Badge className="bg-emerald-500/10 text-emerald-400 text-xs">Reported</Badge>
                ) : (
                    <Badge className="bg-zinc-800 text-zinc-400 text-xs">Awaiting</Badge>
                )}
            </TableCell>
            <TableCell className="text-center">
                {b.is_active_bellwether_signal ? (
                    <Badge className="bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs">
                        Active Signal (14d)
                    </Badge>
                ) : (
                    <span className="text-xs text-zinc-600">-</span>
                )}
            </TableCell>
        </TableRow>
    );
}

function RevisionTableRow({ item }: { item: EarningsAlphaSnapshot }) {
    const upsideClass = useMemo(() => {
        if (item.target_consensus_upside_pct === null) return 'text-zinc-400';
        return item.target_consensus_upside_pct >= 0 ? 'text-emerald-400' : 'text-rose-400';
    }, [item.target_consensus_upside_pct]);

    return (
        <TableRow className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell className="font-semibold text-white">{item.ticker}</TableCell>
            <TableCell className="text-zinc-300 text-xs">{item.sector}</TableCell>
            <TableCell className="text-zinc-200 font-medium">
                {item.analyst_consensus || 'Unknown'}
            </TableCell>
            <TableCell className="text-right font-mono text-zinc-400">
                {item.analyst_coverage_count} analysts
            </TableCell>
            <TableCell className="text-right font-mono">
                <span
                    className={
                        item.analyst_buy_ratio_pct && item.analyst_buy_ratio_pct >= 60
                            ? 'text-emerald-400'
                            : 'text-zinc-300'
                    }
                >
                    {item.analyst_buy_ratio_pct !== null
                        ? `${item.analyst_buy_ratio_pct.toFixed(1)}%`
                        : 'N/A'}
                </span>
            </TableCell>
            <TableCell className="text-right font-mono text-zinc-300">
                {item.target_consensus_price ? `$${item.target_consensus_price.toFixed(2)}` : 'N/A'}
            </TableCell>
            <TableCell className={`text-right font-mono ${upsideClass}`}>
                {item.target_consensus_upside_pct !== null
                    ? item.target_consensus_upside_pct >= 0
                        ? `+${item.target_consensus_upside_pct.toFixed(1)}%`
                        : `${item.target_consensus_upside_pct.toFixed(1)}%`
                    : 'N/A'}
            </TableCell>
        </TableRow>
    );
}

export function EarningsAuditPage({ snapshots, bellwethers }: EarningsAuditPageProps) {
    const [activeTab, setActiveTab] = useState<'pead' | 'bellwethers' | 'revisions'>('pead');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSector, setSelectedSector] = useState<string>('ALL');

    const sectors = useMemo(() => {
        const set = new Set<string>();
        for (const s of snapshots) {
            if (s.sector) set.add(s.sector);
        }
        return ['ALL', ...Array.from(set).sort()];
    }, [snapshots]);

    const filteredSnapshots = useMemo(() => {
        return snapshots.filter((s) => {
            const matchesQuery =
                !searchQuery ||
                s.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
                s.sector.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesSector = selectedSector === 'ALL' || s.sector === selectedSector;
            return matchesQuery && matchesSector;
        });
    }, [snapshots, searchQuery, selectedSector]);

    const topDecileCount = useMemo(
        () => snapshots.filter((s) => s.is_top_decile_sue).length,
        [snapshots],
    );

    const cleanAccrualCount = useMemo(
        () => snapshots.filter((s) => s.is_sloan_accrual_clean).length,
        [snapshots],
    );

    return (
        <PageLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-white md:text-3xl">
                            Earnings Alpha & PEAD Audit
                        </h1>
                        <p className="text-sm text-zinc-400">
                            Empirical earnings surprise momentum, Standardized Unexpected Earnings
                            (SUE), Sloan accruals, and sector bellwether diffusion.
                        </p>
                    </div>
                </div>

                {/* Summary Metrics */}
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                    <Card className="p-4 bg-zinc-900/50 border-zinc-800">
                        <div className="text-xs font-medium text-zinc-400">Total Analyzed</div>
                        <div className="mt-1 text-2xl font-bold text-white">{snapshots.length}</div>
                        <div className="mt-1 text-xs text-zinc-500">S&P 500 Constituents</div>
                    </Card>
                    <Card className="p-4 bg-zinc-900/50 border-zinc-800">
                        <div className="text-xs font-medium text-zinc-400">
                            Top-Decile SUE (≥ +2.0)
                        </div>
                        <div className="mt-1 text-2xl font-bold text-emerald-400">
                            {topDecileCount}
                        </div>
                        <div className="mt-1 text-xs text-emerald-500/80">
                            Active Drift Candidates
                        </div>
                    </Card>
                    <Card className="p-4 bg-zinc-900/50 border-zinc-800">
                        <div className="text-xs font-medium text-zinc-400">Cash-Quality Clean</div>
                        <div className="mt-1 text-2xl font-bold text-cyan-400">
                            {snapshots.length > 0
                                ? `${Math.round((cleanAccrualCount / snapshots.length) * 100)}%`
                                : '0%'}
                        </div>
                        <div className="mt-1 text-xs text-cyan-500/80">Sloan Accrual Filter</div>
                    </Card>
                    <Card className="p-4 bg-zinc-900/50 border-zinc-800">
                        <div className="text-xs font-medium text-zinc-400">Active Bellwethers</div>
                        <div className="mt-1 text-2xl font-bold text-purple-400">
                            {bellwethers.filter((b) => b.is_active_bellwether_signal).length}
                        </div>
                        <div className="mt-1 text-xs text-purple-500/80">14-Day Signal Window</div>
                    </Card>
                </div>

                {/* Navigation Tabs */}
                <div className="flex items-center gap-2 border-b border-zinc-800 pb-2">
                    <button
                        type="button"
                        onClick={() => setActiveTab('pead')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                            activeTab === 'pead'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        PEAD & SUE Leaderboard
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveTab('bellwethers')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                            activeTab === 'bellwethers'
                                ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        Sector Bellwether Radar
                    </button>
                    <button
                        type="button"
                        onClick={() => setActiveTab('revisions')}
                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                            activeTab === 'revisions'
                                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                                : 'text-zinc-400 hover:text-white'
                        }`}
                    >
                        Analyst Revision Momentum
                    </button>
                </div>

                {/* Filters */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="w-full sm:w-64">
                        <Input
                            placeholder="Search ticker or sector..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-500"
                        />
                    </div>
                    <div className="flex items-center gap-2 overflow-x-auto pb-1">
                        {sectors.map((sec) => (
                            <button
                                key={sec}
                                type="button"
                                onClick={() => setSelectedSector(sec)}
                                className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap ${
                                    selectedSector === sec
                                        ? 'bg-zinc-700 text-white'
                                        : 'bg-zinc-900/50 text-zinc-400 hover:text-zinc-200 border border-zinc-800'
                                }`}
                            >
                                {sec}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tab 1: PEAD Table */}
                {activeTab === 'pead' && (
                    <Card className="overflow-hidden bg-zinc-900/40 border-zinc-800">
                        <Table>
                            <TableHeader className="bg-zinc-900/80">
                                <TableRow className="border-zinc-800 hover:bg-transparent">
                                    <TableHead className="text-zinc-400">Ticker</TableHead>
                                    <TableHead className="text-zinc-400">Sector</TableHead>
                                    <TableHead className="text-zinc-400">Report Date</TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Actual EPS
                                    </TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Est. EPS
                                    </TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        SUE Score
                                    </TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Rev Beat
                                    </TableHead>
                                    <TableHead className="text-center text-zinc-400">
                                        Sloan Quality
                                    </TableHead>
                                    <TableHead className="text-center text-zinc-400">
                                        Status
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredSnapshots.length === 0 ? (
                                    <TableRow>
                                        <TableCell
                                            colSpan={9}
                                            className="text-center text-zinc-500 py-8"
                                        >
                                            No earnings snapshots match your filters.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredSnapshots.map((item) => (
                                        <PeadTableRow key={item.ticker} item={item} />
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </Card>
                )}

                {/* Tab 2: Bellwethers */}
                {activeTab === 'bellwethers' && (
                    <Card className="overflow-hidden bg-zinc-900/40 border-zinc-800">
                        <Table>
                            <TableHeader className="bg-zinc-900/80">
                                <TableRow className="border-zinc-800 hover:bg-transparent">
                                    <TableHead className="text-zinc-400">Sector</TableHead>
                                    <TableHead className="text-zinc-400">Ticker</TableHead>
                                    <TableHead className="text-zinc-400">Role</TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Cap Rank
                                    </TableHead>
                                    <TableHead className="text-zinc-400">Report Date</TableHead>
                                    <TableHead className="text-center text-zinc-400">
                                        Status
                                    </TableHead>
                                    <TableHead className="text-center text-zinc-400">
                                        Signal
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {bellwethers.length === 0 ? (
                                    <TableRow>
                                        <TableCell
                                            colSpan={7}
                                            className="text-center text-zinc-500 py-8"
                                        >
                                            No sector bellwethers loaded yet.
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    bellwethers.map((b) => (
                                        <BellwetherTableRow key={`${b.sector}-${b.ticker}`} b={b} />
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </Card>
                )}

                {/* Tab 3: Revisions */}
                {activeTab === 'revisions' && (
                    <Card className="overflow-hidden bg-zinc-900/40 border-zinc-800">
                        <Table>
                            <TableHeader className="bg-zinc-900/80">
                                <TableRow className="border-zinc-800 hover:bg-transparent">
                                    <TableHead className="text-zinc-400">Ticker</TableHead>
                                    <TableHead className="text-zinc-400">Sector</TableHead>
                                    <TableHead className="text-zinc-400">Consensus</TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Coverage
                                    </TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Buy Ratio
                                    </TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Target Price
                                    </TableHead>
                                    <TableHead className="text-right text-zinc-400">
                                        Implied Upside
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredSnapshots.map((item) => (
                                    <RevisionTableRow key={item.ticker} item={item} />
                                ))}
                            </TableBody>
                        </Table>
                    </Card>
                )}
            </div>
        </PageLayout>
    );
}
