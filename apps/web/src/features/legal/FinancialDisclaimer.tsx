import { Link } from '@tanstack/react-router';

export interface FinancialDisclaimerProps {
    compact?: boolean;
    className?: string;
}

const shortText =
    'Benchify is a research and benchmarking tool. Paper trading only. Not financial advice. No returns guaranteed.';

export function FinancialDisclaimer({ compact = false, className = '' }: FinancialDisclaimerProps) {
    if (compact) {
        return (
            <div
                className={`w-full bg-voxel-surface border-b border-voxel-bevel-lo px-4 py-2 text-center text-xs text-voxel-muted ${className}`}
            >
                {shortText}{' '}
                <Link to="/disclaimer" className="font-bold text-accent hover:underline">
                    Learn more
                </Link>
            </div>
        );
    }

    return (
        <div className={`flex flex-col gap-2 ${className}`}>
            <p className="text-xs font-bold uppercase tracking-wider text-voxel-ink">
                Financial disclaimer
            </p>
            <p className="text-xs leading-relaxed text-voxel-muted">
                {shortText} Backtests are simulations, past results do not predict future
                performance, and no content on Benchify is a recommendation to buy or sell a
                security.{' '}
                <Link to="/disclaimer" className="font-bold text-accent hover:underline">
                    Read the full disclaimer
                </Link>
                .
            </p>
        </div>
    );
}
