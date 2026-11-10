import {
    Badge,
    Card,
    EmptyState,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useMemo, useState } from 'react';
import { MarkdownContent } from '~/components/ui/MarkdownContent';
import type { CompanyDossierData, CompanyResearchReport } from '../api/fetch-company-dossier';

interface CompanyDossierPageProps {
    initialData: CompanyDossierData;
}

function getVerdictStyles(verdict: 'bullish' | 'bearish' | 'neutral') {
    if (verdict === 'bullish') {
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
    if (verdict === 'bearish') {
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
    return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
}

function DossierHeader({
    report,
    mentionCount,
}: {
    report: CompanyResearchReport;
    mentionCount: number;
}) {
    const verdictColor = getVerdictStyles(report.verdict);

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-2 border-b border-zinc-800 pb-4">
                <Link
                    to="/companies"
                    className="text-xs font-normal text-electric-blue-500 hover:underline inline-flex items-center gap-1"
                >
                    ← Back to Companies Directory
                </Link>
                <span className="text-xs font-normal text-zinc-500">
                    Featured in {mentionCount} briefing{mentionCount === 1 ? '' : 's'}
                </span>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-zinc-100">{report.ticker}</span>
                    <span className="text-sm font-bold text-zinc-400">{report.company_name}</span>
                    {report.is_sector_etf && (
                        <Badge variant="outline" size="sm">
                            Sector ETF
                        </Badge>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <span
                        className={`px-3 py-1 text-sm font-bold uppercase border rounded-none ${verdictColor}`}
                    >
                        {report.verdict} • {report.conviction_score}% Conviction
                    </span>
                </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs font-normal text-zinc-400">
                {report.sector && (
                    <span>
                        Sector: <strong className="text-zinc-200">{report.sector}</strong>
                    </span>
                )}
                {report.spot_price_at_report !== null && (
                    <span>
                        Spot Price:{' '}
                        <strong className="text-zinc-200">
                            ${report.spot_price_at_report.toFixed(2)}
                        </strong>
                    </span>
                )}
                <span>
                    Target Horizon:{' '}
                    <strong className="text-zinc-200">{report.target_horizon}</strong>
                </span>
                {report.risk_reward_score && (
                    <span>
                        Risk/Reward:{' '}
                        <strong className="text-zinc-200">{report.risk_reward_score}:1</strong>
                    </span>
                )}
                <span>
                    As of:{' '}
                    <strong className="text-zinc-200">
                        {report.formatted_date} ({report.session.toUpperCase()})
                    </strong>
                </span>
            </div>
        </div>
    );
}

function MoatAndValuationGrid({ report }: { report: CompanyResearchReport }) {
    const moat = (report.buffett_moat_analysis || {}) as Record<string, string | undefined>;

    return (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,18rem),1fr))] gap-4">
            <Card variant="default" className="p-4 border border-zinc-800 flex flex-col gap-2">
                <span className="text-sm font-bold uppercase text-zinc-400 tracking-wider">
                    🏰 Economic Moat & Quality
                </span>
                <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-zinc-200">
                        Moat: {moat.moat_rating || 'Unrated'}
                    </span>
                    {moat.pricing_power && (
                        <Badge variant="outline" size="sm">
                            {moat.pricing_power} Pricing Power
                        </Badge>
                    )}
                </div>
                <p className="text-xs font-normal text-zinc-400">
                    {moat.rationale ||
                        moat.summary ||
                        'Economic moat evaluated via ROIC, durable competitive advantages, and pricing elasticity.'}
                </p>
            </Card>

            <Card variant="default" className="p-4 border border-zinc-800 flex flex-col gap-2">
                <span className="text-sm font-bold uppercase text-zinc-400 tracking-wider">
                    📊 Valuation & Multiples
                </span>
                <p className="text-xs font-normal text-zinc-300">
                    {report.valuation_summary ||
                        'Valuation appraisal compiled from balance sheet and earnings multiples.'}
                </p>
            </Card>

            <Card variant="default" className="p-4 border border-zinc-800 flex flex-col gap-2">
                <span className="text-sm font-bold uppercase text-zinc-400 tracking-wider">
                    📈 Options & Volatility Surface
                </span>
                <p className="text-xs font-normal text-zinc-300">
                    {report.options_sentiment_summary ||
                        'Options flow, skew, and IV regime metrics.'}
                </p>
            </Card>
        </div>
    );
}

