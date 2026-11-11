import {
    Badge,
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
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-4">
                        <Link
                            to="/today"
                            className="text-sm font-bold text-electric-blue-500 hover:underline inline-flex items-center gap-1"
                        >
                            ← Back to Today's Dashboard
                        </Link>
                        <span className="text-zinc-600">•</span>
                        <Link
                            to="/companies"
                            className="text-sm font-bold text-electric-blue-500 hover:underline inline-flex items-center gap-1"
                        >
                            Explore Company Dossiers →
                        </Link>
                    </div>
                    <SectionHeading gradient="electric">
                        Daily Market Intelligence Briefings
                    </SectionHeading>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl font-light">
                        Synthesized ~6 minute reads based on ingested daily newsletters, generated
                        twice daily at market open (09:12 ET) and market close (17:00 ET).
                    </p>
                </div>

                {/* Session filter tabs */}
                <div className="flex items-center gap-1.5 p-1.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-none self-start md:self-auto">
                    <button
                        type="button"
                        onClick={() => {
                            setSelectedSession('all');
                            if (initialNewsletters.length) setSelectedId(initialNewsletters[0].id);
                        }}
                        className={`px-3 py-1.5 rounded-none text-xs font-bold transition-all ${
                            selectedSession === 'all'
                                ? 'bg-white dark:bg-zinc-800 text-zinc-900 dark:text-white shadow-sm'
                                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                        }`}
                    >
                        All Briefings
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setSelectedSession('open');
                            const firstOpen = initialNewsletters.find((n) => n.session === 'open');
                            if (firstOpen) setSelectedId(firstOpen.id);
                        }}
                        className={`px-3 py-1.5 rounded-none text-xs font-bold transition-all flex items-center gap-1 ${
                            selectedSession === 'open'
                                ? 'bg-electric-blue-500 text-white shadow-sm'
                                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                        }`}
                    >
                        🌅 Open (09:12 ET)
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setSelectedSession('close');
                            const firstClose = initialNewsletters.find(
                                (n) => n.session === 'close',
                            );
                            if (firstClose) setSelectedId(firstClose.id);
                        }}
                        className={`px-3 py-1.5 rounded-none text-xs font-bold transition-all flex items-center gap-1 ${
                            selectedSession === 'close'
                                ? 'bg-deep-purple-500 text-white shadow-sm'
                                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                        }`}
                    >
                        🌆 Close (17:00 ET)
                    </button>
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
                            <span className="text-xs font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                                Archive ({filteredNewsletters.length})
                            </span>
                            <span className="text-xs font-normal text-zinc-400 font-mono">
                                DeepSeek V4 Flash
                            </span>
                        </div>

                        <div className="flex flex-col gap-2.5 max-h-[700px] overflow-y-auto pr-1">
                            {filteredNewsletters.map((newsletter) => {
                                const isSelected = activeNewsletter?.id === newsletter.id;
                                const isOpenSession = newsletter.session === 'open';

                                return (
                                    <button
                                        type="button"
                                        key={newsletter.id}
                                        onClick={() => setSelectedId(newsletter.id)}
                                        className={`w-full p-4 rounded-none border transition-all cursor-pointer text-left flex flex-col gap-2 ${
                                            isSelected
                                                ? 'bg-electric-blue-50/40 dark:bg-electric-blue-950/20 border-electric-blue-500/50 ring-1 ring-electric-blue-500/30'
                                                : 'bg-white dark:bg-zinc-900/60 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700'
                                        }`}
                                    >
                                        <div className="flex items-center justify-between gap-2">
                                            <Badge
                                                variant="soft"
                                                colorScheme={isOpenSession ? 'accent' : 'warning'}
                                                size="xs"
                                                radius="none"
                                                className="uppercase text-xs font-bold"
                                            >
                                                {isOpenSession
                                                    ? '🌅 Market Open'
                                                    : '🌆 Market Close'}
                                            </Badge>
                                            <span className="text-xs font-normal text-zinc-400 font-mono tabular-nums">
                                                {newsletter.displayTime}
                                            </span>
                                        </div>

                                        <h4 className="text-sm font-bold text-zinc-900 dark:text-white line-clamp-2 leading-snug">
                                            <InlineMarkdown text={newsletter.title} />
                                        </h4>

                                        <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 font-normal">
                                            <InlineMarkdown text={newsletter.summary} />
                                        </p>

                                        <div className="flex items-center justify-between text-xs font-normal text-zinc-400 pt-1 border-t border-zinc-100 dark:border-zinc-800/80">
                                            <span>{newsletter.formattedDate}</span>
                                            <span>
                                                ⏱️ {newsletter.read_time_minutes ?? 6} min read
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Right Spotlight: Selected Newsletter Full View */}
                    {activeNewsletter && (
                        <div className="lg:col-span-8 flex flex-col gap-6">
                            <Card className="p-6 md:p-8 flex flex-col gap-6 rounded-none shadow-sm relative overflow-hidden border-electric-blue-100 dark:border-electric-blue-900/30">
                                {/* Side Accent Line */}
                                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-electric-blue-500 via-deep-purple-500 to-electric-blue-600" />

                                {/* Header badges & Meta */}
                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <Badge
                                            variant="solid"
                                            radius="none"
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
                                        <span className="px-2.5 py-1 rounded-none text-xs font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                                            🕒 Created at {activeNewsletter.displayTime}
                                        </span>
                                        <span className="px-2.5 py-1 rounded-none text-xs font-normal bg-electric-blue-50 dark:bg-electric-blue-950/40 text-electric-blue-600 dark:text-electric-blue-400 border border-electric-blue-200 dark:border-electric-blue-800/50">
                                            ⏱️ {activeNewsletter.read_time_minutes ?? 6} min read
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <Link
                                            to="/chat"
                                            search={{
                                                q: `Analyze market newsletter briefing "${activeNewsletter.title}": ${activeNewsletter.summary.slice(0, 150)}...`,
                                            }}
                                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-none text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm transition-all"
                                            title="Discuss this briefing in AI Chat Gateway"
                                        >
                                            <span>💬</span>
                                            <span>Discuss in AI Chat</span>
                                        </Link>
                                        <span className="text-xs font-normal text-zinc-400 font-mono">
                                            {activeNewsletter.formattedDate}
                                        </span>
                                    </div>
                                </div>

                                {/* Newsletter Title */}
                                <div>
                                    <h1 className="text-lg font-bold text-zinc-900 dark:text-white tracking-tight leading-tight">
                                        <InlineMarkdown text={activeNewsletter.title} />
                                    </h1>
                                </div>

                                {/* Executive Summary Banner */}
                                <div className="p-4 rounded-none bg-electric-blue-50/60 dark:bg-electric-blue-950/20 border border-electric-blue-200/60 dark:border-electric-blue-900/40 flex flex-col gap-1.5">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm">⚡</span>
                                        <span className="text-xs font-bold uppercase tracking-wider text-electric-blue-600 dark:text-electric-blue-400">
                                            Executive Summary
                                        </span>
                                    </div>
                                    <p className="text-xs font-normal text-zinc-700 dark:text-zinc-200 leading-relaxed">
                                        <InlineMarkdown text={activeNewsletter.summary} />
                                    </p>
                                </div>

                                {/* Key Bullet Highlights */}
                                {parsedBullets.length > 0 && (
                                    <div className="flex flex-col gap-3 p-4 rounded-none bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200/80 dark:border-zinc-800">
                                        <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center gap-2">
                                            📌 Key Takeaways
                                        </h3>
                                        <ul className="flex flex-col gap-2">
                                            {parsedBullets.map((bullet) => (
                                                <li
                                                    key={bullet}
                                                    className="text-xs text-zinc-700 dark:text-zinc-300 font-normal flex items-start gap-2.5 leading-relaxed"
                                                >
                                                    <span className="text-electric-blue-500 font-bold mt-0.5">
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
                                    <div className="flex flex-col gap-3 p-4 rounded-none bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200/80 dark:border-zinc-800">
                                        <div className="flex items-center justify-between gap-2 border-b border-zinc-200 dark:border-zinc-800 pb-2">
                                            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900 dark:text-zinc-300 flex items-center gap-2">
                                                <span>🔬</span>
                                                <span>Spotlighted Company & Sector Research</span>
                                                <span className="text-zinc-400 dark:text-zinc-500 font-mono font-normal">
                                                    ({spotlightCompanies.length})
                                                </span>
                                            </h3>
                                            <Link
                                                to="/companies"
                                                className="text-xs font-bold text-electric-blue-500 hover:underline"
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
                                                        className="p-3.5 rounded-none bg-white dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-800 flex flex-col gap-2.5 transition-all hover:border-zinc-300 dark:hover:border-zinc-700"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div className="min-w-0">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-sm font-bold text-zinc-900 dark:text-white tracking-tight">
                                                                        {company.ticker}
                                                                    </span>
                                                                    {company.is_sector_etf && (
                                                                        <Badge
                                                                            variant="outline"
                                                                            size="xs"
                                                                            radius="none"
                                                                            colorScheme="neutral"
                                                                        >
                                                                            ETF
                                                                        </Badge>
                                                                    )}
                                                                </div>
                                                                <div className="text-xs font-normal text-zinc-500 dark:text-zinc-400 truncate">
                                                                    {company.company_name}
                                                                    {company.sector
                                                                        ? ` • ${company.sector}`
                                                                        : ''}
                                                                </div>
                                                            </div>

                                                            <Badge
                                                                variant="solid"
                                                                size="xs"
                                                                radius="none"
                                                                colorScheme={verdictColor}
                                                                className="uppercase font-bold tracking-wider shrink-0"
                                                            >
                                                                {company.verdict}
                                                            </Badge>
                                                        </div>

                                                        <div className="flex items-center gap-3 text-xs font-mono text-zinc-500 dark:text-zinc-400 pt-1 border-t border-zinc-100 dark:border-zinc-900">
                                                            <span className="font-bold text-zinc-800 dark:text-zinc-200">
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
                                                            <p className="text-xs font-normal text-zinc-600 dark:text-zinc-400 line-clamp-2 leading-relaxed">
                                                                {company.catalyst_context}
                                                            </p>
                                                        )}

                                                        <div className="pt-2 border-t border-zinc-100 dark:border-zinc-900 mt-auto">
                                                            <Link
                                                                to="/companies/$ticker"
                                                                params={{ ticker: company.ticker }}
                                                                className="text-xs font-bold text-electric-blue-500 hover:underline inline-flex items-center gap-1"
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
                                <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800">
                                    <MarkdownContent content={activeNewsletter.content} />
                                </div>

                                {/* Footer metadata */}
                                <div className="pt-6 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-xs font-normal text-zinc-400 font-mono">
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
