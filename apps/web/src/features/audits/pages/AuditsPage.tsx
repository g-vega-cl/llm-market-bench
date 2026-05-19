import {
    Button,
    ErrorCard,
    LoadingBoundary,
    LoadingSpinner,
    PageLayout,
    SectionHeading,
    SubHeading,
} from '@llm-market-bench/ui-design-system';
import { useInfiniteQuery } from '@tanstack/react-query';
import * as React from 'react';
import type { PaginatedAudits } from '../api/fetch-audits';
import { AuditCard } from '../components/AuditCard';
import { auditsQueries } from '../queries/options';

interface AuditsPageProps {
    fetchFn: (cursor: string | undefined) => Promise<PaginatedAudits>;
}

export function AuditsPage({ fetchFn }: AuditsPageProps) {
    const { data, fetchNextPage, hasNextPage, isFetching, isFetchingNextPage, status, error } =
        useInfiniteQuery({
            ...auditsQueries.list({ fetchFn }),
        });

    const allAudits = React.useMemo(() => data?.pages.flatMap((page) => page.data) || [], [data]);

    const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
    const sortedAudits = [...allAudits].sort(
        (a, b) =>
            severityOrder[a.severity as keyof typeof severityOrder] -
            severityOrder[b.severity as keyof typeof severityOrder],
    );

    const dbAudits = sortedAudits.filter(
        (a) =>
            a.audit_type === 'DB_ANOMALY' ||
            a.audit_type === 'DATA_QUALITY' ||
            a.audit_type === 'CODE_ERROR',
    );
    const logAudits = sortedAudits.filter((a) => a.audit_type === 'SYSTEM_LOG');

    if (status === 'pending') {
        return (
            <LoadingBoundary isLoading={true}>
                <div />
            </LoadingBoundary>
        );
    }

    if (status === 'error') {
        return <ErrorCard title="Failed to load audits" message={(error as Error).message} />;
    }

    return (
        <div className="min-h-screen">
            <PageLayout>
                <header className="mb-12">
                    <SectionHeading gradient="ai">System Audits</SectionHeading>
                    <p className="text-zinc-400 text-lg leading-relaxed mt-2">
                        Database integrity checks, code error monitoring, and continuous improvement
                        suggestions. Updated weekly.
                    </p>
                </header>

                <div className="space-y-12">
                    <section>
                        <SubHeading
                            rightElement={
                                <span className="text-sm font-normal text-zinc-500">
                                    ({dbAudits.length} findings)
                                </span>
                            }
                        >
                            Database Audits
                        </SubHeading>
                        {dbAudits.length === 0 ? (
                            <p className="text-zinc-500 italic">No database anomalies found.</p>
                        ) : (
                            <div className="space-y-4">
                                {dbAudits.map((audit) => (
                                    <AuditCard key={audit.id} audit={audit} />
                                ))}
                            </div>
                        )}
                    </section>

                    <section>
                        <SubHeading
                            rightElement={
                                <span className="text-sm font-normal text-zinc-500">
                                    ({logAudits.length} findings)
                                </span>
                            }
                        >
                            System Log Analysis
                        </SubHeading>
                        {logAudits.length === 0 ? (
                            <p className="text-zinc-500 italic">No system log issues found.</p>
                        ) : (
                            <div className="space-y-4">
                                {logAudits.map((audit) => (
                                    <AuditCard key={audit.id} audit={audit} />
                                ))}
                            </div>
                        )}
                    </section>

                    {hasNextPage && (
                        <div className="pt-4 pb-2">
                            <Button
                                variant="solid"
                                size="lg"
                                colorScheme="neutral"
                                onClick={() => fetchNextPage()}
                                isLoading={isFetchingNextPage}
                                className="w-full"
                            >
                                Load More
                            </Button>
                        </div>
                    )}

                    {!hasNextPage && allAudits.length > 0 && (
                        <div className="text-center py-4 text-zinc-500 text-xs uppercase tracking-widest">
                            • End of audit findings •
                        </div>
                    )}

                    {isFetching && !isFetchingNextPage && (
                        <div className="text-center py-2">
                            <LoadingSpinner size="sm" />
                        </div>
                    )}
                </div>
            </PageLayout>
        </div>
    );
}
