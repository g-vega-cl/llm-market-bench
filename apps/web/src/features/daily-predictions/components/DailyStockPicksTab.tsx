import { Badge, Button, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { useMemo, useState } from 'react';
import type { DailyStockBasket, DailyStockPick } from '../api/fetch-stock-picks';

export interface DailyStockPicksTabProps {
    baskets: DailyStockBasket[];
}

const STOCK_MODELS = [
    { id: 'consensus', label: '⭐ Consensus' },
    { id: 'deepseek-flash', label: 'DeepSeek Flash' },
    { id: 'MiniMax-M3.1-Flash', label: 'MiniMax-M3.1-Flash' },
    { id: 'gpt-6-luna', label: 'GPT-6 Luna' },
];

function ModelFilterButtons({
    selectedModel,
    onSelectModel,
}: {
    selectedModel: string;
    onSelectModel: (id: string) => void;
}) {
    return (
        <div className="flex flex-wrap items-center gap-2">
            {STOCK_MODELS.map((m) => {
                const isActive = selectedModel === m.id;
                return (
                    <Button
                        key={m.id}
                        type="button"
                        variant={isActive ? 'solid' : 'outline'}
                        colorScheme={isActive ? 'accent' : 'neutral'}
                        size="sm"
                        onClick={() => onSelectModel(m.id)}
                        className="uppercase tracking-wider"
                    >
                        {m.label}
                    </Button>
                );
            })}
        </div>
    );
}

function BasketMetricsOverview({ basket }: { basket: DailyStockBasket }) {
    if (basket.status !== 'evaluated') return null;

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4 rounded-none border border-voxel-bevel-hi bg-voxel-trough">
                <span className="text-xs uppercase tracking-wider text-voxel-muted font-mono">
                    Directional Hit Rate
                </span>
                <div className="text-sm font-bold font-mono tabular-nums text-success mt-1">
                    {basket.directional_hit_rate != null ? `${basket.directional_hit_rate}%` : '—'}
                </div>
            </Card>
            <Card className="p-4 rounded-none border border-voxel-bevel-hi bg-voxel-trough">
                <span className="text-xs uppercase tracking-wider text-voxel-muted font-mono">
                    Net L/S Spread Alpha
                </span>
                <div
                    className={`text-sm font-bold font-mono tabular-nums mt-1 ${
                        (basket.ls_spread_alpha_pct || 0) >= 0 ? 'text-success' : 'text-danger'
                    }`}
                >
                    {basket.ls_spread_alpha_pct != null
                        ? `${basket.ls_spread_alpha_pct > 0 ? '+' : ''}${basket.ls_spread_alpha_pct}%`
                        : '—'}
                </div>
            </Card>
            <Card className="p-4 rounded-none border border-voxel-bevel-hi bg-voxel-trough">
                <span className="text-xs uppercase tracking-wider text-voxel-muted font-mono">
                    SPY Benchmark Move
                </span>
                <div className="text-sm font-bold font-mono tabular-nums text-voxel-ink mt-1">
                    {basket.benchmark_spy_return_pct != null
                        ? `${basket.benchmark_spy_return_pct > 0 ? '+' : ''}${basket.benchmark_spy_return_pct}%`
                        : '—'}
                </div>
            </Card>
            <Card className="p-4 rounded-none border border-voxel-bevel-hi bg-voxel-trough">
                <span className="text-xs uppercase tracking-wider text-voxel-muted font-mono">
                    Excess vs SPY Alpha
                </span>
                <div
                    className={`text-sm font-bold font-mono tabular-nums mt-1 ${
                        (basket.excess_alpha_vs_spy_pct || 0) >= 0 ? 'text-success' : 'text-danger'
                    }`}
                >
                    {basket.excess_alpha_vs_spy_pct != null
                        ? `${basket.excess_alpha_vs_spy_pct > 0 ? '+' : ''}${basket.excess_alpha_vs_spy_pct}%`
                        : '—'}
                </div>
            </Card>
        </div>
    );
}

