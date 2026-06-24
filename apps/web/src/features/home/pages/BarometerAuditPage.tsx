import type { MarketBarometer } from '@llm-market-bench/database';
import {
    Badge,
    Button,
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
import { Link, useNavigate } from '@tanstack/react-router';
import { useMemo, useState } from 'react';

interface Constituent {
    symbol: string;
    company_name: string | null;
    market_cap: number;
    price: number;
    pe: number | null;
    pb: number | null;
    ps: number | null;
    pfcf: number | null;
    next_eps_est: number | null;
    beat: boolean | null;
    eps_actual: number | null;
    eps_estimated: number | null;
    revenue_beat: boolean | null;
    revenue_actual: number | null;
    revenue_estimated: number | null;
}

interface ColumnConfig {
    label: string;
    field: keyof Constituent;
    align: 'left' | 'right' | 'center';
}

const columns: ColumnConfig[] = [
    { label: 'Ticker', field: 'symbol', align: 'left' },
    { label: 'Company', field: 'company_name', align: 'left' },
    { label: 'Market Cap', field: 'market_cap', align: 'right' },
    { label: 'Price', field: 'price', align: 'right' },
    { label: 'P/E', field: 'pe', align: 'right' },
    { label: 'Fwd P/E', field: 'next_eps_est', align: 'right' },
    { label: 'P/S', field: 'ps', align: 'right' },
    { label: 'P/B', field: 'pb', align: 'right' },
    { label: 'P/FCF', field: 'pfcf', align: 'right' },
    { label: 'Earnings Beat', field: 'beat', align: 'center' },
    { label: 'Actual EPS', field: 'eps_actual', align: 'right' },
    { label: 'Expected EPS', field: 'eps_estimated', align: 'right' },
    { label: 'Revenue Beat', field: 'revenue_beat', align: 'center' },
    { label: 'Actual Revenue', field: 'revenue_actual', align: 'right' },
    { label: 'Expected Revenue', field: 'revenue_estimated', align: 'right' },
];

const ALIGN_CLASS: Record<'left' | 'right' | 'center', string> = {
    left: 'text-left',
    right: 'text-right',
    center: 'text-center',
};

const JUSTIFY_CLASS: Record<'left' | 'right' | 'center', string> = {
    left: 'justify-start',
    right: 'justify-end',
    center: 'justify-center',
};

export interface BarometerAuditPageProps {
    dates: string[];
    selectedDate: string | null;
    barometer: MarketBarometer | null;
}

function isNullOrUndefined(val: unknown): boolean {
    return val === null || val === undefined;
}

function compareNumbers(a: number, b: number, sortOrder: 'asc' | 'desc'): number {
    return sortOrder === 'asc' ? a - b : b - a;
}

function compareStrings(a: string, b: string, sortOrder: 'asc' | 'desc'): number {
    return sortOrder === 'asc' ? a.localeCompare(b) : b.localeCompare(a);
}

function compareValues(valA: unknown, valB: unknown, sortOrder: 'asc' | 'desc'): number {
    if (isNullOrUndefined(valA)) return sortOrder === 'asc' ? -1 : 1;
    if (isNullOrUndefined(valB)) return sortOrder === 'asc' ? 1 : -1;

    if (typeof valA === 'string' && typeof valB === 'string') {
        return compareStrings(valA, valB, sortOrder);
    }

    const numA = typeof valA === 'boolean' ? (valA ? 1 : 0) : (valA as number);
    const numB = typeof valB === 'boolean' ? (valB ? 1 : 0) : (valB as number);

    return compareNumbers(numA, numB, sortOrder);
}

export function BarometerAuditPage({ dates, selectedDate, barometer }: BarometerAuditPageProps) {
    const navigate = useNavigate({ from: '/barometer-audit' });
    const [searchTerm, setSearchTerm] = useState('');
    const [beatFilter, setBeatFilter] = useState<'all' | 'beat' | 'miss' | 'na'>('all');
    const [sortBy, setSortBy] = useState<keyof Constituent>('market_cap');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    // Parse constituents from JSONB field safely
    const constituents = useMemo(() => {
        if (!barometer?.constituents_data) {
            return [];
        }
        return barometer.constituents_data as unknown as Constituent[];
    }, [barometer]);

    // Handle Sorting
    const handleSort = (field: keyof Constituent) => {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder('desc');
        }
    };

    // Filter and Sort constituents
    const processedConstituents = useMemo(() => {
        let list = [...constituents];

        // Apply Search Term
        if (searchTerm.trim()) {
            const query = searchTerm.toLowerCase();
            list = list.filter(
                (c) =>
                    c.symbol.toLowerCase().includes(query) ||
                    c.company_name?.toLowerCase().includes(query),
            );
        }

        // Apply Beat Filter
        if (beatFilter !== 'all') {
            list = list.filter((c) => {
                if (beatFilter === 'beat') return c.beat === true;
                if (beatFilter === 'miss') return c.beat === false;
                return c.beat === null || c.beat === undefined;
            });
        }

        // Apply Sort
        list.sort((a, b) => compareValues(a[sortBy], b[sortBy], sortOrder));

        return list;
    }, [constituents, searchTerm, beatFilter, sortBy, sortOrder]);

    const formatMarketCap = (cap: number) => {
        if (cap >= 1e12) {
            return `$${(cap / 1e12).toFixed(2)}T`;
        }
        if (cap >= 1e9) {
            return `$${(cap / 1e9).toFixed(2)}B`;
        }
        return `$${(cap / 1e6).toFixed(2)}M`;
    };

    const formatValue = (val: number | null | undefined, decimals = 2) => {
        if (val === null || val === undefined) return '—';
        return val.toFixed(decimals);
    };

    const formatRevenue = (rev: number | null | undefined) => {
        if (rev === null || rev === undefined) return '—';
        if (rev >= 1e12) {
            return `$${(rev / 1e12).toFixed(2)}T`;
        }
        if (rev >= 1e9) {
            return `$${(rev / 1e9).toFixed(2)}B`;
        }
        if (rev >= 1e6) {
            return `$${(rev / 1e6).toFixed(2)}M`;
        }
        return `$${rev.toLocaleString()}`;
    };

    return (
        <PageLayout>
            <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
                {/* Back button and Date selector */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <Link to="/">
                            <Button variant="ghost" size="sm" className="mb-2">
                                ◀ Back to Dashboard
                            </Button>
                        </Link>
                        <h1 className="text-3xl font-black tracking-tight text-white font-display uppercase">
                            Market Health Barometer Audit
                        </h1>
                        <p className="text-white/60 text-sm mt-1">
                            Auditing S&P 500 aggregate valuation and earnings health statistics
                        </p>
                    </div>

                    <div className="flex items-center gap-3 bg-zinc-900/60 border border-zinc-800 p-3 rounded-xl backdrop-blur-md">
                        <label
                            htmlFor="date-select"
                            className="text-xs font-bold uppercase tracking-wider text-white/40 font-mono"
                        >
                            Select Date:
                        </label>
                        <select
                            id="date-select"
                            value={selectedDate || ''}
                            onChange={(e) => {
                                navigate({
                                    search: (prev) => ({
                                        ...prev,
                                        date: e.target.value || undefined,
                                    }),
                                });
                            }}
                            className="bg-zinc-950 border border-zinc-800 text-white px-3 py-1.5 rounded-lg text-sm focus:outline-none focus:border-accent font-mono cursor-pointer"
                        >
                            {dates.map((date) => (
                                <option key={date} value={date}>
                                    {date}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Latest aggregates overlay */}
                {barometer && (
                    <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                        {[
                            { label: 'Trailing P/E', val: barometer.pe_ratio, highlight: true },
                            { label: 'Forward P/E', val: barometer.forward_pe, highlight: true },
                            { label: 'Price-to-Book', val: barometer.pb_ratio },
                            { label: 'Price-to-Sales', val: barometer.ps_ratio },
                            { label: 'Price-to-FCF', val: barometer.pfcf_ratio },
                            {
                                label: 'Earnings Beat Rate',
                                val: barometer.earnings_surprise_momentum,
                                suffix: '%',
                                colorScheme: 'success',
                            },
                        ].map((item) => (
                            <Card
                                key={item.label}
                                className={`p-4 flex flex-col justify-between ${
                                    item.highlight
                                        ? 'bg-gradient-to-br from-white/[0.06] to-transparent'
                                        : ''
                                }`}
                            >
                                <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider">
                                    {item.label}
                                </span>
                                <span
                                    className={`text-2xl font-black font-mono tracking-tight mt-2 ${
                                        item.colorScheme === 'success'
                                            ? 'text-emerald-400'
                                            : 'text-white'
                                    }`}
                                >
                                    {formatValue(item.val)}
                                    {item.val !== null && item.suffix}
                                </span>
                            </Card>
                        ))}
                    </div>
                )}

                {/* Methodology Card */}
                <Card className="p-6 space-y-4 bg-glass-dark border-white/10">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-white/40 border-b border-white/5 pb-2 font-display">
                        Calculation Methodology
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm text-white/70">
                        <div className="space-y-3">
                            <div>
                                <span className="font-bold text-white block mb-1">
                                    Cap-Weighted Index Aggregates
                                </span>
                                <p className="text-xs leading-relaxed text-white/60">
                                    All multiples are calculated using the index aggregate
                                    capitalization method rather than a simple arithmetic average.
                                    This aligns the metrics with true index weightings.
                                </p>
                            </div>
                            <div>
                                <span className="font-bold text-white block mb-1 font-mono">
                                    Trailing P/E = Sum(Mcap) / Sum(Net Income)
                                </span>
                                <p className="text-xs leading-relaxed text-white/60">
                                    Determined by summing the total market cap of the constituents
                                    and dividing it by their aggregate net income (derived from
                                    `Market Cap / Trailing P/E`). Includes loss-making companies.
                                </p>
                            </div>
                        </div>

                        <div className="space-y-3">
                            <div>
                                <span className="font-bold text-white block mb-1 font-mono">
                                    Forward P/E = Sum(Mcap) / Sum(Est. Net Income)
                                </span>
                                <p className="text-xs leading-relaxed text-white/60">
                                    Uses the next fiscal year's consensus EPS estimate multiplied by
                                    shares outstanding (`Market Cap / Price`) to estimate forward
                                    aggregate income. Excludes negative/zero forward estimates.
                                </p>
                            </div>
                            <div>
                                <span className="font-bold text-white block mb-1">
                                    P/B and P/S Ratios
                                </span>
                                <p className="text-xs leading-relaxed text-white/60">
                                    Calculated as `Sum(Mcap) / Sum(Book Value)` and `Sum(Mcap) /
                                    Sum(Revenue)` respectively, capturing aggregate book value and
                                    total sales across top 100 S&P 500 constituents.
                                </p>
                            </div>
                        </div>
                    </div>
                </Card>

                {/* Audit Table and Controls */}
                <Card className="p-6 space-y-6">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-4 border-b border-white/5 pb-4">
                        <div>
                            <h3 className="text-lg font-black text-white font-display uppercase tracking-wider">
                                Constituent Weights & Valuation (Top {constituents.length})
                            </h3>
                            <p className="text-xs text-white/40">
                                Clicking table headers changes sorting order
                            </p>
                        </div>

                        {/* Filters */}
                        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                            <div className="flex-1 md:flex-initial">
                                <Input
                                    placeholder="Search by Ticker/Name..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full md:w-64"
                                />
                            </div>
                            <select
                                aria-label="Filter Earnings Status"
                                value={beatFilter}
                                onChange={(e) =>
                                    setBeatFilter(e.target.value as 'all' | 'beat' | 'miss' | 'na')
                                }
                                className="bg-zinc-950 border border-zinc-800 text-white px-3 py-2.5 rounded-lg text-xs focus:outline-none focus:border-accent font-mono cursor-pointer w-full md:w-auto"
                            >
                                <option value="all">All Earnings Status</option>
                                <option value="beat">Beats Only</option>
                                <option value="miss">Misses Only</option>
                                <option value="na">No Data Only</option>
                            </select>
                        </div>
                    </div>

                    {/* Check if we have constituents data */}
                    {constituents.length === 0 ? (
                        <div className="py-12 text-center text-white/40 space-y-2 border border-dashed border-zinc-800 rounded-xl">
                            <span className="text-2xl">⚠️</span>
                            <h4 className="font-bold text-white/80">
                                No Constituent-Level Data Available
                            </h4>
                            <p className="text-xs max-w-md mx-auto text-white/40 leading-relaxed px-4">
                                Individual stock weights and ratios are only captured for daily
                                barometer runs completed after 2026-06-17. Prior records only
                                contain index aggregate metrics.
                            </p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto rounded-xl border border-white/5 bg-zinc-950/40">
                            <Table>
                                <TableHeader>
                                    <TableRow className="border-b border-white/5 hover:bg-transparent">
                                        {columns.map((col) => (
                                            <TableHead
                                                key={col.label}
                                                onClick={() => handleSort(col.field)}
                                                className={`cursor-pointer hover:text-white transition-colors py-3 px-4 text-xs font-bold text-white/40 uppercase tracking-wider select-none font-display ${
                                                    ALIGN_CLASS[col.align]
                                                }`}
                                            >
                                                <div
                                                    className={`flex items-center gap-1.5 ${
                                                        JUSTIFY_CLASS[col.align]
                                                    }`}
                                                >
                                                    {col.label}
                                                    {sortBy === col.field && (
                                                        <span className="text-[10px] text-accent">
                                                            {sortOrder === 'asc' ? '▲' : '▼'}
                                                        </span>
                                                    )}
                                                </div>
                                            </TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {processedConstituents.length === 0 ? (
                                        <TableRow>
                                            <TableCell
                                                colSpan={15}
                                                className="text-center py-8 text-white/40"
                                            >
                                                No constituents match search criteria.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        processedConstituents.map((c) => {
                                            let fwdPe: number | null = null;
                                            if (
                                                c.next_eps_est &&
                                                c.next_eps_est > 0 &&
                                                c.price > 0
                                            ) {
                                                fwdPe = c.price / c.next_eps_est;
                                            }

                                            return (
                                                <TableRow
                                                    key={c.symbol}
                                                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                                                >
                                                    <TableCell className="py-2.5 px-4 font-mono font-bold text-white text-sm">
                                                        {c.symbol}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-white/80 max-w-[200px] truncate text-xs">
                                                        {c.company_name || '—'}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatMarketCap(c.market_cap)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        ${formatValue(c.price)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(c.pe)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(fwdPe)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(c.ps)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(c.pb)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(c.pfcf)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-center">
                                                        {c.beat === true && (
                                                            <Badge
                                                                colorScheme="success"
                                                                variant="soft"
                                                                size="sm"
                                                            >
                                                                BEAT
                                                            </Badge>
                                                        )}
                                                        {c.beat === false && (
                                                            <Badge
                                                                colorScheme="danger"
                                                                variant="soft"
                                                                size="sm"
                                                            >
                                                                MISS
                                                            </Badge>
                                                        )}
                                                        {c.beat === null && (
                                                            <span className="text-white/20 text-xs font-mono">
                                                                —
                                                            </span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(c.eps_actual)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatValue(c.eps_estimated)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-center">
                                                        {c.revenue_beat === true && (
                                                            <Badge
                                                                colorScheme="success"
                                                                variant="soft"
                                                                size="sm"
                                                            >
                                                                BEAT
                                                            </Badge>
                                                        )}
                                                        {c.revenue_beat === false && (
                                                            <Badge
                                                                colorScheme="danger"
                                                                variant="soft"
                                                                size="sm"
                                                            >
                                                                MISS
                                                            </Badge>
                                                        )}
                                                        {c.revenue_beat === null && (
                                                            <span className="text-white/20 text-xs font-mono">
                                                                —
                                                            </span>
                                                        )}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatRevenue(c.revenue_actual)}
                                                    </TableCell>
                                                    <TableCell className="py-2.5 px-4 text-right font-mono text-white/80 text-xs">
                                                        {formatRevenue(c.revenue_estimated)}
                                                    </TableCell>
                                                </TableRow>
                                            );
                                        })
                                    )}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </Card>
            </div>
        </PageLayout>
    );
}
