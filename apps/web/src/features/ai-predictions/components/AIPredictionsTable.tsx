import {
    Badge,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@llm-market-bench/ui-design-system';
import { Fragment, useMemo, useState } from 'react';
import type { SectorPrediction } from '../api/fetch-predictions';

interface AIPredictionsTableProps {
    predictions: SectorPrediction[];
}

type ViewMode = 'dual' | 'sector' | 'pair';
type SortField =
    | 'prediction_date'
    | 'target_date'
    | 'model_name'
    | 'sector_return'
    | 'pair_return'
    | 'sector_alpha'
    | 'pair_alpha'
    | 'score';

function formatDateShort(dateStr: string): string {
    if (!dateStr) return 'N/A';
    const parts = dateStr.split('T')[0].split('-');
    if (parts.length === 3) {
        const months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
        ];
        const m = parseInt(parts[1], 10) - 1;
        const d = parseInt(parts[2], 10);
        if (m >= 0 && m < 12) {
            return `${months[m]} ${d}, ${parts[0]}`;
        }
    }
    return dateStr;
}

export function AIPredictionsTable({ predictions }: AIPredictionsTableProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [modelFilter, setModelFilter] = useState<'all' | 'deepseek' | 'minimax'>('all');
    const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'past'>('all');
    const [timeframeFilter, setTimeframeFilter] = useState<'all' | '7d' | '30d' | '60d' | '90d'>(
        'all',
    );
    const [viewMode, setViewMode] = useState<ViewMode>('dual');
    const [sortField, setSortField] = useState<SortField>('prediction_date');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('desc');
        }
    };

    const filteredAndSorted = useMemo(() => {
        return predictions
            .filter((p) => {
                const matchesSearch =
                    searchQuery === '' ||
                    p.predicted_sector.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    p.predicted_pair.join(' ').toLowerCase().includes(searchQuery.toLowerCase()) ||
                    p.model_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    p.reasoning.toLowerCase().includes(searchQuery.toLowerCase());

                const matchesModel =
                    modelFilter === 'all' ||
                    (modelFilter === 'deepseek' &&
                        p.model_name.toLowerCase().includes('deepseek')) ||
                    (modelFilter === 'minimax' && p.model_name.toLowerCase().includes('minimax'));

                const matchesStatus =
                    statusFilter === 'all' ||
                    (statusFilter === 'active' && p.status === 'pending') ||
                    (statusFilter === 'past' && p.status === 'evaluated');

                const matchesTimeframe =
                    timeframeFilter === 'all' || p.timeframe === timeframeFilter;

                return matchesSearch && matchesModel && matchesStatus && matchesTimeframe;
            })
            .sort((a, b) => {
                let valA: number | string = 0;
                let valB: number | string = 0;

                switch (sortField) {
                    case 'prediction_date':
                        valA = a.prediction_date;
                        valB = b.prediction_date;
                        break;
                    case 'target_date':
                        valA = a.target_date;
                        valB = b.target_date;
                        break;
                    case 'model_name':
                        valA = a.model_name;
                        valB = b.model_name;
                        break;
                    case 'sector_return':
                        valA = a.predicted_sector_return ?? -999;
                        valB = b.predicted_sector_return ?? -999;
                        break;
                    case 'pair_return':
                        valA = a.predicted_pair_return ?? -999;
                        valB = b.predicted_pair_return ?? -999;
                        break;
                    case 'sector_alpha':
                        valA =
                            a.predicted_sector_return != null && a.benchmark_spy_return != null
                                ? a.predicted_sector_return - a.benchmark_spy_return
                                : -999;
                        valB =
                            b.predicted_sector_return != null && b.benchmark_spy_return != null
                                ? b.predicted_sector_return - b.benchmark_spy_return
                                : -999;
                        break;
                    case 'pair_alpha':
                        valA =
                            a.predicted_pair_return != null && a.benchmark_spy_return != null
                                ? a.predicted_pair_return - a.benchmark_spy_return
                                : -999;
                        valB =
                            b.predicted_pair_return != null && b.benchmark_spy_return != null
                                ? b.predicted_pair_return - b.benchmark_spy_return
                                : -999;
                        break;
                    case 'score':
                        valA = a.sector_percentile_score ?? -1;
                        valB = b.sector_percentile_score ?? -1;
                        break;
                }

                if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
                if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
                return 0;
            });
    }, [
        predictions,
        searchQuery,
        modelFilter,
        statusFilter,
        timeframeFilter,
        sortField,
        sortOrder,
    ]);

    const renderSortArrow = (field: SortField) => {
        if (sortField !== field) return null;
        return (
            <span className="ml-1 text-xs text-blue-400">{sortOrder === 'asc' ? '▲' : '▼'}</span>
        );
    };

    return (
        <div className="space-y-4">
            {/* Top Toolbar Controls */}
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800 backdrop-blur-sm">
                <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                    {/* Search Input */}
                    <div className="relative min-w-[220px] flex-1 sm:flex-none">
                        <input
                            type="text"
                            placeholder="Search tickers, models, reasoning..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                        />
                        {searchQuery && (
                            <button
                                type="button"
                                onClick={() => setSearchQuery('')}
                                className="absolute right-2 top-1.5 text-xs text-slate-400 hover:text-white"
                            >
                                ✕
                            </button>
                        )}
                    </div>

                    {/* Model Filter */}
                    <select
                        value={modelFilter}
                        onChange={(e) =>
                            setModelFilter(e.target.value as 'all' | 'deepseek' | 'minimax')
                        }
                        className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-300 focus:outline-none focus:border-blue-500"
                    >
                        <option value="all">All Models</option>
                        <option value="deepseek">DeepSeek Models</option>
                        <option value="minimax">MiniMax-M3</option>
                    </select>

                    {/* Status Filter */}
                    <select
                        value={statusFilter}
                        onChange={(e) =>
                            setStatusFilter(e.target.value as 'all' | 'active' | 'past')
                        }
                        className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-300 focus:outline-none focus:border-blue-500"
                    >
                        <option value="all">All Statuses</option>
                        <option value="active">🔮 Active Forecasts</option>
                        <option value="past">🎯 Evaluated Outcomes</option>
                    </select>

                    {/* Timeframe Filter */}
                    <select
                        value={timeframeFilter}
                        onChange={(e) =>
                            setTimeframeFilter(
                                e.target.value as 'all' | '7d' | '30d' | '60d' | '90d',
                            )
                        }
                        className="px-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-300 focus:outline-none focus:border-blue-500"
                    >
                        <option value="all">All Horizons</option>
                        <option value="7d">7 Days</option>
                        <option value="30d">30 Days</option>
                        <option value="60d">60 Days</option>
                        <option value="90d">90 Days</option>
                    </select>
                </div>

                {/* Target View Switcher */}
                <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 self-end lg:self-auto">
                    <button
                        type="button"
                        onClick={() => setViewMode('dual')}
                        className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                            viewMode === 'dual'
                                ? 'bg-blue-600/80 text-white shadow-sm'
                                : 'text-slate-400 hover:text-slate-200'
                        }`}
                    >
                        Dual Target
                    </button>
                    <button
                        type="button"
                        onClick={() => setViewMode('sector')}
                        className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                            viewMode === 'sector'
                                ? 'bg-blue-600/80 text-white shadow-sm'
                                : 'text-slate-400 hover:text-slate-200'
                        }`}
                    >
                        Single Sector
                    </button>
                    <button
                        type="button"
                        onClick={() => setViewMode('pair')}
                        className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                            viewMode === 'pair'
                                ? 'bg-blue-600/80 text-white shadow-sm'
                                : 'text-slate-400 hover:text-slate-200'
                        }`}
                    >
                        Sector Pair
                    </button>
                </div>
            </div>

            {/* Predictions Data Table */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
                <Table>
                    <TableHeader className="bg-slate-950/80 border-b border-slate-800">
                        <TableRow className="border-slate-800 hover:bg-transparent">
                            <TableHead
                                className="text-slate-300 font-semibold text-xs cursor-pointer select-none py-3"
                                onClick={() => handleSort('model_name')}
                            >
                                Model & Prompt {renderSortArrow('model_name')}
                            </TableHead>
                            <TableHead
                                className="text-slate-300 font-semibold text-xs cursor-pointer select-none py-3"
                                onClick={() => handleSort('prediction_date')}
                            >
                                Prediction Date {renderSortArrow('prediction_date')}
                            </TableHead>
                            <TableHead
                                className="text-slate-300 font-semibold text-xs cursor-pointer select-none py-3"
                                onClick={() => handleSort('target_date')}
                            >
                                Target Date {renderSortArrow('target_date')}
                            </TableHead>
                            <TableHead className="text-slate-300 font-semibold text-xs py-3">
                                {viewMode === 'dual' && 'Predictions (Sector / Pair)'}
                                {viewMode === 'sector' && 'Sector Pick'}
                                {viewMode === 'pair' && 'Pair Combination'}
                            </TableHead>
                            <TableHead
                                className="text-slate-300 font-semibold text-xs cursor-pointer select-none py-3 text-right"
                                onClick={() =>
                                    handleSort(
                                        viewMode === 'pair' ? 'pair_return' : 'sector_return',
                                    )
                                }
                            >
                                Performance{' '}
                                {renderSortArrow(
                                    viewMode === 'pair' ? 'pair_return' : 'sector_return',
                                )}
                            </TableHead>
                            <TableHead
                                className="text-slate-300 font-semibold text-xs cursor-pointer select-none py-3 text-right"
                                onClick={() =>
                                    handleSort(viewMode === 'pair' ? 'pair_alpha' : 'sector_alpha')
                                }
                            >
                                vs S&P 500 (Alpha){' '}
                                {renderSortArrow(
                                    viewMode === 'pair' ? 'pair_alpha' : 'sector_alpha',
                                )}
                            </TableHead>
                            <TableHead
                                className="text-slate-300 font-semibold text-xs cursor-pointer select-none py-3 text-center"
                                onClick={() => handleSort('score')}
                            >
                                Percentile {renderSortArrow('score')}
                            </TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredAndSorted.length > 0 ? (
                            filteredAndSorted.map((pred) => {
                                const isExpanded = expandedRowId === pred.id;
                                const isDeepSeek = pred.model_name
                                    .toLowerCase()
                                    .includes('deepseek');

                                const secRet = pred.predicted_sector_return;
                                const pairRet = pred.predicted_pair_return;
                                const spyRet = pred.benchmark_spy_return;

                                const secAlpha =
                                    secRet != null && spyRet != null ? secRet - spyRet : null;
                                const pairAlpha =
                                    pairRet != null && spyRet != null ? pairRet - spyRet : null;

                                return (
                                    <Fragment key={pred.id}>
                                        <TableRow
                                            onClick={() =>
                                                setExpandedRowId(isExpanded ? null : pred.id)
                                            }
                                            className="border-slate-800/60 hover:bg-slate-800/40 cursor-pointer transition-colors"
                                        >
                                            {/* Model */}
                                            <TableCell className="py-3">
                                                <div className="flex items-center gap-2">
                                                    <Badge
                                                        colorScheme={
                                                            isDeepSeek ? 'accent' : 'neutral'
                                                        }
                                                        variant="soft"
                                                        className="text-[11px] font-semibold px-2 py-0.5"
                                                    >
                                                        {isDeepSeek ? 'DeepSeek' : 'MiniMax-M3'}
                                                    </Badge>
                                                    <span className="text-[10px] text-slate-400 font-mono">
                                                        {pred.prompt_tag}
                                                    </span>
                                                </div>
                                            </TableCell>

                                            {/* Prediction Date */}
                                            <TableCell className="text-xs text-slate-300 py-3 whitespace-nowrap">
                                                {formatDateShort(pred.prediction_date)}
                                            </TableCell>

                                            {/* Target Date & Status */}
                                            <TableCell className="text-xs py-3 whitespace-nowrap">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="text-slate-300 font-medium">
                                                        {formatDateShort(pred.target_date)}
                                                    </span>
                                                    {pred.status === 'pending' ? (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 border border-blue-700/50">
                                                            Active ({pred.timeframe})
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                                            Evaluated
                                                        </span>
                                                    )}
                                                </div>
                                            </TableCell>

                                            {/* Predictions */}
                                            <TableCell className="py-3">
                                                {viewMode === 'dual' && (
                                                    <div className="space-y-0.5">
                                                        <div className="text-xs font-bold text-white flex items-center gap-1">
                                                            <span className="text-blue-400 text-[10px] uppercase">
                                                                Sec:
                                                            </span>
                                                            {pred.predicted_sector}
                                                        </div>
                                                        <div className="text-[11px] text-slate-400 flex items-center gap-1">
                                                            <span className="text-emerald-400 text-[10px] uppercase">
                                                                Pair:
                                                            </span>
                                                            {pred.predicted_pair.join(' + ')}
                                                        </div>
                                                    </div>
                                                )}
                                                {viewMode === 'sector' && (
                                                    <span className="text-xs font-bold text-white">
                                                        {pred.predicted_sector}
                                                    </span>
                                                )}
                                                {viewMode === 'pair' && (
                                                    <span className="text-xs font-medium text-emerald-400">
                                                        {pred.predicted_pair.join(' + ')}
                                                    </span>
                                                )}
                                            </TableCell>

                                            {/* Performance */}
                                            <TableCell className="py-3 text-right whitespace-nowrap">
                                                {pred.status === 'pending' ? (
                                                    <span className="text-xs text-slate-500 italic">
                                                        Pending...
                                                    </span>
                                                ) : (
                                                    <div className="space-y-0.5">
                                                        {(viewMode === 'dual' ||
                                                            viewMode === 'sector') && (
                                                            <div
                                                                className={`text-xs font-semibold ${
                                                                    (secRet ?? 0) >= 0
                                                                        ? 'text-emerald-400'
                                                                        : 'text-rose-400'
                                                                }`}
                                                            >
                                                                {secRet != null
                                                                    ? `${secRet >= 0 ? '+' : ''}${secRet.toFixed(2)}%`
                                                                    : 'N/A'}
                                                            </div>
                                                        )}
                                                        {(viewMode === 'dual' ||
                                                            viewMode === 'pair') && (
                                                            <div
                                                                className={`text-[11px] ${
                                                                    (pairRet ?? 0) >= 0
                                                                        ? 'text-emerald-400/80'
                                                                        : 'text-rose-400/80'
                                                                }`}
                                                            >
                                                                {pairRet != null
                                                                    ? `${pairRet >= 0 ? '+' : ''}${pairRet.toFixed(2)}% (Pair)`
                                                                    : ''}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </TableCell>

                                            {/* Alpha vs S&P 500 */}
                                            <TableCell className="py-3 text-right whitespace-nowrap">
                                                {pred.status === 'pending' ? (
                                                    <span className="text-xs text-slate-500 italic">
                                                        --
                                                    </span>
                                                ) : (
                                                    <div className="space-y-0.5">
                                                        {(viewMode === 'dual' ||
                                                            viewMode === 'sector') && (
                                                            <div
                                                                className={`text-xs font-bold ${
                                                                    (secAlpha ?? 0) >= 0
                                                                        ? 'text-emerald-400'
                                                                        : 'text-rose-400'
                                                                }`}
                                                            >
                                                                {secAlpha != null
                                                                    ? `${secAlpha >= 0 ? '+' : ''}${secAlpha.toFixed(2)}%`
                                                                    : 'N/A'}
                                                            </div>
                                                        )}
                                                        {(viewMode === 'dual' ||
                                                            viewMode === 'pair') && (
                                                            <div
                                                                className={`text-[11px] ${
                                                                    (pairAlpha ?? 0) >= 0
                                                                        ? 'text-emerald-400/80'
                                                                        : 'text-rose-400/80'
                                                                }`}
                                                            >
                                                                {pairAlpha != null
                                                                    ? `${pairAlpha >= 0 ? '+' : ''}${pairAlpha.toFixed(2)}% (Pair)`
                                                                    : ''}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </TableCell>

                                            {/* Score */}
                                            <TableCell className="py-3 text-center">
                                                {pred.sector_percentile_score != null ? (
                                                    <Badge
                                                        colorScheme={
                                                            pred.sector_percentile_score >= 75
                                                                ? 'accent'
                                                                : 'neutral'
                                                        }
                                                        variant="soft"
                                                        className="text-xs font-bold"
                                                    >
                                                        {pred.sector_percentile_score.toFixed(1)}
                                                    </Badge>
                                                ) : (
                                                    <span className="text-xs text-slate-500">
                                                        --
                                                    </span>
                                                )}
                                            </TableCell>
                                        </TableRow>

                                        {/* Expanded Row Drawer */}
                                        {isExpanded && (
                                            <TableRow className="bg-slate-950/90 border-b border-slate-800">
                                                <TableCell colSpan={7} className="p-4 space-y-3">
                                                    <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
                                                        <div className="space-y-1 max-w-3xl">
                                                            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">
                                                                Reasoning & Market Audit
                                                            </h4>
                                                            <p className="text-xs text-slate-300 leading-relaxed italic">
                                                                "{pred.reasoning}"
                                                            </p>
                                                        </div>

                                                        {/* Audit Prices */}
                                                        {pred.evaluation_audit_data && (
                                                            <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 min-w-[240px]">
                                                                <div className="font-semibold text-slate-200 border-b border-slate-800 pb-1 flex justify-between">
                                                                    <span>Price Audit Window</span>
                                                                    <span className="text-slate-400 font-mono text-[10px]">
                                                                        {
                                                                            pred
                                                                                .evaluation_audit_data
                                                                                .start_date
                                                                        }{' '}
                                                                        ➔{' '}
                                                                        {
                                                                            pred
                                                                                .evaluation_audit_data
                                                                                .end_date
                                                                        }
                                                                    </span>
                                                                </div>

                                                                {pred.evaluation_audit_data
                                                                    .sector && (
                                                                    <div className="flex justify-between text-slate-300">
                                                                        <span>
                                                                            Sector (
                                                                            {
                                                                                pred
                                                                                    .evaluation_audit_data
                                                                                    .sector.ticker
                                                                            }
                                                                            ):
                                                                        </span>
                                                                        <span className="font-mono text-slate-200">
                                                                            Start: $
                                                                            {pred.evaluation_audit_data.sector.start_price.toFixed(
                                                                                2,
                                                                            )}{' '}
                                                                            ➔ End: $
                                                                            {pred.evaluation_audit_data.sector.end_price.toFixed(
                                                                                2,
                                                                            )}
                                                                        </span>
                                                                    </div>
                                                                )}

                                                                {pred.evaluation_audit_data.spy && (
                                                                    <div className="flex justify-between text-slate-400">
                                                                        <span>S&P 500 (SPY):</span>
                                                                        <span className="font-mono">
                                                                            Start: $
                                                                            {pred.evaluation_audit_data.spy.start_price.toFixed(
                                                                                2,
                                                                            )}{' '}
                                                                            ➔ End: $
                                                                            {pred.evaluation_audit_data.spy.end_price.toFixed(
                                                                                2,
                                                                            )}
                                                                        </span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        )}
                                    </Fragment>
                                );
                            })
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={7}
                                    className="text-center py-8 text-slate-400 text-xs italic"
                                >
                                    No predictions found matching the selected filters.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}
