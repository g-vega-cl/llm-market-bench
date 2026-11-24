import { PageLayout } from '@llm-market-bench/ui-design-system';
import { ChatInterface } from './ChatInterface';

interface ChatPageProps {
    user: { email: string } | null;
    initialPrompt?: string;
}

export function ChatPage({ user, initialPrompt }: ChatPageProps) {
    return (
        <PageLayout maxWidth="xl" className="flex flex-col gap-6">
            <h1 className="sr-only">Investment Chat Gateway</h1>

            <div className="w-full min-w-0">
                <ChatInterface user={user} initialPrompt={initialPrompt} isFullPage={true} />
            </div>
        </PageLayout>
    );
}
