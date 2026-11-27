import { Badge } from '@llm-market-bench/ui-design-system';

/** Single source of truth for the studio + backtest data-coverage disclosure. */
export const US_DATA_COVERAGE_COPY =
    'Benchify has US-listed stocks only. Tickers are validated as 1–5 characters; non-US markets such as NSE/Nifty 100 (RELIANCE, HDFCBANK) have no price history in backtests or live runs, so those strategies place no trades.';

export function DataCoverageNote() {
    return (
        <div
            role="note"
            data-testid="data-coverage-note"
            className="voxel-trough bg-voxel-trough border border-voxel-bevel-lo rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <Badge colorScheme="neutral" variant="soft" size="sm">
                DATA COVERAGE
            </Badge>
            <p className="text-xs font-normal text-voxel-muted leading-relaxed break-words min-w-0">
                {US_DATA_COVERAGE_COPY}
            </p>
        </div>
    );
}
