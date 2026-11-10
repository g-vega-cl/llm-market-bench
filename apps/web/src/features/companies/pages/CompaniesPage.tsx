import {
    Badge,
    Card,
    EmptyState,
    Input,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useMemo, useState } from 'react';
import type { CompanySummaryItem } from '../api/fetch-companies';

interface CompaniesPageProps {
    initialCompanies: CompanySummaryItem[];
}

export function CompaniesPage({ initialCompanies }: CompaniesPageProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [verdictFilter, setVerdictFilter] = useState<'all' | 'bullish' | 'neutral' | 'bearish'>(
        'all',
    );

    const filteredCompanies = useMemo(() => {
        return initialCompanies.filter((company) => {
            const matchesQuery =
                !searchQuery ||
                company.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
                company.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                company.sector?.toLowerCase().includes(searchQuery.toLowerCase());

            const matchesVerdict =
                verdictFilter === 'all' || company.latest_verdict === verdictFilter;

            return matchesQuery && matchesVerdict;
        });
    }, [initialCompanies, searchQuery, verdictFilter]);

    return (
        <PageLayout className="py-8" maxWidth="xl">
            <div className="flex flex-col gap-6">
                {/* Header */}
                <div className="flex flex-col gap-2 border-b border-zinc-800 pb-6">
                    <div className="flex items-center gap-2">
                        <Link
                            to="/generated-newsletters"
                            className="text-xs font-normal text-electric-blue-500 hover:underline inline-flex items-center gap-1"
                        >
                            ← Back to Daily Newsletters
                        </Link>
                    </div>
                    <SectionHeading gradient="electric">
                        Company Intelligence & Research Dossiers
                    </SectionHeading>
                    <p className="text-xs font-normal text-zinc-400 max-w-2xl">
                        Deep-dive institutional research evaluating stocks and sectors spotlighted
                        in Benchify's daily briefings. Every dossier includes valuation, Warren
                        Buffett economic moat audits, options volatility, and falsification rules.
                    </p>
                </div>

                {/* Filters & Search Controls */}
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex-1 basis-72 min-w-0">
                        <Input
                            placeholder="Search by ticker, name, or sector (e.g. NVDA, SMH)..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        {(['all', 'bullish', 'neutral', 'bearish'] as const).map((filter) => (
                            <button
                                key={filter}
                                type="button"
                                onClick={() => setVerdictFilter(filter)}
                                className={`px-3 py-1.5 text-sm font-bold uppercase transition-colors rounded-none ${
                                    verdictFilter === filter
                                        ? 'bg-electric-blue-500/20 text-electric-blue-400 border-2 border-electric-blue-500'
                                        : 'bg-zinc-900 text-zinc-400 border border-zinc-800 hover:text-zinc-200'
                                }`}
                            >
                                {filter}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Grid of Company Cards */}
                {filteredCompanies.length === 0 ? (
                    <EmptyState
                        title="No companies found"
                        subtitle={
                            searchQuery
                                ? `No research dossier matching "${searchQuery}". You can look up any ticker directly.`
                                : 'No company research reports generated yet. Briefing mentions will populate here automatically.'
                        }
                    />
                ) : (
                    <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4">
                        {filteredCompanies.map((c) => {
                            const isBull = c.latest_verdict === 'bullish';
                            const isBear = c.latest_verdict === 'bearish';
                            const verdictColor = isBull
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                : isBear
                                  ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30';

                            return (
                                <Link
                                    key={c.ticker}
                                    to="/companies/$ticker"
                                    params={{ ticker: c.ticker }}
                                    className="group block"
                                >
                                    <Card
                                        variant="default"
                                        className="h-full flex flex-col justify-between p-4 transition-transform group-hover:-translate-y-0.5 border border-zinc-800 group-hover:border-electric-blue-500/50"
                                    >
                                        <div className="flex flex-col gap-3">
                                            {/* Ticker & Verdict Row */}
                                            <div className="flex items-center justify-between gap-2">
                                                <div className="flex items-center gap-2 min-w-0">
                                                    <span className="text-lg font-bold text-zinc-100 group-hover:text-electric-blue-400 transition-colors">
                                                        {c.ticker}
                                                    </span>
                                                    {c.is_sector_etf && (
                                                        <Badge variant="outline" size="sm">
                                                            ETF
                                                        </Badge>
                                                    )}
                                                </div>
                                                <span
                                                    className={`px-2 py-0.5 text-sm font-bold uppercase border rounded-none ${verdictColor}`}
                                                >
                                                    {c.latest_verdict} {c.latest_conviction}%
                                                </span>
                                            </div>

                                            {/* Company Name */}
                                            <p className="text-sm font-bold text-zinc-300 truncate">
                                                {c.company_name}
                                            </p>

                                            {/* Sector & Stats */}
                                            {c.sector && (
                                                <p className="text-xs font-normal text-zinc-400 truncate">
                                                    Sector: {c.sector}
                                                </p>
                                            )}
                                        </div>

                                        {/* Bottom Meta Row */}
                                        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-zinc-800/80 pt-3 text-xs font-normal text-zinc-500">
                                            <span>
                                                {c.spot_price_at_report !== null
                                                    ? `$${c.spot_price_at_report.toFixed(2)}`
                                                    : 'Price N/A'}
                                            </span>
                                            <span>
                                                {c.mention_count > 1
                                                    ? `${c.mention_count} briefings`
                                                    : c.formatted_date}
                                            </span>
                                        </div>
                                    </Card>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </div>
        </PageLayout>
    );
}
