import { Link } from '@tanstack/react-router';

export interface FinancialDisclaimerProps {
    className?: string;
}

export const FINANCIAL_DISCLAIMER_SHORT_TEXT =
    'Benchify is a research and benchmarking tool. Paper trading only. Not financial advice. No returns guaranteed.';

export function FinancialDisclaimer({ className = '' }: FinancialDisclaimerProps) {
    return (
        <div className={`flex flex-col gap-2 ${className}`}>
            <p className="text-xs font-bold uppercase tracking-wider text-voxel-ink">
                Financial disclaimer
            </p>
            <p className="text-xs leading-relaxed text-voxel-muted">
                {FINANCIAL_DISCLAIMER_SHORT_TEXT} Backtests are simulations, past results do not
                predict future performance, and no content on Benchify is a recommendation to buy or
                sell a security.{' '}
                <Link to="/disclaimer" className="font-bold text-accent hover:underline">
                    Read the full disclaimer
                </Link>
                .
            </p>
        </div>
    );
}
