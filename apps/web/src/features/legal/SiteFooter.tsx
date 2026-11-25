import { Link } from '@tanstack/react-router';
import { FinancialDisclaimer } from './FinancialDisclaimer';

export function SiteFooter() {
    return (
        <footer className="mt-auto border-t-2 border-voxel-bevel-lo bg-voxel-surface px-6 py-8 text-voxel-muted">
            <div className="mx-auto grid w-full max-w-7xl grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-8 items-start">
                <div className="flex max-w-xl flex-col gap-3">
                    <p className="text-sm font-bold uppercase tracking-wider text-voxel-ink">
                        Benchify
                    </p>
                    <p className="text-xs leading-relaxed">
                        Describe a trading bot, test it on point-in-time news, and see how it holds
                        up. Research and benchmarking only.
                    </p>
                    <FinancialDisclaimer />
                </div>

                <div className="flex flex-col gap-3 text-xs">
                    <p className="text-sm font-bold uppercase tracking-wider text-voxel-ink">
                        Legal
                    </p>
                    <Link to="/privacy" className="w-fit hover:text-accent hover:underline">
                        Privacy Policy
                    </Link>
                    <Link to="/terms" className="w-fit hover:text-accent hover:underline">
                        Terms of Service
                    </Link>
                    <Link to="/disclaimer" className="w-fit hover:text-accent hover:underline">
                        Financial Disclaimer
                    </Link>
                    <p className="max-w-sm leading-relaxed">
                        Analytics notice: we use PostHog, served from our own domain, for page
                        views, clicks, session replay with form inputs masked, and error logs. No
                        advertising cookies. Details in the Privacy Policy.
                    </p>
                </div>
            </div>
        </footer>
    );
}
