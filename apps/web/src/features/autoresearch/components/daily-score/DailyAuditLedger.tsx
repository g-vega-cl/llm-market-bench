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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3 bg-zinc-950/70 border border-zinc-900 rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    Excess Return (Scaled)
                </div>
                <div
                    className={`text-sm font-mono font-bold ${dailyExcessReturn >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}
                >
                    {dailyExcessReturn >= 0 ? '+' : ''}
                    {(dailyExcessReturn * multiplier).toFixed(4)}%
                </div>
                <div className="text-[9px] text-zinc-500 font-mono">
                    Base: {dailyExcessReturn.toFixed(4)}%
                </div>
            </div>

            <div className="p-3 bg-zinc-950/70 border border-zinc-900 rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    Risk-Free Excess (Scaled)
                </div>
                <div
                    className={`text-sm font-mono font-bold ${opportunityCost >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                >
                    {opportunityCost >= 0 ? '+' : ''}
                    {(opportunityCost * multiplier).toFixed(4)}%
                </div>
                <div className="text-[9px] text-zinc-500 font-mono">
                    Base: {opportunityCost >= 0 ? '+' : ''}
                    {opportunityCost.toFixed(4)}%
                </div>
            </div>

            <div className="p-3 bg-zinc-950/70 border border-zinc-900 rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                    Risk Penalty (Scaled)
                </div>
                <div className="text-sm font-mono font-bold text-rose-400">
                    -{(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                </div>
                <div className="text-[9px] text-zinc-500 font-mono">
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
}: {
    portfolioReturn: number;
    multiplier: number;
    actualReturns?: ActualReturns | null;
    isLoadingActuals?: boolean;
}) {
    return (
        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
            <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                <span>2. Portfolio Return (Compounded equal-weighted daily returns of agents)</span>
                <span>
                    {(portfolioReturn * multiplier).toFixed(4)}%{' '}
                    <span className="text-[10px] font-normal text-zinc-500">
                        (Base: {portfolioReturn.toFixed(4)}%)
                    </span>
                </span>
            </div>
            {actualReturns && Object.keys(actualReturns).length > 0 ? (
                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 space-y-1">
                    <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-400">
                        Constituent Portfolios (Actual Returns for the Week):
                    </div>
                    {Object.entries(actualReturns).map(([ownerId, retData]) => (
                        <div key={ownerId} className="flex justify-between pl-1">
                            <span>● {getAgentDisplayName(ownerId)}</span>
                            <span className="text-zinc-300">
                                {(retData.actualReturn * multiplier).toFixed(4)}%{' '}
                                <span className="opacity-70 text-[9px] text-zinc-500">
                                    (Base: {formatVal(retData.actualReturn)})
                                </span>
                            </span>
                        </div>
                    ))}
                </div>
            ) : isLoadingActuals ? (
                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 animate-pulse">
                    Loading individual actual portfolio returns...
                </div>
            ) : (
                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-600 italic">
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
}: {
    doNothingReturn: number;
    multiplier: number;
    portfolioDetails?: Record<string, PortfolioDetail>;
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
        <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
            <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                <span>3. Do-Nothing Return (Average of starting-asset buy-and-hold returns)</span>
                <span>
                    {(doNothingReturn * multiplier).toFixed(4)}%{' '}
                    <span className="text-[10px] font-normal text-zinc-500">
                        (Base: {doNothingReturn.toFixed(4)}%)
                    </span>
                </span>
            </div>
            {detailEntries.length === 0 ? (
                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-600 italic">
                    No constituent do-nothing details available (live/simulated).
                </div>
            ) : (
                <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 space-y-1.5">
                    <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-400">
                        Base Calculation:
                    </div>
                    <div className="text-zinc-300">
                        ({equationTerms}) / {detailEntries.length} = {doNothingReturn.toFixed(4)}%
                    </div>
                    <div className="font-bold text-[9px] uppercase tracking-wider text-zinc-400 pt-1">
                        Constituent Portfolios (Do-Nothing Returns for the Week):
                    </div>
                    {detailEntries.map(([pid, detail]) => {
                        const dnReturn = detail.do_nothing_return_pct ?? 0;
                        return (
                            <div key={pid} className="flex justify-between pl-1">
                                <span>● {getAgentDisplayName(detail.owner_id)}</span>
                                <span className="text-zinc-300">
                                    {(dnReturn * multiplier).toFixed(4)}%{' '}
                                    <span className="opacity-70 text-[9px] text-zinc-500">
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
    onClose,
}: DailyAuditLedgerProps) {
    return (
        <div className="p-5 rounded-2xl bg-zinc-950/50 border border-zinc-800 space-y-4 animate-fade-in relative z-10">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                <div className="flex flex-col">
                    <h4 className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                        <span className="flex items-center justify-center h-5 w-5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-black">
                            ✓
                        </span>
                        <span>
                            Score Constituents — {selectedDayName}{' '}
                            {selectedCp.dateStr ? `(${selectedCp.dateStr})` : ''}
                        </span>
                    </h4>
                    <p className="text-[10px] text-zinc-500 mt-0.5">
                        Scaled values for day progression (multiplier: {multiplier.toFixed(2)})
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex flex-col items-end">
                        <div className="text-[8px] font-black text-zinc-500 uppercase tracking-widest">
                            Day Score
                        </div>
                        <div
                            className={`text-base font-black font-mono ${selectedCp.score >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}
                        >
                            {selectedCp.score >= 0 ? '+' : ''}
                            {selectedCp.score.toFixed(4)}
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="text-zinc-400 hover:text-zinc-200 text-xs font-bold px-2 py-1 bg-zinc-900 border border-zinc-800 rounded hover:border-zinc-700 transition cursor-pointer"
                    >
                        Close
                    </button>
                </div>
            </div>

            <ScaledMetricTiles
                dailyExcessReturn={dailyExcessReturn}
                opportunityCost={opportunityCost}
                dailyDrawdownPenalty={dailyDrawdownPenalty}
                multiplier={multiplier}
            />

            {/* Step-by-step arithmetic */}
            <div className="bg-zinc-950/80 rounded-xl p-4 font-mono text-[11px] border border-zinc-900 leading-relaxed text-zinc-400 space-y-4">
                <div className="text-zinc-500 text-[9px] uppercase font-bold tracking-wider border-b border-zinc-900 pb-1.5 font-sans">
                    Detailed Audit Ledger
                </div>

                {/* 1. Excess Return */}
                <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                    <div className="font-bold text-zinc-200">1. Excess Return Calculation:</div>
                    <div className="text-[10px] text-zinc-500">
                        Formula: 0.4 × (Portfolio - SPY) + 0.4 × (Portfolio - Do-Nothing) + 0.2 ×
                        (Portfolio - 10Y Bond)
                    </div>
                    <div className="pl-3 border-l-2 border-zinc-800 text-[10px] space-y-1">
                        <div className="text-zinc-400 font-bold">
                            Base Composite Excess Return Calculation:
                        </div>
                        <div className="text-zinc-300">
                            0.4 × ({formatValWithParentheses(portfolioReturn)} -{' '}
                            {formatValWithParentheses(spyReturn)}) + 0.4 × (
                            {formatValWithParentheses(portfolioReturn)} -{' '}
                            {formatValWithParentheses(doNothingReturn)}) + 0.2 × (
                            {formatValWithParentheses(portfolioReturn)} -{' '}
                            {formatValWithParentheses(bondReturn)}) ={' '}
                            {dailyExcessReturn >= 0 ? '+' : ''}
                            {dailyExcessReturn.toFixed(4)}%
                        </div>
                        <div className="text-zinc-400 font-bold mt-1">
                            Scaled Excess Return (x {multiplier.toFixed(2)}):
                        </div>
                        <div className="text-zinc-300">
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
                />

                <DoNothingSection
                    doNothingReturn={doNothingReturn}
                    multiplier={multiplier}
                    portfolioDetails={portfolioDetails}
                />

                {/* 4. Opportunity Cost */}
                <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                    <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                        <span>4. Opportunity Cost</span>
                        <span>
                            -{(opportunityCost * multiplier).toFixed(4)}%{' '}
                            <span className="text-[10px] font-normal text-zinc-500">
                                (Base: -{opportunityCost.toFixed(4)}%)
                            </span>
                        </span>
                    </div>
                </div>

                {/* 5. Risk Penalty */}
                <div className="space-y-1.5 border-b border-zinc-900/60 pb-3">
                    <div className="flex flex-col sm:flex-row sm:justify-between font-bold text-zinc-200">
                        <span>5. Risk Penalty (Max Drawdown * 0.3)</span>
                        <span>
                            -{(dailyDrawdownPenalty * multiplier).toFixed(4)}%{' '}
                            <span className="text-[10px] font-normal text-zinc-500">
                                (Base: -{dailyDrawdownPenalty.toFixed(4)}%)
                            </span>
                        </span>
                    </div>
                    <div className="pl-3 border-l-2 border-zinc-800 text-[10px] text-zinc-500 space-y-1">
                        <div className="text-zinc-300">
                            Base: {maxDrawdown.toFixed(4)}% * 0.3 ={' '}
                            {dailyDrawdownPenalty.toFixed(4)}%
                        </div>
                        <div className="text-zinc-300">
                            Scaled: {(maxDrawdown * multiplier).toFixed(4)}% * 0.3 ={' '}
                            {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                        </div>
                    </div>
                </div>

                {/* 6. Final Score Assembly */}
                <div className="space-y-1.5 pt-1">
                    <div className="font-bold text-zinc-200">6. Final Score Assembly:</div>
                    <div className="text-[10px] text-zinc-500">
                        Formula: score = Composite Excess Return - Risk Penalty
                    </div>
                    <div className="pl-3 border-l-2 border-zinc-800 text-[10px]">
                        <div className="text-emerald-400 font-bold">Base Score Calculation:</div>
                        <div className="text-zinc-300 font-bold">
                            score = {dailyExcessReturn.toFixed(4)}% -{' '}
                            {dailyDrawdownPenalty.toFixed(4)}%
                        </div>
                        <div className="text-zinc-300 font-bold text-xs pt-0.5">
                            score = {dailyScore >= 0 ? '+' : ''}
                            {dailyScore.toFixed(4)}
                        </div>

                        <div className="text-emerald-400 font-bold mt-2">
                            Scaled Day Score Calculation:
                        </div>
                        <div className="text-zinc-300 font-bold">
                            score = {(dailyExcessReturn * multiplier).toFixed(4)}% -{' '}
                            {(dailyDrawdownPenalty * multiplier).toFixed(4)}%
                        </div>
                        <div className="text-emerald-400 font-bold text-xs pt-0.5">
                            score = {selectedCp.score >= 0 ? '+' : ''}
                            {selectedCp.score.toFixed(4)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
