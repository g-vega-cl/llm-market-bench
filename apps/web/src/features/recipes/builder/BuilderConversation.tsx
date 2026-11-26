import { Badge, Button } from '@llm-market-bench/ui-design-system';
import type { BuilderMessage, CompilerReply } from './compiler';

export interface BuilderActivePromptProps {
    messages: BuilderMessage[];
    reply: CompilerReply | null;
    pendingIdea: string | null;
    isSignedIn: boolean;
    isCompiling?: boolean;
    hasError?: boolean;
    onSend: (text: string) => void;
}

export interface BuilderMessageHistoryProps {
    messages: BuilderMessage[];
    messageIds: string[];
    reply: CompilerReply | null;
    isCompiling?: boolean;
    hasError?: boolean;
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
            {!isSignedIn ? (
                <p className="text-xs font-normal text-voxel-muted leading-relaxed">
                    Free Google sign-in is required to compile with AI and save your bot (2 free
                    backtests/day, 3 live paper bots). You&apos;ll return right here with this draft
                    loaded to finish alignment and backtest.
                </p>
            ) : null}
            <div>
                <Button
                    variant="solid"
                    size="sm"
                    colorScheme="accent"
                    disabled={disabled}
                    onClick={() => onSend(idea)}
                >
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

function resolveLatestQuestionIndex(
    messages: BuilderMessage[],
    reply: CompilerReply | null,
    isActiveTurn: boolean,
): number {
    if (messages.length === 0) return -1;
    const lastIndex = messages.length - 1;
    if (reply?.status === 'question') {
        return messages[lastIndex]?.role === 'assistant' ? lastIndex : -1;
    }
    if (
        isActiveTurn &&
        messages.length >= 2 &&
        messages[lastIndex]?.role === 'user' &&
        messages[lastIndex - 1]?.role === 'assistant'
    ) {
        return lastIndex - 1;
    }
    return -1;
}

/**
 * Active prompt slot rendered above the input/CTA so the user always sees what
 * action is needed right now (parked browser idea, current clarifying question
 * + quick picks, or declined-scope explanation) without scrolling.
 */
export function BuilderActivePrompt({
    messages,
    reply,
    pendingIdea,
    isSignedIn,
    isCompiling = false,
    hasError = false,
    onSend,
}: BuilderActivePromptProps) {
    const activeQuestionIndex = resolveLatestQuestionIndex(
        messages,
        reply,
        isCompiling || hasError,
    );
    const activeQuestion = activeQuestionIndex >= 0 ? messages[activeQuestionIndex] : null;
    const hasContent = Boolean(pendingIdea) || Boolean(activeQuestion) || Boolean(reply);

    return (
        <section
            className={hasContent ? 'flex flex-col gap-2 min-w-0' : 'sr-only'}
            aria-live="polite"
        >
            {pendingIdea ? (
                <PendingIdeaCard
                    idea={pendingIdea}
                    isSignedIn={isSignedIn}
                    disabled={isCompiling}
                    onSend={onSend}
                />
            ) : null}

            {activeQuestion ? <MessageRow message={activeQuestion} /> : null}

            {reply ? (
                <QuestionOptions reply={reply} disabled={isCompiling} onSend={onSend} />
            ) : null}
            {reply ? <DeclinedCard reply={reply} /> : null}
        </section>
    );
}

/**
 * Prior conversation turns rendered below the active input/CTA so historical
 * context stays accessible without pushing the primary action off-screen.
 */
export function BuilderMessageHistory({
    messages,
    messageIds,
    reply,
    isCompiling = false,
    hasError = false,
}: BuilderMessageHistoryProps) {
    const activeQuestionIndex = resolveLatestQuestionIndex(
        messages,
        reply,
        isCompiling || hasError,
    );
    const historyEntries = messages
        .map((message, index) => ({
            message,
            id: messageIds[index] ?? `m-${index}`,
            index,
        }))
        .filter((entry) => entry.index !== activeQuestionIndex);

    if (historyEntries.length === 0) return null;

    return (
        <section aria-label="Earlier messages" className="flex flex-col gap-2 min-w-0">
            {historyEntries.map((entry) => (
                <MessageRow key={entry.id} message={entry.message} />
            ))}
        </section>
    );
}
