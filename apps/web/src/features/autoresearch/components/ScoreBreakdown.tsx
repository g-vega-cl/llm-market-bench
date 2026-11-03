import type { PromptExperiment } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { formatEasternDateTime } from '~/utils/date';

interface ScoreBreakdownProps {
    experiment: PromptExperiment;
}

function ActiveExperimentPlaceholder() {
    return (
        <Card className="p-8 space-y-4 bg-gradient-to-br from-white to-zinc-50 dark:from-zinc-900 dark:to-zinc-950 border-zinc-200 dark:border-zinc-800 animate-fade-in">
            <div className="space-y-2">
                <SectionHeading>Score Breakdown</SectionHeading>
                <p className="text-zinc-500 dark:text-zinc-400 text-sm leading-relaxed">
                    This experiment variant is currently active. Performance metrics and the
                    risk-adjusted scoring breakdown will be computed automatically at the close of
                    the trading week.
                </p>
            </div>
        </Card>
    );
}

interface SignValueProps {
    value: number;
    suffix?: string;
    showSign?: boolean;
    className?: string;
}

function SignValue({ value, suffix = '', showSign = true, className = '' }: SignValueProps) {
    const isPositive = value >= 0;
    const sign = showSign && isPositive ? '+' : '';
    const colorClass = isPositive ? 'text-emerald-500' : 'text-rose-500';
    return (
        <span className={`${colorClass} ${className}`}>
            {sign}
            {value.toFixed(4)}
            {suffix}
        </span>
    );
}

interface PositionDetail {
    qty: number;
    end_price: number;
    value: number;
    start_price?: number;
    start_value?: number;
    start_date?: string;
    end_date?: string;
}

interface PortfolioDetail {
    owner_id?: string;
    initial_equity?: number;
    initial_cash?: number;
    end_equity?: number;
    do_nothing_return_pct?: number;
    positions?: Record<string, PositionDetail>;
}

interface ScoreMetrics {
    portfolioReturn: number;
    spyReturn: number;
    doNothingReturn: number;
    excessReturn: number;
    bondReturn: number;
    dollarReturn: number;
    opportunityCost: number;
    maxDrawdown: number;
    drawdownPenalty: number;
    netExcessReturn: number;
    volatility: number;
    spyVolatility: number;
    effectiveVolatility: number;
    weeklyEffectiveVolatility: number;
    score: number;
}

function extractScoreMetrics(metrics: Record<string, unknown>): ScoreMetrics {
    const num = (val: unknown): number => (typeof val === 'number' ? val : 0);
    const excessReturn = num(metrics.excess_return);
    const maxDrawdown = num(metrics.max_drawdown);
    const drawdownPenalty = num(metrics.drawdown_penalty);
    const netExcessReturn =
        typeof metrics.net_excess_return === 'number'
            ? metrics.net_excess_return
            : excessReturn - drawdownPenalty;
    const volatility = num(metrics.volatility);
    const spyVolatility = num(metrics.spy_volatility);
    const effectiveVolatility =
        typeof metrics.effective_volatility === 'number'
            ? metrics.effective_volatility
            : Math.max(volatility, spyVolatility, 10.0);
    const weeklyEffectiveVolatility =
        typeof metrics.weekly_effective_volatility === 'number'
            ? metrics.weekly_effective_volatility
            : effectiveVolatility / Math.sqrt(52);

    return {
        portfolioReturn: num(metrics.portfolio_return_pct),
        spyReturn: num(metrics.spy_return_pct),
        doNothingReturn: num(metrics.do_nothing_return_pct),
        excessReturn,
        bondReturn: num(metrics.bond_return_pct),
        dollarReturn: num(metrics.dollar_return_pct),
        opportunityCost: num(metrics.opportunity_cost_penalty),
        maxDrawdown,
        drawdownPenalty,
        netExcessReturn,
        volatility,
        spyVolatility,
        effectiveVolatility,
        weeklyEffectiveVolatility,
        score: num(metrics.score),
    };
}

