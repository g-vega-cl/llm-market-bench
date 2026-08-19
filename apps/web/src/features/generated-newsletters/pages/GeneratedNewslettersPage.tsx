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

    return (
        <PageLayout className="py-8 space-y-8" maxWidth="xl">
            {/* Header section */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <Link
                            to="/today"
                            className="text-xs font-bold text-electric-blue-500 hover:underline inline-flex items-center gap-1"
                        >
                            ← Back to Today's Dashboard
                        </Link>
                    </div>
                    <SectionHeading gradient="electric">
                        Daily Market Intelligence Briefings
                    </SectionHeading>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-2xl font-light">
                        Synthesized ~6 minute reads based on ingested daily newsletters, generated
                        twice daily at market open (09:15 ET) and market close (17:00 ET).
                    </p>
                </div>

                {/* Session filter tabs */}
                <div className="flex items-center gap-1.5 p-1.5 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl self-start md:self-auto">
                    <button
                        type="button"
                        onClick={() => {
                            setSelectedSession('all');
                            if (initialNewsletters.length) setSelectedId(initialNewsletters[0].id);
                        }}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
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
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1 ${
                            selectedSession === 'open'
                                ? 'bg-electric-blue-500 text-white shadow-sm'
                                : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'
                        }`}
                    >
                        🌅 Open (09:15 ET)
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
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1 ${
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
                    subtitle="Daily briefings are automatically synthesized at 09:15 ET (Market Open) and 17:00 ET (Market Close)."
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
                    <div className="lg:col-span-4 space-y-3">
                        <div className="flex items-center justify-between px-1">
                            <span className="text-xs font-black text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
                                Archive ({filteredNewsletters.length})
                            </span>
                            <span className="text-[10px] text-zinc-400 font-mono">
                                DeepSeek V4 Flash
                            </span>
                        </div>

                        <div className="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
                            {filteredNewsletters.map((newsletter) => {
                                const isSelected = activeNewsletter?.id === newsletter.id;
                                const isOpenSession = newsletter.session === 'open';

                                return (
                                    <button
                                        type="button"
                                        key={newsletter.id}
                                        onClick={() => setSelectedId(newsletter.id)}
                                        className={`w-full p-4 rounded-2xl border transition-all cursor-pointer text-left space-y-2 ${
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
                                                className="uppercase text-[9px] font-bold"
                                            >
                                                {isOpenSession
                                                    ? '🌅 Market Open'
                                                    : '🌆 Market Close'}
                                            </Badge>
                                            <span className="text-[10px] text-zinc-400 font-mono tabular-nums">
                                                {newsletter.displayTime}
                                            </span>
                                        </div>

                                        <h4 className="text-sm font-bold text-zinc-900 dark:text-white line-clamp-2 leading-snug">
                                            {newsletter.title}
                                        </h4>

                                        <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 font-light">
                                            {newsletter.summary}
                                        </p>

                                        <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-zinc-100 dark:border-zinc-800/80">
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
                        <div className="lg:col-span-8 space-y-6">
                            <Card className="p-6 md:p-8 space-y-6 relative overflow-hidden border-electric-blue-100 dark:border-electric-blue-900/30">
                                {/* Side Accent Line */}
                                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-electric-blue-500 via-deep-purple-500 to-electric-blue-600" />

                                {/* Header badges & Meta */}
                                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
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
                                        <span className="px-2.5 py-1 rounded-full text-xs font-mono bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                                            🕒 Created at {activeNewsletter.displayTime}
                                        </span>
                                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-electric-blue-50 dark:bg-electric-blue-950/40 text-electric-blue-600 dark:text-electric-blue-400 border border-electric-blue-200 dark:border-electric-blue-800/50">
                                            ⏱️ {activeNewsletter.read_time_minutes ?? 6} min read
                                        </span>
                                    </div>
                                    <span className="text-xs text-zinc-400 font-mono">
                                        {activeNewsletter.formattedDate}
                                    </span>
                                </div>

                                {/* Newsletter Title */}
                                <div className="space-y-3">
                                    <h1 className="text-2xl md:text-3xl font-black text-zinc-900 dark:text-white tracking-tight leading-tight">
                                        {activeNewsletter.title}
                                    </h1>
                                </div>

                                {/* Executive Summary Banner */}
                                <div className="p-4 rounded-2xl bg-electric-blue-50/60 dark:bg-electric-blue-950/20 border border-electric-blue-200/60 dark:border-electric-blue-900/40 space-y-1.5">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm">⚡</span>
                                        <span className="text-xs font-black uppercase tracking-widest text-electric-blue-600 dark:text-electric-blue-400">
                                            Executive Summary
                                        </span>
                                    </div>
                                    <p className="text-sm text-zinc-700 dark:text-zinc-200 font-medium leading-relaxed">
                                        {activeNewsletter.summary}
                                    </p>
                                </div>

                                {/* Key Bullet Highlights */}
                                {parsedBullets.length > 0 && (
                                    <div className="space-y-3 p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-900/40 border border-zinc-200/80 dark:border-zinc-800">
                                        <h3 className="text-xs font-black uppercase tracking-widest text-zinc-500 dark:text-zinc-400 flex items-center gap-2">
                                            📌 Key Takeaways
                                        </h3>
                                        <ul className="space-y-2">
                                            {parsedBullets.map((bullet) => (
                                                <li
                                                    key={bullet}
                                                    className="text-xs md:text-sm text-zinc-700 dark:text-zinc-300 font-light flex items-start gap-2.5 leading-relaxed"
                                                >
                                                    <span className="text-electric-blue-500 font-bold mt-0.5">
                                                        •
                                                    </span>
                                                    <span>{bullet}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Main Newsletter Body Content */}
                                <div className="pt-4 border-t border-zinc-100 dark:border-zinc-800">
                                    <MarkdownContent content={activeNewsletter.content} />
                                </div>

                                {/* Footer metadata */}
                                <div className="pt-6 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between text-[11px] text-zinc-400 font-mono">
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
