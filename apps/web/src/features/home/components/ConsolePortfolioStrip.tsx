import type { LiveTraderPortfolioSummary } from '../api/fetch-intraday-tape';

export interface ConsolePortfolioStripProps {
    portfolio?: LiveTraderPortfolioSummary | null;
}

function formatMoney(val: number) {
    const sign = val < 0 ? '-' : '';
    return `${sign}$${Math.abs(val).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

interface ComputedMetrics {
    totalEquity: number;
    cash: number;
    shares: number;
    cashPct: number;
    posPct: number;
    pnlPct: number;
    unrealizedPnl: number;
    pnlColor: string;
}

function computeMetrics(portfolio: LiveTraderPortfolioSummary): ComputedMetrics {
    const totalEquity = portfolio.total_equity || 10000;
    const cash = portfolio.cash_balance || 10000;
    const shares = portfolio.position_shares || 0;
    const costBasis = portfolio.position_cost_basis || 0;
    const marketValue = portfolio.position_market_value || 0;
    const unrealizedPnl = portfolio.unrealized_pnl || 0;
    const cashPct = totalEquity > 0 ? (cash / totalEquity) * 100 : 100;
    const posPct = totalEquity > 0 ? (marketValue / totalEquity) * 100 : 0;
    const pnlPct = costBasis > 0 && shares > 0 ? (unrealizedPnl / (shares * costBasis)) * 100 : 0;

    let pnlColor = 'text-boxel-muted';
    if (unrealizedPnl > 0) pnlColor = 'text-success';
    else if (unrealizedPnl < 0) pnlColor = 'text-danger';

    return { totalEquity, cash, shares, cashPct, posPct, pnlPct, unrealizedPnl, pnlColor };
}

export function ConsolePortfolioStrip({ portfolio }: ConsolePortfolioStripProps) {
    if (!portfolio) {
        return null;
    }

    const { totalEquity, cash, shares, cashPct, posPct, pnlPct, unrealizedPnl, pnlColor } =
        computeMetrics(portfolio);

    return (
        <div
            data-testid="console-portfolio-strip"
            className="voxel-trough p-3 flex flex-col gap-2 font-mono text-xs"
        >
            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-boxel-bevel-hi/50 pb-1.5">
                <span className="text-sm font-bold uppercase tracking-wider text-accent">
                    Live Desk Portfolio
                </span>
                <span className="text-boxel-muted">Target: 20% SPY Cap</span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
                <div className="flex items-center gap-1.5">
                    <span className="text-boxel-muted">EQUITY:</span>
                    <span className="font-bold text-boxel-ink text-sm">
                        {formatMoney(totalEquity)}
                    </span>
                </div>

                <div className="flex items-center gap-1.5">
                    <span className="text-boxel-muted">CASH:</span>
                    <span className="text-boxel-ink">
                        {formatMoney(cash)} ({cashPct.toFixed(1)}%)
                    </span>
                </div>

                <div className="flex items-center gap-1.5">
                    <span className="text-boxel-muted">POSITION:</span>
                    {shares > 0 ? (
                        <span className="font-bold text-boxel-ink">
                            {shares} SPY ({posPct.toFixed(1)}% alloc)
                        </span>
                    ) : (
                        <span className="text-boxel-muted">0 SPY (100% Cash)</span>
                    )}
                </div>

                {shares > 0 && (
                    <div className="flex items-center gap-1.5">
                        <span className="text-boxel-muted">P&amp;L:</span>
                        <span className={`font-bold ${pnlColor}`}>
                            {unrealizedPnl >= 0 ? '+' : ''}
                            {formatMoney(unrealizedPnl)} ({pnlPct >= 0 ? '+' : ''}
                            {pnlPct.toFixed(2)}%)
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
}
