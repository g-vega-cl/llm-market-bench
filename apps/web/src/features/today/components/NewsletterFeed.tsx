import type { NewsletterSnapshot } from '@llm-market-bench/database';
import { Badge, SectionHeading } from '@llm-market-bench/ui-design-system';

interface NewsletterFeedProps {
    newsletters: NewsletterSnapshot[];
}

export function NewsletterFeed({ newsletters }: NewsletterFeedProps) {
    if (!newsletters.length) return null;

    return (
        <section className="space-y-8 animate-slide-up">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <SectionHeading gradient="electric">Daily Intelligence Briefing</SectionHeading>

                <div className="flex items-center gap-2 px-4 py-2 bg-electric-blue-50 dark:bg-electric-blue-950/20 border border-electric-blue-200 dark:border-electric-blue-900/30 rounded-xl shadow-md">
                    <span className="text-[10px] font-black text-electric-blue-600 dark:text-electric-blue-400 uppercase tracking-widest">
                        📰 {newsletters.length} Brief{newsletters.length !== 1 ? 's' : ''}
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {newsletters.map((news, idx) => (
                    <article
                        key={news.id}
                        className="group relative p-6 border border-zinc-200 dark:border-zinc-800 rounded-3xl bg-white dark:bg-zinc-900 shadow-sm hover:shadow-xl hover:shadow-electric-blue-500/10 transition-all duration-300 card-lift overflow-hidden animate-slide-up"
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
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <Badge variant="soft" colorScheme="accent" size="xs">
                                        {news.sender}
                                    </Badge>
                                </div>
                                <span className="text-[10px] text-zinc-400 font-mono flex items-center gap-1.5 tabular-nums">
                                    <span className="w-2 h-2 bg-electric-blue-400 rounded-full animate-pulse" />
                                    {new Date(news.date).toLocaleTimeString([], {
                                        hour: '2-digit',
                                        minute: '2-digit',
                                    })}
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
                    </article>
                ))}
            </div>
        </section>
    );
}
