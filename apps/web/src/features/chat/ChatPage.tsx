import { HeroBackground, PageLayout, SectionHeading } from '@llm-market-bench/ui-design-system';
import { ChatInterface } from './ChatInterface';

interface ChatPageProps {
    user: { email: string } | null;
    initialPrompt?: string;
}

export function ChatPage({ user, initialPrompt }: ChatPageProps) {
    return (
        <PageLayout>
            <HeroBackground gradient="ai">
                <div className="text-center max-w-3xl mx-auto space-y-4">
                    <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight">
                        Investment Chat Gateway
                    </h1>
                    <p className="text-lg text-zinc-200 font-light">
                        Interrogate autonomous trading agents, query memories & causal chains, and
                        evaluate investment theses.
                    </p>
                </div>
            </HeroBackground>

            <div className="mt-8 max-w-5xl mx-auto w-full px-4 md:px-0">
                <div className="mb-4">
                    <SectionHeading gradient="ai">Interactive Research Terminal</SectionHeading>
                    <p className="text-xs text-zinc-400 mt-1 pl-7">
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
