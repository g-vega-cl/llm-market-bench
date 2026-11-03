import type { NewsletterSnapshot } from '@llm-market-bench/database';
import { Badge, Card, SectionHeading } from '@llm-market-bench/ui-design-system';
import { Link } from '@tanstack/react-router';
import { parseInlineMarkdown } from '~/components/ui/MarkdownContent';

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
            <section className="flex flex-col gap-4 h-full animate-slide-up">
                <SectionHeading gradient="electric">Daily Intelligence Briefing</SectionHeading>
                <div className="voxel-trough rounded-none flex flex-col items-center justify-center py-12 text-center gap-2">
                    <span className="text-xl">📭</span>
                    <p className="text-xs font-normal text-boxel-muted">
                        No briefings ingested yet today
                    </p>
                </div>
            </section>
        );
    }

    return (
        <section className="flex flex-col gap-4 h-full animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <SectionHeading gradient="electric">Daily Intelligence Briefing</SectionHeading>

                {newsletters.length > 0 && (
                    <Badge colorScheme="accent" variant="soft" size="xs">
                        📰 {newsletters.length} Brief{newsletters.length !== 1 ? 's' : ''}
                    </Badge>
                )}
            </div>

            {newsSummary && (
                <Card padding="md" className="voxel-card flex flex-col gap-2">
                    <div className="flex items-center justify-between gap-2 border-b border-boxel-bevel-hi/60 pb-1.5">
                        <div className="flex items-center gap-1.5">
                            <span className="text-sm">🤖</span>
                            <span className="text-xs font-normal uppercase tracking-wider text-accent font-bold">
                                AI News Synthesis
                            </span>
                        </div>
                        {(newsSummaryDate || newsSummaryTime) && (
                            <span className="text-xs font-normal text-boxel-muted font-mono">
                                {newsSummaryDate}
                                {newsSummaryDate && newsSummaryTime ? ' • ' : ''}
                                {newsSummaryTime}
                            </span>
                        )}
                    </div>
                    <p className="text-xs font-normal text-boxel-ink leading-relaxed italic">
                        "{parseInlineMarkdown(newsSummary)}"
                    </p>

                    <div className="mt-2 pt-2 border-t border-boxel-bevel-hi/60 flex items-center justify-between">
                        <Link
                            to="/generated-newsletters"
                            className="text-sm font-bold text-accent hover:underline uppercase tracking-wider"
                        >
                            Read Full Daily Newsletter →
                        </Link>
                    </div>
                </Card>
            )}

            {newsletters.length > 0 ? (
                <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,16rem),1fr))] gap-4 items-stretch">
                    {newsletters.map((news, idx) => (
                        <Card
                            key={news.id}
                            isHoverable
                            padding="md"
                            className="h-full flex flex-col justify-between gap-3 animate-slide-up"
                            style={{ animationDelay: `${idx * 100}ms` }}
                        >
                            <div className="flex flex-col gap-2">
                                {/* Header */}
                                <div className="flex justify-between items-start gap-3">
                                    <Badge
                                        variant="soft"
                                        colorScheme="accent"
                                        size="xs"
                                        className="whitespace-normal break-words"
                                    >
                                        {formatSender(news.sender)}
                                    </Badge>
                                    <span className="text-xs font-normal text-boxel-muted font-mono shrink-0">
                                        {news.formattedTime
                                            ? `${news.formattedTime} ET`
                                            : 'Unknown Time'}
                                    </span>
                                </div>

                                {/* Content */}
                                <h3 className="text-sm font-bold text-boxel-ink line-clamp-2 leading-snug">
                                    {news.subject}
                                </h3>
                                <p className="text-xs font-normal text-boxel-muted line-clamp-4 leading-relaxed">
                                    {news.content}
                                </p>
                            </div>

                            {/* Footer */}
                            <div className="mt-auto pt-2 border-t border-boxel-bevel-hi flex items-center justify-between text-xs font-normal font-mono text-boxel-muted">
                                <span>
                                    {(news.content?.length || 0).toLocaleString('en-US')} chars
                                </span>
                                <span className="text-sm font-bold text-accent hover:underline uppercase tracking-wider">
                                    Read More →
                                </span>
                            </div>
                        </Card>
                    ))}
                </div>
            ) : (
                <div className="voxel-trough rounded-none flex flex-col items-center justify-center py-12 text-center gap-2">
                    <span className="text-xl">📭</span>
                    <p className="text-xs font-normal text-boxel-muted">
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