export function ScoreBreakdown({ experiment }: ScoreBreakdownProps) {
    const metrics = experiment.metrics || {};

    if (metrics.score === undefined || metrics.score === null) {
        return <ActiveExperimentPlaceholder />;
    }

    const {
        portfolioReturn,
        spyReturn,
        doNothingReturn,
        excessReturn,
        bondReturn,
        dollarReturn,
        opportunityCost,
        maxDrawdown,
        drawdownPenalty,
        netExcessReturn,
        volatility,
        spyVolatility,
        weeklyEffectiveVolatility,
        score,
    } = extractScoreMetrics(metrics);

    // Intermediate calculations
    const excessVsSpy = portfolioReturn - spyReturn;
    const excessVsDoNothing = portfolioReturn - doNothingReturn;
    const excessVsBond = portfolioReturn - bondReturn;

    // Portfolio details
    const portfolioDetails = (metrics.portfolio_details || {}) as Record<string, PortfolioDetail>;
    const hasDetails = Object.keys(portfolioDetails).length > 0;
    const settlementDate = (metrics.evaluated_at || experiment.created_at) as string | undefined;

    return (
        <Card className="p-6 flex flex-col gap-6 bg-boxel-surface border-boxel-bevel-hi">
            <div className="flex flex-col gap-1 border-b border-boxel-bevel-hi pb-4">
                <SectionHeading>Score Audit & Step-by-Step Math</SectionHeading>
                <p className="text-boxel-muted max-w-2xl text-xs font-normal leading-relaxed">
                    Review the step-by-step arithmetic, raw inputs, and portfolio ledgers used to
                    verify the final risk-adjusted prompt score.
                </p>
            </div>

            {/* Step-by-Step Audit Flow */}
            <div className="flex flex-col gap-6">
                {/* Step 1: Excess Return vs Benchmarks */}
                <Step1CompositeReturn
                    excessReturn={excessReturn}
                    portfolioReturn={portfolioReturn}
                    spyReturn={spyReturn}
                    doNothingReturn={doNothingReturn}
                    bondReturn={bondReturn}
                    excessVsSpy={excessVsSpy}
                    excessVsDoNothing={excessVsDoNothing}
                    excessVsBond={excessVsBond}
                    settlementDate={settlementDate}
                />

                {/* Step 2: Risk-Free Bond Component */}
                <Step2RiskFreeBond
                    opportunityCost={opportunityCost}
                    bondReturn={bondReturn}
                    dollarReturn={dollarReturn}
                    portfolioReturn={portfolioReturn}
                    excessVsBond={excessVsBond}
                />

                {/* Step 3: Drawdown Penalty */}
                <Step3DrawdownRisk maxDrawdown={maxDrawdown} drawdownPenalty={drawdownPenalty} />

                {/* Step 4: Granular Portfolio & Asset Auditor (Fact Check Ledger) */}
                {hasDetails && (
                    <Step4PortfolioDetailsAuditor
                        portfolioDetails={portfolioDetails}
                        settlementDate={settlementDate}
                    />
                )}

                {/* Step 5: Complete Arithmetic */}
                <div className="p-5 rounded-none bg-boxel-trough border border-boxel-bevel-hi flex flex-col gap-4">
                    <h4 className="text-sm font-bold text-boxel-ink flex items-center gap-2">
                        <span className="flex items-center justify-center h-5 w-5 rounded-none bg-emerald-500/20 text-emerald-400 text-xs font-normal">
                            Σ
                        </span>
                        <span>Complete Score Arithmetic</span>
                    </h4>

                    <div className="bg-boxel-canvas text-boxel-muted rounded-none p-4 font-mono text-xs font-normal overflow-x-auto flex flex-col gap-2 border border-boxel-bevel-hi leading-relaxed">
                        <div className="text-boxel-muted text-sm uppercase font-bold tracking-wider border-b border-boxel-bevel-hi pb-1.5 mb-2 font-sans">
                            Math Equation Breakdown
                        </div>
                        <div>
                            score = (Composite Excess Return - Drawdown Penalty) / Weekly Effective
                            Volatility
                        </div>
                        <div className="text-boxel-muted">
                            net_excess = {excessReturn.toFixed(4)}% - {drawdownPenalty.toFixed(4)}%
                            = {netExcessReturn.toFixed(4)}%
                        </div>
                        <div className="text-boxel-muted">
                            weekly_effective_vol = max({volatility.toFixed(1)}% port,{' '}
                            {spyVolatility.toFixed(1)}% SPY, 10.0% floor) / √52 ={' '}
                            {weeklyEffectiveVolatility.toFixed(4)}%
                        </div>
                        <div className="text-emerald-400 pt-1 font-bold">
                            score = {netExcessReturn.toFixed(4)}% /{' '}
                            {weeklyEffectiveVolatility.toFixed(4)}%
                        </div>
                        <div className="text-emerald-400 font-bold text-sm pt-1.5 border-t border-boxel-bevel-hi flex items-center justify-between">
                            <span>Unified Z-Score:</span>
                            <span>
                                {score >= 0 ? '+' : ''}
                                {score.toFixed(4)}σ
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </Card>
    );
}

