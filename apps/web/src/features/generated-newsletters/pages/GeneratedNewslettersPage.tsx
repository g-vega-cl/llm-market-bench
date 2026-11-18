import {
    Badge,
    Button,
    Card,
    EmptyState,
    PageLayout,
    SectionHeading,
} from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { useMemo, useState } from 'react';
import { InlineMarkdown, MarkdownContent } from '~/components/ui/MarkdownContent';
import type { FormattedGeneratedNewsletter } from '../api/fetch-generated-newsletters';

interface GeneratedNewslettersPageProps {
    initialNewsletters: FormattedGeneratedNewsletter[];
}

export function GeneratedNewslettersPage({ initialNewsletters }: GeneratedNewslettersPageProps) {
    const [selectedSession, setSelectedSession] = useState<'all' | 'open' | 'close'>('all');
    const [selectedId, setSelectedId] = useState<string | null>(
        initialNewsletters.length > 0 ? initialNewsletters[0].id : null,
    );

    const filteredNewsletters = useMemo(() => {
        if (selectedSession === 'all') return initialNewsletters;
        return initialNewsletters.filter((n) => n.session === selectedSession);
    }, [initialNewsletters, selectedSession]);

    const activeNewsletter = useMemo(() => {
        if (!filteredNewsletters.length) return null;
        if (!selectedId) return filteredNewsletters[0];
        return filteredNewsletters.find((n) => n.id === selectedId) || filteredNewsletters[0];
    }, [filteredNewsletters, selectedId]);

    const parsedBullets = useMemo(() => {
        if (!activeNewsletter?.bullet_points) return [];
        if (Array.isArray(activeNewsletter.bullet_points)) {
            return activeNewsletter.bullet_points as string[];
        }
        return [];
    }, [activeNewsletter]);

    const spotlightCompanies = useMemo(() => {
        return activeNewsletter?.spotlight_companies || [];
    }, [activeNewsletter]);

    return (
        <PageLayout className="py-8 space-y-8" maxWidth="xl">
            {/* Header section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-voxel-bevel-hi pb-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-4">
                        <Link
                            to="/today"
                            className="text-sm font-bold text-info hover:underline inline-flex items-center gap-1"
                        >
                            ← Back to Today's Dashboard
                        </Link>
                        <span className="text-voxel-muted">•</span>
                        <Link
                            to="/companies"
                            className="text-sm font-bold text-info hover:underline inline-flex items-center gap-1"
                        >
                            Explore Company Dossiers →
                        </Link>
                    </div>
                    <SectionHeading>Daily Market Intelligence Briefings</SectionHeading>
                    <p className="text-sm text-voxel-muted max-w-2xl font-normal">
                        Synthesized ~6 minute reads based on ingested daily newsletters, generated
                        twice daily at market open (09:12 ET) and market close (17:00 ET).
                    </p>
                </div>

                {/* Session filter tabs */}
                <div className="flex items-center gap-1.5 p-1.5 bg-voxel-trough border border-voxel-bevel-hi rounded-none self-start md:self-auto">
                    <Button
                        type="button"
                        variant={selectedSession === 'all' ? 'solid' : 'outline'}
                        colorScheme={selectedSession === 'all' ? 'accent' : 'neutral'}
                        size="sm"
                        onClick={() => {
                            setSelectedSession('all');
                            if (initialNewsletters.length) setSelectedId(initialNewsletters[0].id);
                        }}
                    >
                        All Briefings
                    </Button>
                    <Button
                        type="button"
                        variant={selectedSession === 'open' ? 'solid' : 'outline'}
                        colorScheme={selectedSession === 'open' ? 'accent' : 'neutral'}
                        size="sm"
                        onClick={() => {
                            setSelectedSession('open');
                            const firstOpen = initialNewsletters.find((n) => n.session === 'open');
                            if (firstOpen) setSelectedId(firstOpen.id);
                        }}
                        className="flex items-center gap-1"
                    >
                        🌅 Open (09:12 ET)
                    </Button>
                    <Button
                        type="button"
                        variant={selectedSession === 'close' ? 'solid' : 'outline'}
                        colorScheme={selectedSession === 'close' ? 'accent' : 'neutral'}
                        size="sm"
                        onClick={() => {
                            setSelectedSession('close');
                            const firstClose = initialNewsletters.find(
                                (n) => n.session === 'close',
                            );
                            if (firstClose) setSelectedId(firstClose.id);
                        }}
                        className="flex items-center gap-1"
                    >
                        🌆 Close (17:00 ET)
                    </Button>
                </div>
            </div>

            {/* Empty state when no newsletters exist */}
            {!filteredNewsletters.length ? (
                <EmptyState
                    emoji="🗞️"
                    title="No generated newsletters available yet"
                    subtitle="Daily briefings are automatically synthesized at 09:12 ET (Market Open) and 17:00 ET (Market Close)."
                    actions={[
                        {
                            label: 'Back to Today',
                            href: '/today',
                        },
                    ]}
                />
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                    {/* Left Sidebar: Timeline of generated briefings */}
                    <div className="lg:col-span-4 flex flex-col gap-3">
                        <div className="flex items-center justify-between px-1">
                            <span className="text-sm font-bold text-voxel-muted uppercase tracking-wider">
                                Archive ({filteredNewsletters.length})
                            </span>
                            <span className="text-xs font-normal text-voxel-muted font-mono">
                                DeepSeek V4 Flash
                            </span>
                        </div>

                        <div className="flex flex-col gap-2.5 max-h-[700px] overflow-y-auto pr-1">
                            {filteredNewsletters.map((newsletter) => {
                                const isSelected = activeNewsletter?.id === newsletter.id;
                                const isOpenSession = newsletter.session === 'open';

                                return (
                                    <Button
                                        type="button"
                                        key={newsletter.id}
                                        variant="outline"
                                        colorScheme={isSelected ? 'accent' : 'neutral'}
                                        onClick={() => setSelectedId(newsletter.id)}
                                        className="w-full p-4 text-left flex flex-col items-stretch gap-2"
                                    >
                                        <div className="flex items-center justify-between gap-2">
                                            <Badge
                                                variant="soft"
                                                colorScheme={isOpenSession ? 'accent' : 'warning'}
                                                size="xs"
                                                className="uppercase text-sm font-bold"
                                            >
                                                {isOpenSession
                                                    ? '🌅 Market Open'
                                                    : '🌆 Market Close'}
                                            </Badge>
                                            <span className="text-xs font-normal text-voxel-muted font-mono tabular-nums">
                                                {newsletter.displayTime}
                                            </span>
                                        </div>

                                        <h4 className="text-sm font-bold text-voxel-ink line-clamp-2 leading-snug">
                                            <InlineMarkdown text={newsletter.title} />
                                        </h4>

                                        <p className="text-sm text-voxel-muted line-clamp-2 font-normal">
                                            <InlineMarkdown text={newsletter.summary} />
                                        </p>

                                        <div className="flex items-center justify-between text-xs font-normal text-voxel-muted pt-1 border-t border-voxel-bevel-lo">
                                            <span>{newsletter.formattedDate}</span>
                                            <span>
                                                ⏱️ {newsletter.read_time_minutes ?? 6} min read
                                            </span>
                                        </div>
                                    </Button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Right Spotlight: Selected Newsletter Full View */}
                    {activeNewsletter && (
                        <div className="lg:col-span-8 flex flex-col gap-6">
                            <Card className="p-6 md:p-8 flex flex-col gap-6 rounded-none shadow-sm relative overflow-hidden border-voxel-bevel-hi">
                                {/* Side Accent Line */}
                                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-electric-blue-500 via-deep-purple-500 to-electric-blue-600" />

                                {/* Header badges & Meta */}
                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-voxel-bevel-hi pb-4">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <Badge
                                            variant="solid"
                                            colorScheme={
                                                activeNewsletter.session === 'open'
                                                    ? 'accent'
                                                    : 'warning'
                                            }
                                            size="sm"
                                        >
                                            {activeNewsletter.session === 'open'
                                                ? '🌅 Market Open Briefing'
                                                : '🌆 Market Close Briefing'}
                                        </Badge>
                                        <span className="px-2.5 py-1 rounded-none text-xs font-mono bg-voxel-trough text-voxel-ink border border-voxel-bevel-hi">
                                            🕒 Created at {activeNewsletter.displayTime}
                                        </span>
                                        <span className="px-2.5 py-1 rounded-none text-xs font-normal bg-voxel-trough text-info border border-voxel-bevel-hi">
                                            ⏱️ {activeNewsletter.read_time_minutes ?? 6} min read
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Link
                                            to="/chat"
                                            search={{
                                                q: `Analyze market newsletter briefing "${activeNewsletter.title}": ${activeNewsletter.summary.slice(0, 150)}...`,
                                            }}
                                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-none text-sm font-bold bg-accent hover:bg-accent/90 text-voxel-trough shadow-sm transition-all"
                                            title="Discuss this briefing in AI Chat Gateway"
                                        >
                                            <span>💬</span>
                                            <span>Discuss in AI Chat</span>
                                        </Link>
                                        <span className="text-xs font-normal text-voxel-muted font-mono">
                                            {activeNewsletter.formattedDate}
                                        </span>
                                    </div>
                                </div>

                                {/* Newsletter Title */}
                                <div>
                                    <h1 className="text-sm font-bold text-voxel-ink tracking-tight leading-tight">
                                        <InlineMarkdown text={activeNewsletter.title} />
                                    </h1>
                                </div>

                                {/* Executive Summary Banner */}
                                <div className="p-4 rounded-none bg-voxel-trough border border-voxel-bevel-hi flex flex-col gap-1.5">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm">⚡</span>
                                        <span className="text-sm font-bold uppercase tracking-wider text-info">
                                            Executive Summary
                                        </span>
                                    </div>
                                    <p className="text-xs font-normal text-voxel-ink leading-relaxed">
                                        <InlineMarkdown text={activeNewsletter.summary} />
                                    </p>
                                </div>

                                {/* Key Bullet Highlights */}
                                {parsedBullets.length > 0 && (
                                    <div className="flex flex-col gap-3 p-4 rounded-none bg-voxel-trough border border-voxel-bevel-hi">
                                        <h3 className="text-sm font-bold uppercase tracking-wider text-voxel-muted flex items-center gap-2">
                                            📌 Key Takeaways
                                        </h3>
                                        <ul className="flex flex-col gap-2">
                                            {parsedBullets.map((bullet) => (
                                                <li
                                                    key={bullet}
                                                    className="text-xs text-voxel-ink font-normal flex items-start gap-2.5 leading-relaxed"
                                                >
                                                    <span className="text-info font-bold mt-0.5">
                                                        •
                                                    </span>
                                                    <span className="flex-1">
                                                        <InlineMarkdown
                                                            text={bullet.replace(/^[-*•]\s+/, '')}
                                                        />
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Spotlighted Company & Sector Research */}
                                {spotlightCompanies.length > 0 && (
                                    <div className="flex flex-col gap-3 p-4 rounded-none bg-voxel-trough border border-voxel-bevel-hi">
                                        <div className="flex items-center justify-between gap-2 border-b border-voxel-bevel-hi pb-2">
                                            <h3 className="text-sm font-bold uppercase tracking-wider text-voxel-ink flex items-center gap-2">
                                                <span>🔬</span>
                                                <span>Spotlighted Company & Sector Research</span>
                                                <span className="text-voxel-muted font-mono font-normal">
                                                    ({spotlightCompanies.length})
                                                </span>
                                            </h3>
                                            <Link
                                                to="/companies"
                                                className="text-sm font-bold text-info hover:underline"
                                            >
                                                All Dossiers →
                                            </Link>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {spotlightCompanies.map((company) => {
                                                const isBullish = company.verdict === 'bullish';
                                                const isBearish = company.verdict === 'bearish';
                                                const verdictColor = isBullish
                                                    ? 'accent'
                                                    : isBearish
                                                      ? 'warning'
                                                      : 'neutral';

                                                return (
                                                    <div
                                                        key={company.id || company.ticker}
                                                        className="p-3.5 rounded-none bg-voxel-surface border border-voxel-bevel-hi flex flex-col gap-2.5 transition-all hover:border-voxel-muted"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div className="min-w-0">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-bold text-voxel-ink tracking-tight">
                                                                        {company.ticker}
                                                                    </span>
                                                                    {company.is_sector_etf && (
                                                                        <Badge
                                                                            variant="soft"
                                                                            size="xs"
                                                                            colorScheme="neutral"
                                                                        >
                                                                            ETF
                                                                        </Badge>
                                                                    )}
                                                                </div>
                                                                <div className="text-xs font-normal text-voxel-muted truncate">
                                                                    {company.company_name}
                                                                    {company.sector
                                                                        ? ` • ${company.sector}`
                                                                        : ''}
                                                                </div>
                                                            </div>

                                                            <Badge
                                                                variant="solid"
                                                                size="xs"
                                                                colorScheme={verdictColor}
                                                                className="uppercase font-bold tracking-wider shrink-0"
                                                            >
                                                                {company.verdict}
                                                            </Badge>
                                                        </div>

                                                        <div className="flex items-center gap-3 text-xs font-mono text-voxel-muted pt-1 border-t border-voxel-bevel-lo">
                                                            <span className="font-bold text-voxel-ink">
                                                                {company.conviction_score}%
                                                                Conviction
                                                            </span>
                                                            {company.spot_price_at_report !=
                                                                null && (
                                                                <span>
                                                                    Spot: $
                                                                    {company.spot_price_at_report.toFixed(
                                                                        2,
                                                                    )}
                                                                </span>
                                                            )}
                                                            {company.risk_reward_score != null && (
                                                                <span>
                                                                    R/R: {company.risk_reward_score}
                                                                    x
                                                                </span>
                                                            )}
                                                        </div>

                                                        {company.catalyst_context && (
                                                            <p className="text-xs font-normal text-voxel-muted line-clamp-2 leading-relaxed">
                                                                {company.catalyst_context}
                                                            </p>
                                                        )}

                                                        <div className="pt-2 border-t border-voxel-bevel-lo mt-auto">
                                                            <Link
                                                                to="/companies/$ticker"
                                                                params={{ ticker: company.ticker }}
                                                                className="text-sm font-bold text-electric-blue-500 hover:underline inline-flex items-center gap-1"
                                                            >
                                                                View Full Dossier →
                                                            </Link>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* Main Newsletter Body Content */}
                                <div className="pt-4 border-t border-voxel-bevel-hi">
                                    <MarkdownContent content={activeNewsletter.content} />
                                </div>

                                {/* Footer metadata */}
                                <div className="pt-6 border-t border-voxel-bevel-hi flex items-center justify-between text-xs font-normal text-voxel-muted font-mono">
                                    <span>
                                        Sources Ingested: {activeNewsletter.source_count ?? 0}{' '}
                                        Briefings
                                    </span>
                                    <span>Powered by DeepSeek V4 Flash</span>
                                </div>
                            </Card>
                        </div>
                    )}
                </div>
            )}
        </PageLayout>
    );
}
