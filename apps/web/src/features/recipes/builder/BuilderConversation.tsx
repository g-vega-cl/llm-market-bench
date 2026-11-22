import { Badge, Button, Card } from '@llm-market-bench/ui-design-system';
import type { BuilderMessage, CompilerReply } from './compiler';

export interface BuilderConversationProps {
    messages: BuilderMessage[];
    messageIds: string[];
    reply: CompilerReply | null;
    pendingIdea: string | null;
    isSignedIn: boolean;
    onSend: (text: string) => void;
}

function MessageRow({ message }: { message: BuilderMessage }) {
    return (
        <Card padding="sm" className="flex flex-col gap-1">
            <span className="text-xs font-normal uppercase text-voxel-muted">
                {message.role === 'user' ? 'You' : 'Builder'}
            </span>
            <p className="text-xs font-normal text-voxel-ink whitespace-pre-wrap break-words">
                {message.content}
            </p>
        </Card>
    );
}

function PendingIdeaCard({
    idea,
    isSignedIn,
    onSend,
}: {
    idea: string;
    isSignedIn: boolean;
    onSend: (text: string) => void;
}) {
    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-normal uppercase text-voxel-muted">
                Saved in this browser
            </span>
            <p className="text-xs font-normal text-voxel-ink break-words">{idea}</p>
            <div>
                <Button variant="solid" size="sm" onClick={() => onSend(idea)}>
                    {isSignedIn ? 'Continue' : 'Sign in to continue'}
                </Button>
            </div>
        </Card>
    );
}

function QuestionOptions({
    reply,
    onSend,
}: {
    reply: CompilerReply;
    onSend: (text: string) => void;
}) {
    if (reply.status !== 'question' || reply.options.length === 0) return null;
    return (
        <div className="flex flex-wrap gap-2">
            {reply.options.map((option) => (
                <Button key={option} variant="outline" size="sm" onClick={() => onSend(option)}>
                    {option}
                </Button>
            ))}
        </div>
    );
}

function DeclinedCard({ reply }: { reply: CompilerReply }) {
    if (reply.status !== 'declined') return null;
    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <Badge colorScheme="warning" variant="soft" size="sm">
                CANNOT RUN AS DESCRIBED
            </Badge>
            <p className="text-xs font-normal text-voxel-ink break-words">{reply.reason}</p>
            {reply.closest ? (
                <p className="text-xs font-normal text-voxel-muted break-words">
                    Closest buildable version: {reply.closest}
                </p>
            ) : null}
        </Card>
    );
}

export function BuilderConversation({
    messages,
    messageIds,
    reply,
    pendingIdea,
    isSignedIn,
    onSend,
}: BuilderConversationProps) {
    return (
        <section className="flex flex-col gap-3" aria-live="polite">
            {messages.map((message, index) => (
                <MessageRow key={messageIds[index] ?? `m-${index}`} message={message} />
            ))}

            {pendingIdea ? (
                <PendingIdeaCard idea={pendingIdea} isSignedIn={isSignedIn} onSend={onSend} />
            ) : null}

            {reply ? <QuestionOptions reply={reply} onSend={onSend} /> : null}
            {reply ? <DeclinedCard reply={reply} /> : null}
        </section>
    );
}