interface Step1CompositeReturnProps {
    excessReturn: number;
    portfolioReturn: number;
    spyReturn: number;
    doNothingReturn: number;
    bondReturn: number;
    excessVsSpy: number;
    excessVsDoNothing: number;
    excessVsBond: number;
    settlementDate?: string;
}

function Step1CompositeReturn({
    excessReturn,
    portfolioReturn,
    spyReturn,
    doNothingReturn,
    bondReturn,
    excessVsSpy,
    excessVsDoNothing,
    excessVsBond,
    settlementDate,
}: Step1CompositeReturnProps) {
    return (
        <div className="p-5 rounded-none bg-boxel-trough border border-boxel-bevel-hi flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-boxel-bevel-hi pb-2">
                <h4 className="text-sm font-bold text-boxel-ink flex items-center gap-2">
                    <span className="flex items-center justify-center h-5 w-5 rounded-none bg-emerald-500/10 text-emerald-400 text-xs font-normal">
                        1
                    </span>
                    <span>Benchmark-Triad Composite Return (40/40/20)</span>
                </h4>
                <SignValue value={excessReturn} suffix="%" showSign={true} />
            </div>

            <div className="flex flex-col gap-3 font-mono text-xs font-normal text-boxel-muted">
                {/* Excess vs SPY */}
                <div className="flex items-center justify-between">
                    <span className="flex flex-col">
                        <span className="font-sans font-bold text-boxel-ink">
                            Excess vs S&P 500 (SPY) — 40% Weight
                        </span>
                        <span>Formula: 0.4 × (Portfolio - SPY)</span>
                    </span>
                    <span className="flex flex-col items-end">
                        <span className="font-bold text-boxel-ink">
                            {portfolioReturn.toFixed(4)}% - {spyReturn.toFixed(4)}%
                        </span>
                        <SignValue value={0.4 * excessVsSpy} suffix="%" showSign={true} />
                    </span>
                </div>

                {/* Excess vs Do-Nothing */}
                <div className="flex items-center justify-between pt-2 border-t border-dashed border-boxel-bevel-hi">
                    <span className="flex flex-col">
                        <span className="font-sans font-bold text-boxel-ink">
                            Excess vs Do-Nothing Portfolio — 40% Weight
                        </span>
                        <span>Formula: 0.4 × (Portfolio - Do-Nothing)</span>
                        {settlementDate && (
                            <span className="text-xs font-normal text-boxel-muted font-mono">
                                Audited Settlement: {formatEasternDateTime(settlementDate)}
                            </span>
                        )}
                    </span>
                    <span className="flex flex-col items-end">
                        <span className="font-bold text-boxel-ink">
                            {portfolioReturn.toFixed(4)}% - {doNothingReturn.toFixed(4)}%
                        </span>
                        <SignValue value={0.4 * excessVsDoNothing} suffix="%" showSign={true} />
                    </span>
                </div>

                {/* Excess vs 10Y Bond */}
                <div className="flex items-center justify-between pt-2 border-t border-dashed border-boxel-bevel-hi">
                    <span className="flex flex-col">
                        <span className="font-sans font-bold text-boxel-ink">
                            Risk-Free Excess (vs 10Y Bond) — 20% Weight
                        </span>
                        <span>Formula: 0.2 × (Portfolio - 10Y Bond)</span>
                    </span>
                    <span className="flex flex-col items-end">
                        <span className="font-bold text-boxel-ink">
                            {portfolioReturn.toFixed(4)}% - {bondReturn.toFixed(4)}%
                        </span>
                        <SignValue value={0.2 * excessVsBond} suffix="%" showSign={true} />
                    </span>
                </div>

                {/* Combined Excess */}
                <div className="flex items-center justify-between pt-2 border-t border-boxel-bevel-hi">
                    <span className="font-sans font-bold text-boxel-ink">
                        Composite Triad Excess Return
                    </span>
                    <span className="font-bold text-boxel-ink">{excessReturn.toFixed(4)}%</span>
                </div>
            </div>
        </div>
    );
}

