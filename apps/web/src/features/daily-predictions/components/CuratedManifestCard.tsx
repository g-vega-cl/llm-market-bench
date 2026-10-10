import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type { ParsedCuratedManifest } from '../utils/daily-predictions-helpers';

export interface CuratedManifestCardProps {
    manifest: ParsedCuratedManifest;
}

export function CuratedManifestCard({ manifest }: CuratedManifestCardProps) {
    const newsletters = manifest.selected_newsletters || [];
    const proxies = manifest.include_macro_proxies || [];

    return (
        <Card className="p-5 rounded-2xl border border-blue-950/40 bg-slate-900/90 text-white shadow-lg mb-6">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-blue-400">
                        📦 Curated Pre-Market Data Manifest
                    </span>
                    <Badge colorScheme="accent" variant="soft" size="xs">
                        LAB CHAMPION
                    </Badge>
                </div>
                <span className="text-xs text-slate-400">
                    Point-in-Time 09:15 AM ET Filtered Input Stream
                </span>
            </div>

            <div className="flex flex-wrap gap-6 text-xs">
                {/* Curated Newsletters */}
                <div className="flex-1 basis-64 min-w-0">
                    <div className="text-slate-400 font-semibold mb-2 uppercase tracking-wider text-[11px]">
                        Active Ingested Newsletters ({newsletters.length})
                    </div>
                    {newsletters.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                            {newsletters.map((nl) => (
                                <Badge key={nl} colorScheme="info" variant="soft" size="xs">
                                    📰 {nl}
                                </Badge>
                            ))}
                        </div>
                    ) : (
                        <span className="text-slate-500 italic">All available newsletters</span>
                    )}
                </div>

                {/* Macro Proxies */}
                <div className="flex-1 basis-48 min-w-0">
                    <div className="text-slate-400 font-semibold mb-2 uppercase tracking-wider text-[11px]">
                        Active Macro Proxies
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {proxies.map((px) => (
                            <Badge key={px} colorScheme="neutral" variant="soft" size="xs">
                                📊 {px}
                            </Badge>
                        ))}
                    </div>
                </div>

                {/* Technical & Pre-Market Signals */}
                <div className="flex-1 basis-64 min-w-0">
                    <div className="text-slate-400 font-semibold mb-2 uppercase tracking-wider text-[11px]">
                        Pre-Market Feature Signals
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {manifest.include_synthetic_newsletter && (
                            <Badge colorScheme="success" variant="soft" size="xs">
                                ⚡ Morning Briefing
                            </Badge>
                        )}
                        {manifest.include_intraday_profile && (
                            <Badge colorScheme="success" variant="soft" size="xs">
                                📈 Prior Day VWAP/CLV
                            </Badge>
                        )}
                        {manifest.include_economic_calendar && (
                            <Badge colorScheme="success" variant="soft" size="xs">
                                🏛️ 8:30 AM Econ Releases
                            </Badge>
                        )}
                        {manifest.include_options_derivatives && (
                            <Badge colorScheme="success" variant="soft" size="xs">
                                🎯 Options Skew
                            </Badge>
                        )}
                    </div>
                </div>
            </div>
        </Card>
    );
}