function fmtPct(val: number | null | undefined): string {
    if (val == null) return '—';
    return `${val > 0 ? '+' : ''}${val}%`;
}

function HistoricalBasketRow({ basket: b }: { basket: DailyStockBasket }) {
    const statusScheme =
        b.status === 'evaluated' ? 'success' : b.status === 'cancelled' ? 'danger' : 'warning';
    const isAlphaPos = (b.ls_spread_alpha_pct || 0) >= 0;

    return (
        <tr className="hover:bg-voxel-elevated/40 transition-colors">
            <td className="p-3 font-bold">{b.target_date}</td>
            <td className="p-3 text-voxel-muted">{b.model_name}</td>
            <td className="p-3">
                <Badge variant="soft" colorScheme={statusScheme}>
                    {b.status}
                </Badge>
            </td>
            <td className="p-3 text-right tabular-nums font-bold">
                {b.directional_hit_rate != null ? `${b.directional_hit_rate}%` : '—'}
            </td>
            <td className="p-3 text-right tabular-nums text-success">
                {fmtPct(b.mean_long_return_pct)}
            </td>
            <td className="p-3 text-right tabular-nums text-danger">
                {fmtPct(b.mean_short_return_pct)}
            </td>
            <td
                className={`p-3 text-right tabular-nums font-bold ${
                    isAlphaPos ? 'text-success' : 'text-danger'
                }`}
            >
                {fmtPct(b.ls_spread_alpha_pct)}
            </td>
            <td className="p-3 text-right tabular-nums text-voxel-muted">
                {fmtPct(b.benchmark_spy_return_pct)}
            </td>
        </tr>
    );
}