interface Step2RiskFreeBondProps {
    opportunityCost: number;
    bondReturn: number;
    dollarReturn: number;
    portfolioReturn: number;
    excessVsBond: number;
}

function Step2RiskFreeBond({
    opportunityCost,
    bondReturn,
    dollarReturn,
    portfolioReturn,
    excessVsBond,
}: Step2RiskFreeBondProps) {
    return (
        <div className="p-5 rounded-none bg-boxel-trough border border-boxel-bevel-hi flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-boxel-bevel-hi pb-2">
                <h4 className="text-sm font-bold text-boxel-ink flex items-center gap-2">
                    <span className="flex items-center justify-center h-5 w-5 rounded-none bg-emerald-500/10 text-emerald-400 text-xs font-normal">
                        2
                    </span>
                    <span>Risk-Free Bond Component (10Y Yield)</span>
                </h4>
                <SignValue value={opportunityCost} suffix="%" showSign={true} />
            </div>

            <div className="flex flex-col gap-3 font-mono text-xs font-normal text-boxel-muted">
                {/* Compounded Bond Yield */}
                <div className="flex items-center justify-between">
                    <span className="flex flex-col">
                        <span className="font-sans font-bold text-boxel-ink">
                            10-Year Treasury Bond Yield
                        </span>
                        <span>Compounded Weekly (Active Hurdle)</span>
                    </span>
                    <span className="font-bold text-boxel-ink">{bondReturn.toFixed(4)}%</span>
                </div>

                {/* US Dollar Index */}
                <div className="flex items-center justify-between pt-2 border-t border-dashed border-boxel-bevel-hi">
                    <span className="flex flex-col">
                        <span className="font-sans font-bold text-boxel-ink">
                            US Dollar Index (DXY/UUP) Return
                        </span>
                        <span className="text-xs text-boxel-muted font-sans font-normal uppercase tracking-wider">
                            Context Only (No Penalty)
                        </span>
                    </span>
                    <SignValue value={dollarReturn} suffix="%" showSign={true} />
                </div>

                {/* Risk-Free Excess Calculation */}
                <div className="flex items-center justify-between pt-2 border-t border-boxel-bevel-hi">
                    <span className="flex flex-col font-sans text-boxel-ink">
                        <span className="font-bold">Risk-Free Excess Calculation</span>
                        <span className="font-mono text-xs text-boxel-muted lowercase">
                            portfolio_return - bond_hurdle
                        </span>
                    </span>
                    <span className="font-bold text-boxel-ink">
                        {portfolioReturn.toFixed(4)}% - {bondReturn.toFixed(4)}% ={' '}
                        <SignValue value={excessVsBond} suffix="%" showSign={true} />
                    </span>
                </div>
            </div>
        </div>
    );
}

interface Step3DrawdownRiskProps {
    maxDrawdown: number;
    drawdownPenalty: number;
}

function Step3DrawdownRisk({ maxDrawdown, drawdownPenalty }: Step3DrawdownRiskProps) {
    return (
        <div className="p-5 rounded-none bg-boxel-trough border border-boxel-bevel-hi flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-boxel-bevel-hi pb-2">
                <h4 className="text-sm font-bold text-boxel-ink flex items-center gap-2">
                    <span className="flex items-center justify-center h-5 w-5 rounded-none bg-rose-500/10 text-rose-400 text-xs font-normal">
                        3
                    </span>
                    <span>Drawdown Risk Penalty</span>
                </h4>
                <span className="text-sm font-mono font-bold text-rose-400">
                    -{drawdownPenalty.toFixed(4)}%
                </span>
            </div>

            <div className="flex flex-col gap-3 font-mono text-xs font-normal text-boxel-muted">
                {/* Max Drawdown */}
                <div className="flex items-center justify-between">
                    <span className="flex flex-col font-sans text-boxel-ink">
                        <span className="font-bold">Maximum Drawdown</span>
                        <span className="text-boxel-muted text-xs font-normal font-sans">
                            Largest peak-to-trough drop
                        </span>
                    </span>
                    <span className="font-bold text-boxel-ink">{maxDrawdown.toFixed(4)}%</span>
                </div>

                {/* Weighting penalty */}
                <div className="flex items-center justify-between pt-2 border-t border-boxel-bevel-hi">
                    <span className="flex flex-col font-sans text-boxel-ink">
                        <span className="font-bold">Risk-Adjusted Penalty Formula</span>
                        <span className="font-mono text-xs text-boxel-muted lowercase">
                            max_drawdown × 0.3
                        </span>
                    </span>
                    <span className="font-bold text-boxel-ink">
                        {maxDrawdown.toFixed(4)}% × 0.3 = {drawdownPenalty.toFixed(4)}%
                    </span>
                </div>
            </div>
        </div>
    );
}

