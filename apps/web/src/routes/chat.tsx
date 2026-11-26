import { createFileRoute, redirect } from '@tanstack/react-router';
import { ChatPage } from '~/features/chat/ChatPage';
import { seo } from '~/lib/seo';
import { buildAuthRedirectSearch } from '~/shared/auth/redirect';

interface ChatSearch {
    q?: string;
    ticker?: string;
}

export const Route = createFileRoute('/chat')({
    beforeLoad: ({ context, location }) => {
        if (!context.user) {
            throw redirect({
                to: '/login',
                search: buildAuthRedirectSearch(location.pathname, location.searchStr),
                replace: true,
            });
        }
    },
    validateSearch: (search: Record<string, unknown>): ChatSearch => ({
        q: typeof search.q === 'string' ? search.q : undefined,
        ticker: typeof search.ticker === 'string' ? search.ticker : undefined,
    }),
    head: () => ({
        meta: [
            ...seo({
                title: 'Investment Chat Gateway | Benchify',
                description:
                    'Interrogate autonomous trading agents, query memories and causal chains, and evaluate investment theses against live trade history.',
            }),
        ],
    }),
    component: ChatRouteComponent,
});

function ChatRouteComponent() {
    const { user } = Route.useRouteContext();
    const search = Route.useSearch();

    let initialPrompt: string | undefined;
    if (search.q) {
        initialPrompt = search.q;
    } else if (search.ticker) {
        initialPrompt = `Should I invest in ${search.ticker.toUpperCase()} based on current memories and trades?`;
    }

    return <ChatPage user={user} initialPrompt={initialPrompt} />;
}
