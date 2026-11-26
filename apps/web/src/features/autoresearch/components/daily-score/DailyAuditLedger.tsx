import { Button } from '@llm-market-bench/ui-design-system';
import { formatEasternDateTime } from '~/utils/date';
import {
    type ActualReturns,
    type Checkpoint,
    getAgentDisplayName,
    type PortfolioDetail,
} from './daily-score-math';

const formatVal = (val: number) => `${val.toFixed(4)}%`;
const formatValWithParentheses = (val: number) =>
    val < 0 ? `(${val.toFixed(4)}%)` : `${val.toFixed(4)}%`;

interface DailyAuditLedgerProps {
    selectedDayName: string;
    selectedCp: Checkpoint;
    multiplier: number;
    portfolioReturn: number;
    spyReturn: number;
    doNothingReturn: number;
    bondReturn: number;
    maxDrawdown: number;
    dailyExcessReturn: number;
    opportunityCost: number;
    dailyDrawdownPenalty: number;
    dailyScore: number;
    portfolioDetails?: Record<string, PortfolioDetail>;
    actualReturns?: ActualReturns | null;
    isLoadingActuals?: boolean;
    actualsError?: string | null;
    isPending?: boolean;
    isActive?: boolean;
    evaluatedAt?: string | null;
    onClose: () => void;
}