function HistoricalTimeline({
    latestReport,
    pastReports,
    activeId,
    onSelect,
}: {
    latestReport: CompanyResearchReport;
    pastReports: CompanyResearchReport[];
    activeId: string;
    onSelect: (id: string) => void;
}) {
    if (pastReports.length === 0) return null;

    return (
        <div className="flex flex-col gap-3 border-t border-zinc-800 pt-6">
            <span className="text-sm font-bold text-zinc-200">Historical Research Timeline</span>
            <div className="flex flex-wrap gap-2">
                <button
                    type="button"
                    onClick={() => onSelect(latestReport.id)}
                    className={`px-3 py-1.5 text-sm font-bold rounded-none border transition-colors ${
                        activeId === latestReport.id
                            ? 'bg-electric-blue-500/20 text-electric-blue-400 border-electric-blue-500'
                            : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'
                    }`}
                >
                    Latest: {latestReport.formatted_date} ({latestReport.session.toUpperCase()}) •{' '}
                    {latestReport.verdict}
                </button>
                {pastReports.map((past) => (
                    <button
                        key={past.id}
                        type="button"
                        onClick={() => onSelect(past.id)}
                        className={`px-3 py-1.5 text-sm font-bold rounded-none border transition-colors ${
                            activeId === past.id
                                ? 'bg-electric-blue-500/20 text-electric-blue-400 border-electric-blue-500'
                                : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'
                        }`}
                    >
                        {past.formatted_date} ({past.session.toUpperCase()}) • {past.verdict}
                    </button>
                ))}
            </div>
        </div>
    );
}

export function CompanyDossierPage({ initialData }: CompanyDossierPageProps) {
    const { ticker, latestReport, pastReports, mentionCount } = initialData;
    const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

    const activeReport = useMemo(() => {
        if (!selectedReportId || !latestReport) return latestReport;
        if (latestReport.id === selectedReportId) return latestReport;
        return pastReports.find((r) => r.id === selectedReportId) || latestReport;
    }, [selectedReportId, latestReport, pastReports]);

    if (!activeReport) {
        return (
            <PageLayout className="py-8" maxWidth="xl">
                <div className="flex flex-col gap-6">
                    <Link
                        to="/companies"
                        className="text-xs font-normal text-electric-blue-500 hover:underline"
                    >
                        ← Back to Companies
                    </Link>
                    <EmptyState
                        title={`No Research Dossier for ${ticker}`}
                        subtitle="This ticker has not yet been spotlighted in a daily market briefing. As new newsletters are published, fresh deep-dive research will populate here automatically."
                    />
                </div>
            </PageLayout>
        );
    }

    return (
        <PageLayout className="py-8" maxWidth="xl">
            <div className="flex flex-col gap-6">
                <DossierHeader report={activeReport} mentionCount={mentionCount} />
                <MoatAndValuationGrid report={activeReport} />

                {activeReport.falsification_triggers?.length > 0 && (
                    <Card
                        variant="default"
                        className="p-4 border border-amber-500/20 bg-amber-500/5 flex flex-col gap-2"
                    >
                        <span className="text-sm font-bold uppercase text-amber-400 tracking-wider">
                            ⚠️ Thesis Falsification Criteria (What Breaks This Call)
                        </span>
                        <ul className="flex flex-col gap-1 list-disc list-inside text-xs font-normal text-zinc-300">
                            {activeReport.falsification_triggers.map((trigger) => (
                                <li key={trigger}>{trigger}</li>
                            ))}
                        </ul>
                    </Card>
                )}

                <Card variant="default" className="p-6 border border-zinc-800 flex flex-col gap-4">
                    <SectionHeading gradient="electric">
                        Institutional Research Dossier
                    </SectionHeading>
                    <div className="prose prose-invert max-w-none text-xs font-normal text-zinc-300">
                        <MarkdownContent content={activeReport.full_report_markdown} />
                    </div>
                </Card>

                <HistoricalTimeline
                    latestReport={latestReport ?? activeReport}
                    pastReports={pastReports}
                    activeId={activeReport.id}
                    onSelect={setSelectedReportId}
                />
            </div>
        </PageLayout>
    );
}
