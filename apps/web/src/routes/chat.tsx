import { createFileRoute } from '@tanstack/react-router';
import { ChatPage } from '~/features/chat/ChatPage';

interface ChatSearch {
    q?: string;
    ticker?: string;
}

export const Route = createFileRoute('/chat')({
    validateSearch: (search: Record<string, unknown>): ChatSearch => ({
        q: typeof search.q === 'string' ? search.q : undefined,
        ticker: typeof search.ticker === 'string' ? search.ticker : undefined,
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