function ScaledMetricTiles({
    dailyExcessReturn,
    opportunityCost,
    dailyDrawdownPenalty,
    multiplier,
}: {
    dailyExcessReturn: number;
    opportunityCost: number;
    dailyDrawdownPenalty: number;
    multiplier: number;
}) {
    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-4 items-stretch">
            <div className="p-3 bg-voxel-trough border border-voxel-bevel-hi rounded-none h-full flex flex-col justify-between gap-1">
                <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                    Excess Return (Scaled)
                </div>
                <div
                    className={`text-sm font-mono font-bold ${dailyExcessReturn >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}
                >
                    {dailyExcessReturn >= 0 ? '+' : ''}
                    {(dailyExcessReturn * multiplier).toFixed(4)}%
                </div>
                <div className="text-xs font-normal text-voxel-muted font-mono">
                    Base: {dailyExcessReturn.toFixed(4)}%
                </div>
            </div>

            <div className="p-3 bg-voxel-trough border border-voxel-bevel-hi rounded-none h-full flex flex-col justify-between gap-1">
                <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                    Risk-Free Excess (Scaled)
                </div>
                <div
                    className={`text-sm font-mono font-bold ${opportunityCost >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                >
                    {opportunityCost >= 0 ? '+' : ''}
                    {(opportunityCost * multiplier).toFixed(4)}%
                </div>
                <div className="text-xs font-normal text-voxel-muted font-mono">
                    Base: {opportunityCost >= 0 ? '+' : ''}
                    {opportunityCost.toFixed(4)}%
                </div>
            </div>

            <div className="p-3 bg-voxel-trough border border-voxel-bevel-hi rounded-none h-full flex flex-col justify-between gap-1">
                <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                    Risk Penalty (Scaled)
                </div>
                <div className="text-sm font-mono font-bold text-rose-400">
                    -{(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                </div>
                <div className="text-xs font-normal text-voxel-muted font-mono">
                    Base: -{dailyDrawdownPenalty.toFixed(4)}%
                </div>
            </div>
        </div>
    );
}

function PortfolioReturnSection({
    portfolioReturn,
    multiplier,
    actualReturns,
    isLoadingActuals,
    actualsError,
    isPending,
}: {
    portfolioReturn: number;
    multiplier: number;
    actualReturns?: ActualReturns | null;
    isLoadingActuals?: boolean;
    actualsError?: string | null;
    isPending?: boolean;
}) {
    return (
        <div className="flex flex-col gap-1.5 border-b border-voxel-bevel-hi/60 pb-3">
            <div className="flex flex-col sm:flex-row sm:justify-between text-sm font-bold text-voxel-ink">
                <span>2. Portfolio Return (Compounded equal-weighted daily returns of agents)</span>
                <span>
                    {(portfolioReturn * multiplier).toFixed(4)}%{' '}
                    <span className="text-xs font-normal text-voxel-muted">
                        (Base: {portfolioReturn.toFixed(4)}%)
                    </span>
                </span>
            </div>
            {isLoadingActuals ? (
                <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal text-voxel-muted animate-pulse">
                    Loading individual actual portfolio returns...
                </div>
            ) : actualsError ? (
                <div className="pl-3 border-l-2 border-danger text-xs font-normal text-danger">
                    Failed to load constituent portfolio returns ({actualsError}).
                </div>
            ) : actualReturns && Object.keys(actualReturns).length > 0 ? (
                <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal text-voxel-muted flex flex-col gap-1">
                    <div className="text-sm font-bold uppercase tracking-wider text-voxel-ink">
                        Constituent Portfolios (Actual Returns for the Week):
                    </div>
                    {Object.entries(actualReturns).map(([ownerId, retData]) => (
                        <div key={ownerId} className="flex justify-between pl-1">
                            <span>● {getAgentDisplayName(ownerId)}</span>
                            <span className="text-voxel-ink">
                                {(retData.actualReturn * multiplier).toFixed(4)}%{' '}
                                <span className="opacity-70 text-xs text-voxel-muted">
                                    (Base: {formatVal(retData.actualReturn)})
                                </span>
                            </span>
                        </div>
                    ))}
                </div>
            ) : isPending ? (
                <div className="pl-3 border-l-2 border-amber-800/60 text-xs font-normal text-amber-400 italic">
                    Trading session in progress — returns will accumulate upon daily market closing
                    settlement (4:00 PM ET).
                </div>
            ) : (
                <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal text-voxel-muted italic">
                    No constituent portfolio actuals available (live/simulated).
                </div>
            )}
        </div>
    );
}

function DoNothingSection({
    doNothingReturn,
    multiplier,
    portfolioDetails,
    isPending,
    isActive,
    evaluatedAt,
}: {
    doNothingReturn: number;
    multiplier: number;
    portfolioDetails?: Record<string, PortfolioDetail>;
    isPending?: boolean;
    isActive?: boolean;
    evaluatedAt?: string | null;
}) {
    const details = (portfolioDetails || {}) as Record<string, PortfolioDetail>;
    const detailEntries = Object.entries(details);

    const equationTerms = detailEntries
        .map(([_, d]) => {
            const val = d.do_nothing_return_pct ?? 0;
            return val < 0 ? `(${val.toFixed(4)}%)` : `${val.toFixed(4)}%`;
        })
        .join(' + ');

    return (
        <div className="flex flex-col gap-1.5 border-b border-voxel-bevel-hi/60 pb-3">
            <div className="flex flex-col sm:flex-row sm:justify-between text-sm font-bold text-voxel-ink">
                <span>3. Do-Nothing Return (Average of starting-asset buy-and-hold returns)</span>
                <span>
                    {(doNothingReturn * multiplier).toFixed(4)}%{' '}
                    <span className="text-xs font-normal text-voxel-muted">
                        (Base: {doNothingReturn.toFixed(4)}%)
                    </span>
                </span>
            </div>
            {evaluatedAt && (
                <div className="text-xs font-normal font-mono text-voxel-muted">
                    Audited Settlement: {formatEasternDateTime(evaluatedAt)}
                </div>
            )}
            {detailEntries.length === 0 ? (
                isActive ? (
                    <div className="mt-2 p-3 rounded-none bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs font-normal flex flex-col gap-1">
                        <div className="flex items-center gap-1.5 text-sm font-bold uppercase tracking-wider text-amber-400">
                            <span>⚠️</span>
                            <span>PROVISIONAL LIVE TRACKING BENCHMARK</span>
                        </div>
                        <p className="text-xs font-normal leading-relaxed text-amber-300">
                            The Do-Nothing baseline is provisional (0.0000%) during active trading.
                            Constituent starting holdings and buy-and-hold returns are audited and
                            finalized upon weekly market settlement.
                        </p>
                    </div>
                ) : (
                    <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal text-voxel-muted italic">
                        {isPending
                            ? 'Active variant: starting positions will be audited at the close of the trading period.'
                            : 'No constituent do-nothing details available (live/simulated).'}
                    </div>
                )
            ) : (
                <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal text-voxel-muted flex flex-col gap-1.5">
                    <div className="text-sm font-bold uppercase tracking-wider text-voxel-ink">
                        Base Calculation:
                    </div>
                    <div className="text-voxel-ink">
                        ({equationTerms}) / {detailEntries.length} = {doNothingReturn.toFixed(4)}%
                    </div>
                    <div className="text-sm font-bold uppercase tracking-wider text-voxel-ink pt-1">
                        Constituent Portfolios (Do-Nothing Returns for the Week):
                    </div>
                    {detailEntries.map(([pid, detail]) => {
                        const dnReturn = detail.do_nothing_return_pct ?? 0;
                        return (
                            <div key={pid} className="flex justify-between pl-1">
                                <span>● {getAgentDisplayName(detail.owner_id)}</span>
                                <span className="text-voxel-ink">
                                    {(dnReturn * multiplier).toFixed(4)}%{' '}
                                    <span className="opacity-70 text-xs text-voxel-muted">
                                        (Base: {formatVal(dnReturn)})
                                    </span>
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

export function DailyAuditLedger({
    selectedDayName,
    selectedCp,
    multiplier,
    portfolioReturn,
    spyReturn,
    doNothingReturn,
    bondReturn,
    maxDrawdown,
    dailyExcessReturn,
    opportunityCost,
    dailyDrawdownPenalty,
    dailyScore,
    portfolioDetails,
    actualReturns,
    isLoadingActuals,
    actualsError,
    isPending = false,
    isActive = false,
    evaluatedAt,
    onClose,
}: DailyAuditLedgerProps) {
    return (
        <div className="p-5 rounded-none voxel-card bg-voxel-surface border border-voxel-bevel-hi flex flex-col gap-4 animate-fade-in relative z-10">
            <div className="flex items-center justify-between border-b border-voxel-bevel-hi pb-2">
                <div className="flex flex-col">
                    <h4 className="text-sm font-bold text-voxel-ink flex items-center gap-2">
                        <span className="flex items-center justify-center h-5 w-5 rounded-none bg-emerald-500/10 text-emerald-400 text-xs font-normal">
                            ✓
                        </span>
                        <span>
                            Score Constituents — {selectedDayName}{' '}
                            {selectedCp.dateStr ? `(${selectedCp.dateStr})` : ''}
                        </span>
                    </h4>
                    <p className="text-xs font-normal text-voxel-muted mt-0.5">
                        Scaled values for day progression (multiplier: {multiplier.toFixed(2)})
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex flex-col items-end">
                        <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                            Day Score
                        </div>
                        <div
                            className={`text-sm font-bold font-mono ${selectedCp.score >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}
                        >
                            {selectedCp.score >= 0 ? '+' : ''}
                            {selectedCp.score.toFixed(4)}
                        </div>
                    </div>
                    <Button
                        type="button"
                        variant="outline"
                        colorScheme="neutral"
                        size="sm"
                        onClick={onClose}
                    >
                        Close
                    </Button>
                </div>
            </div>

            <ScaledMetricTiles
                dailyExcessReturn={dailyExcessReturn}
                opportunityCost={opportunityCost}
                dailyDrawdownPenalty={dailyDrawdownPenalty}
                multiplier={multiplier}
            />

            {/* Step-by-step arithmetic */}
            <div className="bg-voxel-trough rounded-none p-4 font-mono text-xs font-normal border border-voxel-bevel-hi leading-relaxed text-voxel-muted flex flex-col gap-4">
                <div className="text-sm font-bold text-voxel-muted uppercase tracking-wider border-b border-voxel-bevel-hi pb-1.5 font-sans">
                    Detailed Audit Ledger
                </div>

                {/* 1. Excess Return */}
                <div className="flex flex-col gap-1.5 border-b border-voxel-bevel-hi/60 pb-3">
                    <div className="text-sm font-bold text-voxel-ink">
                        1. Excess Return Calculation:
                    </div>
                    <div className="text-xs font-normal text-voxel-muted">
                        Formula: 0.4 × (Portfolio - SPY) + 0.4 × (Portfolio - Do-Nothing) + 0.2 ×
                        (Portfolio - 10Y Bond)
                    </div>
                    <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal flex flex-col gap-1">
                        <div className="text-sm font-bold text-voxel-ink">
                            Base Composite Excess Return Calculation:
                        </div>
                        <div className="text-voxel-ink">
                            0.4 × ({formatValWithParentheses(portfolioReturn)} -{' '}
                            {formatValWithParentheses(spyReturn)}) + 0.4 × (
                            {formatValWithParentheses(portfolioReturn)} -{' '}
                            {formatValWithParentheses(doNothingReturn)}) + 0.2 × (
                            {formatValWithParentheses(portfolioReturn)} -{' '}
                            {formatValWithParentheses(bondReturn)}) ={' '}
                            {dailyExcessReturn >= 0 ? '+' : ''}
                            {dailyExcessReturn.toFixed(4)}%
                        </div>
                        <div className="text-sm font-bold text-voxel-ink mt-1">
                            Scaled Excess Return (x {multiplier.toFixed(2)}):
                        </div>
                        <div className="text-voxel-ink">
                            {formatValWithParentheses(portfolioReturn * multiplier)} -{' '}
                            {formatValWithParentheses(spyReturn * multiplier)} + (
                            {formatValWithParentheses(portfolioReturn * multiplier)} -{' '}
                            {formatValWithParentheses(doNothingReturn * multiplier)}) ={' '}
                            {dailyExcessReturn >= 0 ? '+' : ''}
                            {(dailyExcessReturn * multiplier).toFixed(4)}%
                        </div>
                    </div>
                </div>

                <PortfolioReturnSection
                    portfolioReturn={portfolioReturn}
                    multiplier={multiplier}
                    actualReturns={actualReturns}
                    isLoadingActuals={isLoadingActuals}
                    actualsError={actualsError}
                    isPending={isPending}
                />

                <DoNothingSection
                    doNothingReturn={doNothingReturn}
                    multiplier={multiplier}
                    portfolioDetails={portfolioDetails}
                    isPending={isPending}
                    isActive={isActive}
                    evaluatedAt={evaluatedAt}
                />

                {/* 4. Opportunity Cost */}
                <div className="flex flex-col gap-1.5 border-b border-voxel-bevel-hi/60 pb-3">
                    <div className="flex flex-col sm:flex-row sm:justify-between text-sm font-bold text-voxel-ink">
                        <span>4. Opportunity Cost</span>
                        <span>
                            -{(opportunityCost * multiplier).toFixed(4)}%{' '}
                            <span className="text-xs font-normal text-voxel-muted">
                                (Base: -{opportunityCost.toFixed(4)}%)
                            </span>
                        </span>
                    </div>
                </div>

                {/* 5. Risk Penalty */}
                <div className="flex flex-col gap-1.5 border-b border-voxel-bevel-hi/60 pb-3">
                    <div className="flex flex-col sm:flex-row sm:justify-between text-sm font-bold text-voxel-ink">
                        <span>5. Risk Penalty (Max Drawdown * 0.3)</span>
                        <span>
                            -{(dailyDrawdownPenalty * multiplier).toFixed(4)}%{' '}
                            <span className="text-xs font-normal text-voxel-muted">
                                (Base: -{dailyDrawdownPenalty.toFixed(4)}%)
                            </span>
                        </span>
                    </div>
                    <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal text-voxel-muted flex flex-col gap-1">
                        <div className="text-voxel-ink">
                            Base: {maxDrawdown.toFixed(4)}% * 0.3 ={' '}
                            {dailyDrawdownPenalty.toFixed(4)}%
                        </div>
                        <div className="text-voxel-ink">
                            Scaled: {(maxDrawdown * multiplier).toFixed(4)}% * 0.3 ={' '}
                            {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                        </div>
                    </div>
                </div>

                {/* 6. Final Score Assembly */}
                <div className="flex flex-col gap-1.5 pt-1">
                    <div className="text-sm font-bold text-voxel-ink">6. Final Score Assembly:</div>
                    <div className="text-xs font-normal text-voxel-muted">
                        Formula: score = Composite Excess Return - Risk Penalty
                    </div>
                    <div className="pl-3 border-l-2 border-voxel-bevel-hi text-xs font-normal flex flex-col gap-1">
                        <div className="text-emerald-400 font-bold">Base Score Calculation:</div>
                        <div className="text-voxel-ink">
                            score = {dailyExcessReturn.toFixed(4)}% -{' '}
                            {dailyDrawdownPenalty.toFixed(4)}%
                        </div>
                        <div className="text-voxel-ink text-sm font-bold pt-0.5">
                            score = {dailyScore >= 0 ? '+' : ''}
                            {dailyScore.toFixed(4)}
                        </div>

                        <div className="text-emerald-400 font-bold mt-2">
                            Scaled Day Score Calculation:
                        </div>
                        <div className="text-voxel-ink">
                            score = {(dailyExcessReturn * multiplier).toFixed(4)}% -{' '}
                            {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                        </div>
                        <div className="text-emerald-400 text-sm font-bold pt-0.5">
                            score = {selectedCp.score >= 0 ? '+' : ''}
                            {selectedCp.score.toFixed(4)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
