import { createFileRoute, redirect } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';
import { NotFound } from '~/components/ui/NotFound';
import { LlmLogsPage } from '~/features/llm-logs/LlmLogsPage';
import { fetchLlmLogsFn } from '~/features/llm-logs/llm-logs-server';
import {
    isAllowedLlmLogsEmail,
    type LlmLogsFilter,
    type LlmLogsResponse,
} from '~/features/llm-logs/llm-logs-types';
import { seo } from '~/lib/seo';
import { buildAuthRedirectSearch } from '~/shared/auth/redirect';

export const Route = createFileRoute('/llm-logs')({
    beforeLoad: ({ context, location }) => {
        if (!context.user) {
            throw redirect({
                to: '/login',
                search: buildAuthRedirectSearch(location.pathname, location.searchStr),
                replace: true,
            });
        }
    },
    head: () => ({
        meta: [
            { name: 'robots', content: 'noindex, nofollow' },
            ...seo({
                title: 'LLM Proxy Logs | Benchify',
                description: 'Private free LLM proxy audit logs.',
            }),
        ],
    }),
    component: LlmLogsRouteComponent,
});

function LlmLogsRouteComponent() {
    const { user } = Route.useRouteContext();
    const isAuthorized = isAllowedLlmLogsEmail(user?.email);

    const [filter, setFilter] = useState<LlmLogsFilter>({ limit: 50, offset: 0 });
    const [data, setData] = useState<LlmLogsResponse | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);

    const loadLogs = useCallback(
        async (activeFilter: LlmLogsFilter) => {
            if (!isAuthorized) return;
            setIsLoading(true);
            setErrorMessage(null);
            try {
                const res = await fetchLlmLogsFn({ data: activeFilter });
                setData(res);
            } catch (err) {
                setErrorMessage(err instanceof Error ? err.message : 'Failed to load proxy logs');
            } finally {
                setIsLoading(false);
            }
        },
        [isAuthorized],
    );

    useEffect(() => {
        if (isAuthorized) {
            void loadLogs(filter);
        }
    }, [isAuthorized, filter, loadLogs]);

    if (!isAuthorized) {
        return <NotFound />;
    }

    return (
        <LlmLogsPage
            data={data}
            errorMessage={errorMessage}
            isLoading={isLoading}
            filter={filter}
            onFilterChange={setFilter}
            onRefresh={() => void loadLogs(filter)}
        />
    );
}
