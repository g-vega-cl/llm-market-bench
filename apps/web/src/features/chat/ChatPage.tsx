import { PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { ChatInterface } from './ChatInterface';

interface ChatPageProps {
    user: { email: string } | null;
    initialPrompt?: string;
}

export function ChatPage({ user, initialPrompt }: ChatPageProps) {
    return (
        <PageLayout>
            <h1 className="sr-only">Investment Chat Gateway</h1>

            <div className="max-w-5xl mx-auto w-full px-4 md:px-0">
                <div className="mb-4">
                    <SectionHeading>Interactive Research Terminal</SectionHeading>
                    <p className="text-xs font-normal text-zinc-400 mt-1 pl-7">
                        Grounded in real-time Supabase trade history, agent decisions, and market
                        memories.
                    </p>
                </div>

                <div className="mt-4">
                    <ChatInterface user={user} initialPrompt={initialPrompt} isFullPage={true} />
                </div>
            </div>
        </PageLayout>
    );
}
