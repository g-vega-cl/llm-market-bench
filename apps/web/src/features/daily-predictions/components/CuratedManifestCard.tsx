import { Badge, Card } from '@llm-market-bench/ui-design-system';
import type { ParsedCuratedManifest } from '../utils/daily-predictions-helpers';

export interface CuratedManifestCardProps {
    manifest: ParsedCuratedManifest;
}

export function CuratedManifestCard({ manifest }: CuratedManifestCardProps) {
    const newsletters = manifest.selected_newsletters || [];
    const proxies = manifest.include_macro_proxies || [];

    return (
        <Card className="p-5 rounded-none border border-blue-950/40 bg-slate-900/90 text-white shadow-lg flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-blue-400">
                        📦 Curated Pre-Market Data Manifest
                    </span>
                    <Badge colorScheme="accent" variant="soft" size="xs" radius="none">
                        LAB CHAMPION
                    </Badge>
                </div>
                <span className="text-xs font-normal text-slate-400">
                    Point-in-Time 09:15 AM ET Filtered Input Stream
                </span>
            </div>

            <div className="flex flex-wrap gap-6 text-xs font-normal">
                {/* Curated Newsletters */}
                <div className="flex-1 basis-64 min-w-0 flex flex-col gap-2">
                    <div className="text-slate-400 font-bold uppercase tracking-wider text-xs">
                        Active Ingested Newsletters ({newsletters.length})
                    </div>
                    {newsletters.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                            {newsletters.map((nl) => (
                                <Badge
                                    key={nl}
                                    colorScheme="info"
                                    variant="soft"
                                    size="xs"
                                    radius="none"
                                >
                                    📰 {nl}
                                </Badge>
                            ))}
                        </div>
                    ) : (
                        <span className="text-slate-500 italic">All available newsletters</span>
                    )}
                </div>

                {/* Macro Proxies */}
                <div className="flex-1 basis-48 min-w-0 flex flex-col gap-2">
                    <div className="text-slate-400 font-bold uppercase tracking-wider text-xs">
                        Active Macro Proxies
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {proxies.map((px) => (
                            <Badge
                                key={px}
                                colorScheme="neutral"
                                variant="soft"
                                size="xs"
                                radius="none"
                            >
                                📊 {px}
                            </Badge>
                        ))}
                    </div>
                </div>

                {/* Technical & Pre-Market Signals */}
                <div className="flex-1 basis-64 min-w-0 flex flex-col gap-2">
                    <div className="text-slate-400 font-bold uppercase tracking-wider text-xs">
                        Pre-Market Feature Signals
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {manifest.include_synthetic_newsletter && (
                            <Badge colorScheme="success" variant="soft" size="xs" radius="none">
                                ⚡ Morning Briefing
                            </Badge>
                        )}
                        {manifest.include_intraday_profile && (
                            <Badge colorScheme="success" variant="soft" size="xs" radius="none">
                                📈 Prior Day VWAP/CLV
                            </Badge>
                        )}
                        {manifest.include_economic_calendar && (
                            <Badge colorScheme="success" variant="soft" size="xs" radius="none">
                                🏛️ 8:30 AM Econ Releases
                            </Badge>
                        )}
                        {manifest.include_options_derivatives && (
                            <Badge colorScheme="success" variant="soft" size="xs" radius="none">
                                🎯 Options Skew
                            </Badge>
                        )}
                    </div>
                </div>
            </div>
        </Card>
    );
}
