import {
    Badge,
    Button,
    Card,
    Input,
    PageLayout,
    Table,
    TableBody,
    TableCell,
    type TableCellTone,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import { signToneOrMuted } from '~/lib/sign-tone';
import type { EarningsAlphaSnapshot, SectorBellwetherSignal } from '../api/fetch-earnings-audit';
import type { EarningsPrediction } from '../api/fetch-earnings-predictions';
import { EarningsArenaTab } from '../components/EarningsArenaTab';

export interface EarningsAuditPageProps {
    snapshots: EarningsAlphaSnapshot[];
    bellwethers: SectorBellwetherSignal[];
    predictions?: EarningsPrediction[];
}

function PeadTableRow({ item }: { item: EarningsAlphaSnapshot }) {
    const sueTone: TableCellTone | undefined = useMemo(() => {
        if (item.sue_score === null) return 'muted';
        if (item.sue_score >= 2.0) return 'positive';
        if (item.sue_score < 0) return 'negative';
        return undefined;
    }, [item.sue_score]);

    return (
        <TableRow className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell>{item.ticker}</TableCell>
            <TableCell>
                <Badge variant="soft" colorScheme="neutral" size="xs">
                    {item.sector}
                </Badge>
            </TableCell>
            <TableCell tone="muted">{item.report_date || 'N/A'}</TableCell>
            <TableCell align="right">
                {item.actual_eps !== null ? `$${item.actual_eps.toFixed(2)}` : 'N/A'}
            </TableCell>
            <TableCell align="right" tone="muted">
                {item.estimated_eps !== null ? `$${item.estimated_eps.toFixed(2)}` : 'N/A'}
            </TableCell>
            <TableCell align="right" tone={sueTone}>
                {item.sue_score !== null
                    ? item.sue_score >= 0
                        ? `+${item.sue_score.toFixed(2)}`
                        : item.sue_score.toFixed(2)
                    : 'N/A'}
            </TableCell>
            <TableCell align="right" tone={signToneOrMuted(item.revenue_surprise_pct)}>
                {item.revenue_surprise_pct !== null
                    ? item.revenue_surprise_pct >= 0
                        ? `+${item.revenue_surprise_pct.toFixed(1)}%`
                        : `${item.revenue_surprise_pct.toFixed(1)}%`
                    : 'N/A'}
            </TableCell>
            <TableCell align="center">
                {item.is_sloan_accrual_clean ? (
                    <Badge variant="soft" colorScheme="success" size="xs">
                        Clean Cash
                    </Badge>
                ) : (
                    <Badge variant="soft" colorScheme="warning" size="xs">
                        High Accrual
                    </Badge>
                )}
            </TableCell>
            <TableCell align="center">
                {item.is_top_decile_sue ? (
                    <Badge variant="soft" colorScheme="success" size="xs">
                        Top Decile
                    </Badge>
                ) : (
                    <span className="text-xs text-voxel-muted">Standard</span>
                )}
            </TableCell>
        </TableRow>
    );
}

function BellwetherTableRow({ b }: { b: SectorBellwetherSignal }) {
    return (
        <TableRow className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell>{b.sector}</TableCell>
            <TableCell className="font-mono">{b.ticker}</TableCell>
            <TableCell tone="muted">
                {b.classification === 'EARLY_BELLWETHER' ? (
                    <Badge variant="soft" colorScheme="info" size="xs">
                        Early Bellwether
                    </Badge>
                ) : (
                    <span className="text-voxel-muted">Downstream Peer</span>
                )}
            </TableCell>
            <TableCell align="right" tone="muted">
                #{b.market_cap_rank || '-'}
            </TableCell>
            <TableCell tone="muted">{b.report_date || 'Upcoming'}</TableCell>
            <TableCell align="center">
                {b.is_reported ? (
                    <Badge variant="soft" colorScheme="success" size="xs">
                        Reported
                    </Badge>
                ) : (
                    <Badge variant="soft" colorScheme="neutral" size="xs">
                        Awaiting
                    </Badge>
                )}
            </TableCell>
            <TableCell align="center">
                {b.is_active_bellwether_signal ? (
                    <Badge variant="soft" colorScheme="accent" size="xs">
                        Active Signal (14d)
                    </Badge>
                ) : (
                    <span className="text-xs text-voxel-muted">-</span>
                )}
            </TableCell>
        </TableRow>
    );
}

function RevisionTableRow({ item }: { item: EarningsAlphaSnapshot }) {
    return (
        <TableRow className="border-zinc-800/50 hover:bg-zinc-800/30">
            <TableCell>{item.ticker}</TableCell>
            <TableCell tone="muted">{item.sector}</TableCell>
            <TableCell>{item.analyst_consensus || 'Unknown'}</TableCell>
            <TableCell align="right">{item.analyst_coverage_count} analysts</TableCell>
            <TableCell align="right">
                <span
                    className={
                        item.analyst_buy_ratio_pct && item.analyst_buy_ratio_pct >= 60
                            ? 'text-success'
                            : 'text-voxel-ink'
                    }
                >
                    {item.analyst_buy_ratio_pct !== null
                        ? `${item.analyst_buy_ratio_pct.toFixed(1)}%`
                        : 'N/A'}
                </span>
            </TableCell>
            <TableCell align="right" tone="muted">
                {item.target_consensus_price ? `$${item.target_consensus_price.toFixed(2)}` : 'N/A'}
            </TableCell>
            <TableCell align="right" tone={signToneOrMuted(item.target_consensus_upside_pct)}>
                {item.target_consensus_upside_pct !== null
                    ? item.target_consensus_upside_pct >= 0
                        ? `+${item.target_consensus_upside_pct.toFixed(1)}%`
                        : `${item.target_consensus_upside_pct.toFixed(1)}%`
                    : 'N/A'}
            </TableCell>
        </TableRow>
    );
}

export function EarningsAuditPage({
    snapshots,
    bellwethers,
    predictions = [],
}: EarningsAuditPageProps) {
    const [activeTab, setActiveTab] = useState<'pead' | 'bellwethers' | 'revisions' | 'arena'>(
        'pead',
    );

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
            <div className="flex flex-col gap-6">
                {/* Header */}
                <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h1 className="text-sm font-bold uppercase tracking-wider text-voxel-ink">
                            Earnings Alpha & PEAD Audit
                        </h1>
                        <p className="text-xs font-normal text-voxel-muted">
                            Empirical earnings surprise momentum, Standardized Unexpected Earnings
                            (SUE), Sloan accruals, and sector bellwether diffusion.
                        </p>
                    </div>
                </div>

                {/* Summary Metrics */}
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,14rem),1fr))] gap-4 items-stretch">
                    <Card
                        padding="md"
                        className="h-full flex flex-col justify-between gap-1 rounded-none shadow-sm"
                    >
                        <div className="text-xs font-normal text-voxel-muted uppercase tracking-wider">
                            Total Analyzed
                        </div>
                        <div className="text-sm font-bold text-voxel-ink font-mono tabular-nums">
                            {snapshots.length}
                        </div>
                        <div className="text-xs font-normal text-voxel-muted">
                            S&P 500 Constituents
                        </div>
                    </Card>
                    <Card
                        padding="md"
                        className="h-full flex flex-col justify-between gap-1 rounded-none shadow-sm"
                    >
                        <div className="text-xs font-normal text-voxel-muted uppercase tracking-wider">
                            Top-Decile SUE (≥ +2.0)
                        </div>
                        <div className="text-sm font-bold text-success font-mono tabular-nums">
                            {topDecileCount}
                        </div>
                        <div className="text-xs font-normal text-voxel-muted">
                            Active Drift Candidates
                        </div>
                    </Card>
                    <Card
                        padding="md"
                        className="h-full flex flex-col justify-between gap-1 rounded-none shadow-sm"
                    >
                        <div className="text-xs font-normal text-voxel-muted uppercase tracking-wider">
                            Cash-Quality Clean
                        </div>
                        <div className="text-sm font-bold text-info font-mono tabular-nums">
                            {snapshots.length > 0
                                ? `${Math.round((cleanAccrualCount / snapshots.length) * 100)}%`
                                : '0%'}
                        </div>
                        <div className="text-xs font-normal text-voxel-muted">
                            Sloan Accrual Filter
                        </div>
                    </Card>
                    <Card
                        padding="md"
                        className="h-full flex flex-col justify-between gap-1 rounded-none shadow-sm"
                    >
                        <div className="text-xs font-normal text-voxel-muted uppercase tracking-wider">
                            Active Bellwethers
                        </div>
                        <div className="text-sm font-bold text-accent font-mono tabular-nums">
                            {bellwethers.filter((b) => b.is_active_bellwether_signal).length}
                        </div>
                        <div className="text-xs font-normal text-voxel-muted">
                            14-Day Signal Window
                        </div>
                    </Card>
                </div>

                {/* Navigation Tabs */}
                <div className="flex flex-wrap items-center gap-2 border-b border-voxel-bevel-hi pb-2">
                    <Button
                        type="button"
                        size="sm"
                        variant={activeTab === 'pead' ? 'solid' : 'outline'}
                        colorScheme={activeTab === 'pead' ? 'success' : 'neutral'}
                        onClick={() => setActiveTab('pead')}
                    >
                        PEAD & SUE Leaderboard
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={activeTab === 'bellwethers' ? 'solid' : 'outline'}
                        colorScheme={activeTab === 'bellwethers' ? 'info' : 'neutral'}
                        onClick={() => setActiveTab('bellwethers')}
                    >
                        Sector Bellwether Radar
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={activeTab === 'revisions' ? 'solid' : 'outline'}
                        colorScheme={activeTab === 'revisions' ? 'info' : 'neutral'}
                        onClick={() => setActiveTab('revisions')}
                    >
                        Analyst Revision Momentum
                    </Button>
                    <Button
                        type="button"
                        size="sm"
                        variant={activeTab === 'arena' ? 'solid' : 'outline'}
                        colorScheme={activeTab === 'arena' ? 'accent' : 'neutral'}
                        onClick={() => setActiveTab('arena')}
                    >
                        Day-1 Movement Arena
                    </Button>
                </div>

                {/* Filters (for PEAD, Bellwethers, Revisions) */}
                {activeTab !== 'arena' && (
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="w-full sm:w-64">
                            <Input
                                placeholder="Search ticker or sector..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="text-xs font-normal"
                            />
                        </div>
                        <div className="flex items-center gap-2 overflow-x-auto pb-1">
                            {sectors.map((sec) => (
                                <Button
                                    key={sec}
                                    type="button"
                                    size="sm"
                                    variant={selectedSector === sec ? 'solid' : 'outline'}
                                    colorScheme={selectedSector === sec ? 'accent' : 'neutral'}
                                    onClick={() => setSelectedSector(sec)}
                                    className="whitespace-nowrap"
                                >
                                    {sec}
                                </Button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Tab 1: PEAD Table */}
                {activeTab === 'pead' && (
                    <Card className="overflow-hidden bg-zinc-900/40 border-zinc-800 rounded-none shadow-sm">
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
                                            align="center"
                                            tone="muted"
                                            className="py-8"
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
                                            align="center"
                                            tone="muted"
                                            className="py-8"
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

                {/* Tab 4: Day-1 Movement Arena */}
                {activeTab === 'arena' && <EarningsArenaTab predictions={predictions} />}
            </div>
        </PageLayout>
    );
}
