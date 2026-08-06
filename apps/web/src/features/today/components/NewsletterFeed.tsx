import type { NewsletterSnapshot } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';

interface NewsletterFeedProps {
    newsletters: (NewsletterSnapshot & { formattedTime?: string })[];
    newsSummary?: string | null;
    newsSummaryDate?: string | null;
    newsSummaryTime?: string | null;
}

export function NewsletterFeed({
    newsletters,
    newsSummary,
    newsSummaryDate,
    newsSummaryTime,
}: NewsletterFeedProps) {
    if (!newsletters.length && !newsSummary) {
        return (
            <section className="space-y-8 animate-slide-up">
                <SectionHeading gradient="electric">Daily Intelligence Briefing</SectionHeading>
                <div className="flex flex-col items-center justify-center py-12 rounded-3xl border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 text-center gap-3">
                    <span className="text-3xl">📭</span>
                    <p className="text-sm font-medium text-zinc-400 dark:text-zinc-500">
                        No briefings ingested yet today
                    </p>
                </div>
            </section>
        );
    }

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="electric">Daily Intelligence Briefing</SectionHeading>

                {newsletters.length > 0 && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-electric-blue-50 dark:bg-electric-blue-950/20 border border-electric-blue-200 dark:border-electric-blue-900/30 rounded-xl shadow-md">
                        <span className="text-[10px] font-black text-electric-blue-600 dark:text-electric-blue-400 uppercase tracking-widest">
                            📰 {newsletters.length} Brief{newsletters.length !== 1 ? 's' : ''}
                        </span>
                    </div>
                )}
            </div>

            {newsSummary && (
                <Card className="relative overflow-hidden border border-electric-blue-100 dark:border-electric-blue-900/30 bg-electric-blue-50/10 dark:bg-electric-blue-950/5 rounded-3xl">
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-electric-blue-500 to-deep-purple-500" />
                    <div className="relative pl-6 py-4 pr-4">
                        <div className="flex items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2">
                                <span className="text-lg">🤖</span>
                                <span className="text-xs font-black uppercase tracking-widest text-electric-blue-500 dark:text-electric-blue-400">
                                    AI News Synthesis
                                </span>
                            </div>
                            {(newsSummaryDate || newsSummaryTime) && (
                                <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono">
                                    {newsSummaryDate}
                                    {newsSummaryDate && newsSummaryTime ? ' • ' : ''}
                                    {newsSummaryTime}
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed font-light italic">
                            "{newsSummary}"
                        </p>

                        <div className="mt-3 pt-3 border-t border-electric-blue-100/50 dark:border-electric-blue-900/20 flex items-center justify-between">
                            <Link
                                to="/generated-newsletters"
                                className="text-xs font-bold text-electric-blue-600 dark:text-electric-blue-400 hover:text-electric-blue-500 transition-colors inline-flex items-center gap-1.5 group/link"
                            >
                                <span>📰 Read Full Daily Newsletter (1-2 min read)</span>
                                <span className="group-hover/link:translate-x-1 transition-transform">
                                    →
                                </span>
                            </Link>
                        </div>
                    </div>
                </Card>
            )}

            {newsletters.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {newsletters.map((news, idx) => (
                        <Card
                            key={news.id}
                            isHoverable
                            className="relative overflow-hidden animate-slide-up hover:shadow-electric-blue-500/10"
                            style={{ animationDelay: `${idx * 100}ms` }}
                        >
                            {/* Gradient Border on Hover */}
                            <div
                                className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
                                style={{
                                    background:
                                        'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%)',
                                }}
                            />
                            <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none border-2 border-electric-blue-500/30" />

                            {/* Content Container */}
                            <div className="relative">
                                {/* Header */}
                                <div className="flex justify-between items-start gap-4 mb-4">
                                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                                        <Badge
                                            variant="soft"
                                            colorScheme="accent"
                                            size="xs"
                                            className="whitespace-normal break-words text-center justify-center"
                                        >
                                            {formatSender(news.sender)}
                                        </Badge>
                                    </div>
                                    <span className="text-[10px] text-zinc-400 font-mono flex items-center gap-1.5 tabular-nums">
                                        {news.formattedTime
                                            ? `${news.formattedTime} ET`
                                            : 'Unknown Time'}
                                    </span>
                                </div>

                                {/* Content */}
                                <h3 className="text-lg font-bold text-zinc-900 dark:text-white mb-3 group-hover:text-electric-blue-500 transition-colors duration-300 line-clamp-2 leading-snug">
                                    {news.subject}
                                </h3>
                                <p className="text-sm text-zinc-500 dark:text-zinc-400 line-clamp-4 font-light leading-relaxed">
                                    {news.content}
                                </p>

                                {/* Footer */}
                                <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                                    <span className="text-[9px] font-black text-zinc-400 uppercase tracking-widest tabular-nums">
                                        {(news.content?.length || 0).toLocaleString()} chars
                                    </span>
                                    <span className="text-[9px] font-bold text-electric-blue-500 uppercase tracking-wider group-hover:translate-x-2 transition-transform duration-300 inline-flex items-center gap-1.5">
                                        Read More
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            width="14"
                                            height="14"
                                            viewBox="0 0 24 24"
                                            fill="none"
                                            stroke="currentColor"
                                            strokeWidth="3"
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            className="group-hover:translate-x-1 transition-transform duration-300"
                                        >
                                            <title>SVG</title>
                                            <path d="M5 12h14M12 5l7 7-7 7" />
                                        </svg>
                                    </span>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center py-12 rounded-3xl border border-dashed border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/30 text-center gap-3">
                    <span className="text-3xl">📭</span>
                    <p className="text-sm font-medium text-zinc-400 dark:text-zinc-500">
                        No individual briefings ingested yet today
                    </p>
                </div>
            )}
        </section>
    );
}

export function formatSender(sender: string): string {
    if (!sender) return '';
    const cleaned = sender.replace(/<[^>]*>/g, '').trim();
    return cleaned || sender;
}
