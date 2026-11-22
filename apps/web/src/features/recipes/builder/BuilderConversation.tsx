import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type { BuilderMessage, CompilerReply } from './compiler';

export interface BuilderConversationProps {
    messages: BuilderMessage[];
    messageIds: string[];
    reply: CompilerReply | null;
    pendingIdea: string | null;
    isSignedIn: boolean;
    isCompiling?: boolean;
    onSend: (text: string) => void;
}

function MessageRow({ message }: { message: BuilderMessage }) {
    return (
        <div
            data-testid="builder-message-row"
            className="voxel-trough bg-voxel-trough rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <span className="text-xs font-normal uppercase text-voxel-muted">
                {message.role === 'user' ? 'You' : 'Builder'}
            </span>
            <p className="text-xs font-normal text-voxel-ink whitespace-pre-wrap break-words">
                {message.content}
            </p>
        </div>
    );
}

function PendingIdeaCard({
    idea,
    isSignedIn,
    disabled,
    onSend,
}: {
    idea: string;
    isSignedIn: boolean;
    disabled: boolean;
    onSend: (text: string) => void;
}) {
    return (
        <div
            data-testid="builder-pending-idea"
            className="voxel-trough bg-voxel-trough rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <span className="text-xs font-normal uppercase text-voxel-muted">
                Saved in this browser
            </span>
            <p className="text-xs font-normal text-voxel-ink break-words">{idea}</p>
            <div>
                <Button variant="solid" size="sm" disabled={disabled} onClick={() => onSend(idea)}>
                    {isSignedIn ? 'Continue' : 'Sign in to continue'}
                </Button>
            </div>
        </div>
    );
}

function QuestionOptions({
    reply,
    disabled,
    onSend,
}: {
    reply: CompilerReply;
    disabled: boolean;
    onSend: (text: string) => void;
}) {
    if (
        reply.status !== 'question' ||
        !Array.isArray(reply.options) ||
        reply.options.length === 0
    ) {
        return null;
    }
    return (
        <div className="flex flex-wrap gap-2">
            {reply.options.map((option) => (
                <Button
                    key={option}
                    variant="outline"
                    size="sm"
                    disabled={disabled}
                    onClick={() => onSend(option)}
                >
                    {option}
                </Button>
            ))}
        </div>
    );
}

function DeclinedCard({ reply }: { reply: CompilerReply }) {
    if (reply.status !== 'declined') return null;
    return (
        <div
            data-testid="builder-declined-card"
            className="voxel-trough bg-voxel-trough rounded-none p-3 flex flex-col gap-2 min-w-0"
        >
            <div>
                <Badge colorScheme="warning" variant="soft" size="sm">
                    CANNOT RUN AS DESCRIBED
                </Badge>
            </div>
            <p className="text-xs font-normal text-voxel-ink break-words">{reply.reason}</p>
            {reply.closest ? (
                <p className="text-xs font-normal text-voxel-muted break-words">
                    Closest buildable version: {reply.closest}
                </p>
            ) : null}
        </div>
    );
}

export function BuilderConversation({
    messages,
    messageIds,
    reply,
    pendingIdea,
    isSignedIn,
    isCompiling = false,
    onSend,
}: BuilderConversationProps) {
    const hasContent = messages.length > 0 || Boolean(pendingIdea) || Boolean(reply);

    return (
        <section
            className={hasContent ? 'flex flex-col gap-2 min-w-0' : 'sr-only'}
            aria-live="polite"
        >
            {messages.map((message, index) => (
                <MessageRow key={messageIds[index] ?? `m-${index}`} message={message} />
            ))}

            {pendingIdea ? (
                <PendingIdeaCard
                    idea={pendingIdea}
                    isSignedIn={isSignedIn}
                    disabled={isCompiling}
                    onSend={onSend}
                />
            ) : null}

            {reply ? (
                <QuestionOptions reply={reply} disabled={isCompiling} onSend={onSend} />
            ) : null}
            {reply ? <DeclinedCard reply={reply} /> : null}
        </section>
    );
}