export function DailyStockPicksTab({ baskets }: DailyStockPicksTabProps) {
    const [selectedModel, setSelectedModel] = useState<string>('consensus');

    const filteredBaskets = useMemo(() => {
        return baskets.filter((b) => {
            if (selectedModel === 'consensus') return b.model_name === 'consensus';
            return b.model_name.toLowerCase().includes(selectedModel.toLowerCase());
        });
    }, [baskets, selectedModel]);

    const latestBasket = filteredBaskets[0] || null;
    const picksUp = (latestBasket?.picks || []).filter((p) => p.direction === 'UP');
    const picksDown = (latestBasket?.picks || []).filter((p) => p.direction === 'DOWN');

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-4">
                <ModelFilterButtons
                    selectedModel={selectedModel}
                    onSelectModel={setSelectedModel}
                />
                {latestBasket && (
                    <div className="flex items-center gap-2 text-xs font-mono text-voxel-muted">
                        <span>SESSION:</span>
                        <Badge variant="soft" colorScheme="neutral">
                            {latestBasket.target_date}
                        </Badge>
                        <Badge
                            variant="solid"
                            colorScheme={
                                latestBasket.status === 'evaluated' ? 'success' : 'warning'
                            }
                        >
                            {latestBasket.status.toUpperCase()}
                        </Badge>
                    </div>
                )}
            </div>

            {latestBasket && <BasketMetricsOverview basket={latestBasket} />}

            {latestBasket ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card className="p-5 rounded-none border-t-4 border-t-emerald-600 border-x border-b border-voxel-bevel-hi bg-voxel-surface">
                        <div className="flex items-center justify-between border-b border-voxel-bevel-hi pb-3 mb-4">
                            <span className="font-bold text-sm uppercase tracking-wider text-success flex items-center gap-2">
                                <span>🟢</span> 3 Stocks To Go UP (Long)
                            </span>
                            <Badge variant="soft" colorScheme="success">
                                Long Basket
                            </Badge>
                        </div>
                        <div className="flex flex-col gap-4">
                            {picksUp.map((pick) => (
                                <PickCard key={pick.id} pick={pick} />
                            ))}
                        </div>
                    </Card>

                    <Card className="p-5 rounded-none border-t-4 border-t-rose-600 border-x border-b border-voxel-bevel-hi bg-voxel-surface">
                        <div className="flex items-center justify-between border-b border-voxel-bevel-hi pb-3 mb-4">
                            <span className="font-bold text-sm uppercase tracking-wider text-danger flex items-center gap-2">
                                <span>🔴</span> 3 Stocks To Go DOWN (Short)
                            </span>
                            <Badge variant="soft" colorScheme="danger">
                                Short Basket
                            </Badge>
                        </div>
                        <div className="flex flex-col gap-4">
                            {picksDown.map((pick) => (
                                <PickCard key={pick.id} pick={pick} />
                            ))}
                        </div>
                    </Card>
                </div>
            ) : (
                <Card className="p-8 text-center text-voxel-muted rounded-none border border-voxel-bevel-hi font-mono text-sm">
                    No active stock picks found for selected model track.
                </Card>
            )}

            {filteredBaskets.length > 0 && (
                <div className="flex flex-col gap-3 mt-4">
                    <SectionHeading>Historical Basket Performance & Alpha Log</SectionHeading>
                    <div className="overflow-x-auto border border-voxel-bevel-hi">
                        <table className="w-full text-left text-sm border-collapse">
                            <thead>
                                <tr className="border-b border-voxel-bevel-hi bg-voxel-trough text-voxel-muted font-mono text-xs uppercase">
                                    <th className="p-3">Date</th>
                                    <th className="p-3">Model</th>
                                    <th className="p-3">Status</th>
                                    <th className="p-3 text-right">Hit Rate</th>
                                    <th className="p-3 text-right">Mean Long</th>
                                    <th className="p-3 text-right">Mean Short</th>
                                    <th className="p-3 text-right">L/S Alpha</th>
                                    <th className="p-3 text-right">SPY Move</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-voxel-bevel-lo font-mono text-xs">
                                {filteredBaskets.map((b) => (
                                    <HistoricalBasketRow key={b.id} basket={b} />
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}

function PickCard({ pick }: { pick: DailyStockPick }) {
    return (
        <div className="p-3.5 bg-voxel-trough border border-voxel-bevel-hi rounded-none flex flex-col gap-2">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-voxel-muted">
                        #{pick.rank}
                    </span>
                    <span className="font-mono font-bold text-sm tracking-tight text-voxel-ink">
                        {pick.ticker}
                    </span>
                    <Badge variant="soft" colorScheme="neutral">
                        {pick.confidence}% Conviction
                    </Badge>
                </div>
                {pick.status === 'evaluated' && (
                    <Badge variant="solid" colorScheme={pick.is_hit ? 'success' : 'danger'}>
                        {pick.is_hit ? 'HIT' : 'MISS'}
                    </Badge>
                )}
            </div>

            <p className="text-xs text-voxel-muted line-clamp-2">{pick.reasoning}</p>

            {pick.status === 'evaluated' && pick.open_price != null && pick.close_price != null && (
                <div className="flex flex-wrap items-center justify-between pt-2 border-t border-voxel-bevel-lo font-mono text-xs text-voxel-muted">
                    <div>
                        <span>Open: ${pick.open_price.toFixed(2)}</span>
                        <span className="mx-1.5">→</span>
                        <span>Close: ${pick.close_price.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <span>
                            Stock:{' '}
                            <strong className="text-voxel-ink">
                                {pick.stock_return_pct != null
                                    ? `${pick.stock_return_pct > 0 ? '+' : ''}${pick.stock_return_pct}%`
                                    : '—'}
                            </strong>
                        </span>
                        <span
                            className={`font-bold ${
                                (pick.position_return_pct || 0) >= 0
                                    ? 'text-success'
                                    : 'text-danger'
                            }`}
                        >
                            PnL:{' '}
                            {pick.position_return_pct != null
                                ? `${pick.position_return_pct > 0 ? '+' : ''}${pick.position_return_pct}%`
                                : '—'}
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}