interface Step4PortfolioDetailsAuditorProps {
    portfolioDetails: Record<string, PortfolioDetail>;
    settlementDate?: string;
}

function Step4PortfolioDetailsAuditor({
    portfolioDetails,
    settlementDate,
}: Step4PortfolioDetailsAuditorProps) {
    return (
        <div className="p-5 rounded-none bg-boxel-trough border border-boxel-bevel-hi flex flex-col gap-4 animate-fade-in">
            <div className="flex items-center justify-between border-b border-boxel-bevel-hi pb-2">
                <h4 className="text-sm font-bold text-boxel-ink flex items-center gap-2">
                    <span className="flex items-center justify-center h-5 w-5 rounded-none bg-accent/20 text-accent text-xs font-normal">
                        4
                    </span>
                    <span>Granular Portfolio & Asset Auditor</span>
                </h4>
                <div className="flex items-center gap-3">
                    {settlementDate && (
                        <span className="text-xs font-normal text-boxel-muted font-mono">
                            Audited Settlement: {formatEasternDateTime(settlementDate)}
                        </span>
                    )}
                    <span className="text-xs text-boxel-muted font-mono font-normal uppercase tracking-wider">
                        Fact-Check Ledger
                    </span>
                </div>
            </div>

            <div className="flex flex-col gap-6">
                {Object.entries(portfolioDetails).map(
                    ([pid, detail]: [string, PortfolioDetail]) => {
                        const initialEquity = detail.initial_equity ?? 0;
                        const initialCash = detail.initial_cash ?? 0;
                        const endEquity = detail.end_equity ?? 0;
                        const dnReturn = detail.do_nothing_return_pct ?? 0;
                        const positionsList = Object.entries(detail.positions || {});
                        const is100PctCash = positionsList.length === 0;

                        return (
                            <div
                                key={pid}
                                className="flex flex-col gap-3 bg-boxel-canvas p-4 rounded-none border border-boxel-bevel-hi"
                            >
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-boxel-bevel-hi pb-2">
                                    <div className="flex items-center gap-2">
                                        <span className="h-2 w-2 rounded-none bg-accent" />
                                        <span className="text-sm font-bold text-boxel-ink">
                                            Agent: {detail.owner_id || 'Unknown'}
                                        </span>
                                        {is100PctCash && (
                                            <Badge variant="soft" size="sm">
                                                100% Cash at Week Start (0.0000% Return)
                                            </Badge>
                                        )}
                                    </div>
                                    <span className="text-xs font-normal text-boxel-muted font-mono">
                                        ID: {pid}
                                    </span>
                                </div>

                                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,10rem),1fr))] gap-3 text-xs font-mono font-normal items-stretch">
                                    <div className="flex flex-col bg-boxel-trough p-2.5 rounded-none border border-boxel-bevel-hi justify-between">
                                        <span className="text-xs font-normal text-boxel-muted font-sans">
                                            Initial Equity
                                        </span>
                                        <span className="font-bold text-boxel-ink">
                                            $
                                            {initialEquity.toLocaleString('en-US', {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                                        </span>
                                    </div>
                                    <div className="flex flex-col bg-boxel-trough p-2.5 rounded-none border border-boxel-bevel-hi justify-between">
                                        <span className="text-xs font-normal text-boxel-muted font-sans">
                                            Initial Cash
                                        </span>
                                        <span className="font-bold text-boxel-ink">
                                            $
                                            {initialCash.toLocaleString('en-US', {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                                        </span>
                                    </div>
                                    <div className="flex flex-col bg-boxel-trough p-2.5 rounded-none border border-boxel-bevel-hi justify-between">
                                        <span className="text-xs font-normal text-boxel-muted font-sans">
                                            Do-Nothing End Equity
                                        </span>
                                        <span className="font-bold text-boxel-ink">
                                            $
                                            {endEquity.toLocaleString('en-US', {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2,
                                            })}
                                        </span>
                                    </div>
                                    <div className="flex flex-col bg-boxel-trough p-2.5 rounded-none border border-boxel-bevel-hi justify-between">
                                        <span className="text-xs font-normal text-boxel-muted font-sans">
                                            Do-Nothing Return
                                        </span>
                                        <SignValue
                                            value={dnReturn}
                                            suffix="%"
                                            showSign={true}
                                            className="font-bold text-xs"
                                        />
                                    </div>
                                </div>

                                {positionsList.length > 0 && (
                                    <div className="pt-2 flex flex-col gap-1.5">
                                        <div className="text-sm font-bold text-boxel-muted uppercase tracking-wider font-sans">
                                            Starting Assets & Weekly Valuation Comparison
                                        </div>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-xs font-mono font-normal text-boxel-muted">
                                                <thead>
                                                    <tr className="border-b border-boxel-bevel-hi text-left text-boxel-muted text-sm font-bold uppercase tracking-wider">
                                                        <th className="pb-1 text-left">Asset</th>
                                                        <th className="pb-1 text-right">Qty</th>
                                                        <th className="pb-1 text-right">
                                                            Start Price
                                                        </th>
                                                        <th className="pb-1 text-right">
                                                            Start Value
                                                        </th>
                                                        <th className="pb-1 text-right">
                                                            End Price
                                                        </th>
                                                        <th className="pb-1 text-right">
                                                            End Value
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-boxel-bevel-hi/50">
                                                    {positionsList.map(
                                                        ([ticker, pos]: [
                                                            string,
                                                            PositionDetail,
                                                        ]) => (
                                                            <tr
                                                                key={ticker}
                                                                className="hover:bg-boxel-elevated/40"
                                                            >
                                                                <td className="py-1.5 font-bold text-boxel-ink text-left">
                                                                    {ticker}
                                                                </td>
                                                                <td className="py-1.5 text-right">
                                                                    {pos.qty}
                                                                </td>
                                                                <td className="py-1.5 text-right">
                                                                    {pos.start_price !==
                                                                    undefined ? (
                                                                        <div className="flex flex-col items-end">
                                                                            <span>
                                                                                $
                                                                                {pos.start_price.toFixed(
                                                                                    2,
                                                                                )}
                                                                            </span>
                                                                            {pos.start_date && (
                                                                                <span className="text-xs font-normal text-boxel-muted font-sans tracking-tight leading-none mt-0.5">
                                                                                    {pos.start_date}
                                                                                </span>
                                                                            )}
                                                                        </div>
                                                                    ) : (
                                                                        <span className="text-boxel-muted">
                                                                            —
                                                                        </span>
                                                                    )}
                                                                </td>
                                                                <td className="py-1.5 text-right font-normal">
                                                                    {pos.start_value !==
                                                                    undefined ? (
                                                                        `$${pos.start_value.toLocaleString(
                                                                            'en-US',
                                                                            {
                                                                                minimumFractionDigits: 2,
                                                                                maximumFractionDigits: 2,
                                                                            },
                                                                        )}`
                                                                    ) : (
                                                                        <span className="text-boxel-muted">
                                                                            —
                                                                        </span>
                                                                    )}
                                                                </td>
                                                                <td className="py-1.5 text-right">
                                                                    <div className="flex flex-col items-end">
                                                                        <span>
                                                                            $
                                                                            {(
                                                                                pos.end_price ?? 0
                                                                            ).toFixed(2)}
                                                                        </span>
                                                                        {pos.end_date && (
                                                                            <span className="text-xs font-normal text-boxel-muted font-sans tracking-tight leading-none mt-0.5">
                                                                                {pos.end_date}
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </td>
                                                                <td className="py-1.5 text-right font-bold text-boxel-ink">
                                                                    $
                                                                    {(
                                                                        pos.value ?? 0
                                                                    ).toLocaleString('en-US', {
                                                                        minimumFractionDigits: 2,
                                                                        maximumFractionDigits: 2,
                                                                    })}
                                                                </td>
                                                            </tr>
                                                        ),
                                                    )}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    },
                )}
            </div>
        </div>
    );
}
