import { usePostHog } from '@posthog/react';
import * as React from 'react';
import { InlineMarkdown, MarkdownContent } from '~/components/ui/MarkdownContent';
import { formatEasternTime } from '~/utils/date';
import {
    type AgentQueueItem,
    MAX_QUEUE_MESSAGE_LENGTH,
    submitAgentQueueQuestion,
} from '../api/fetch-agent-queue';

function formatTimestamp(ts: string | null | undefined): string | null {
    if (!ts) return null;
    if (ts.endsWith('ET') || ts.endsWith('EST') || ts.endsWith('EDT')) return ts;
    const formatted = formatEasternTime(ts);
    return formatted === 'Unknown' ? ts : formatted;
}

export function isOutageFallbackResponse(response: string | null | undefined): boolean {
    if (!response) return false;
    const trimmed = response.trim();
    return (
        trimmed.includes('All LLM endpoints currently unavailable') ||
        (trimmed.startsWith('{') && trimmed.includes('"action"') && trimmed.includes('"HOLD"'))
    );
}

export interface ConsoleQueueCardProps {
    user?: { id: string; email?: string } | null;
    pendingCount?: number;
    latestAnswered?: AgentQueueItem | null;
    onQuestionQueued?: () => void;
}

function AnsweredTurnView({
    latestAnswered,
    isOutage,
}: {
    latestAnswered: AgentQueueItem;
    isOutage: boolean;
}) {
    const injectedTime = formatTimestamp(latestAnswered.injected_turn_at);
    const createdTime = formatTimestamp(latestAnswered.created_at);

    return (
        <div className="border-t border-boxel-bevel-hi/60 pt-2 flex flex-col gap-1.5 text-xs">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-boxel-muted font-mono text-xs font-normal">
                <div className="flex flex-wrap items-baseline gap-x-2 min-w-0">
                    <span className="whitespace-nowrap">Latest Answered Turn:</span>
                    {injectedTime && <span className="whitespace-nowrap">{injectedTime}</span>}
                </div>
                <div className="flex flex-wrap items-baseline gap-x-2 min-w-0">
                    <span className="min-w-0 truncate">@{latestAnswered.display_name}</span>
                    {createdTime && <span className="whitespace-nowrap">• {createdTime}</span>}
                </div>
            </div>
            <div className="flex flex-col gap-2 min-w-0">
                <span className="text-xs font-normal uppercase tracking-wider text-boxel-muted">
                    Question
                </span>
                <div
                    data-testid="answered-question"
                    className="min-w-0 border-l-2 border-accent/40 pl-2.5 text-xs font-normal leading-relaxed text-boxel-ink whitespace-pre-wrap break-words"
                >
                    <InlineMarkdown text={latestAnswered.message} />
                </div>
            </div>
            {latestAnswered.agent_response &&
                (isOutage ? (
                    <div className="p-2.5 bg-boxel-surface border border-accent/40 flex flex-col gap-1 text-xs font-normal font-mono">
                        <div className="flex items-center gap-1.5 text-sm font-bold text-accent">
                            <span>⚠️</span>
                            <span>DESK NOTICE: HIGH SYSTEM VOLUME</span>
                        </div>
                        <div className="text-boxel-ink leading-relaxed">
                            Quantitative commentary models experienced high demand during this
                            evaluation turn. The desk maintained a disciplined neutral stance, and
                            your inquiry has been recorded for the strategists on the next turn.
                        </div>
                    </div>
                ) : (
                    <div className="text-boxel-ink text-xs font-normal leading-relaxed break-words bg-boxel-canvas/60 p-2.5 border border-accent/20 font-mono min-w-0">
                        <MarkdownContent content={latestAnswered.agent_response} />
                    </div>
                ))}
        </div>
    );
}

export function ConsoleQueueCard({
    user,
    pendingCount = 0,
    latestAnswered,
    onQuestionQueued,
}: ConsoleQueueCardProps) {
    const posthog = usePostHog();
    const trackedErrorIdRef = React.useRef<string | null>(null);
    const [userQuestion, setUserQuestion] = React.useState('');
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [submittedMessage, setSubmittedMessage] = React.useState<string | null>(null);
    const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

    const isOutage = isOutageFallbackResponse(latestAnswered?.agent_response);

    React.useEffect(() => {
        if (isOutage && latestAnswered?.id && trackedErrorIdRef.current !== latestAnswered.id) {
            trackedErrorIdRef.current = latestAnswered.id;

            const err = new Error(
                `Agent Q&A LLM Outage: All endpoints unavailable for question "${latestAnswered.message}"`,
            );
            err.name = 'AgentLLMOutageError';

            // 1. Explicit Error Tracking ($exception event)
            if (typeof posthog?.captureException === 'function') {
                posthog.captureException(err, {
                    feature: 'agent_chat_queue',
                    question: latestAnswered.message,
                    author: latestAnswered.display_name,
                    user_id: latestAnswered.user_id,
                    raw_response: latestAnswered.agent_response,
                    error_type: 'llm_endpoints_unavailable',
                });
            }

            // 2. Custom analytics event for dashboard trends
            posthog?.capture('agent_chat_endpoint_error', {
                question: latestAnswered.message,
                author: latestAnswered.display_name,
                user_id: latestAnswered.user_id,
                error_type: 'llm_endpoints_unavailable',
            });
        }
    }, [isOutage, latestAnswered, posthog]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = userQuestion.trim();
        if (!trimmed || isSubmitting) return;

        try {
            setIsSubmitting(true);
            setErrorMessage(null);
            await submitAgentQueueQuestion({ data: { message: trimmed } });
            setSubmittedMessage('Question queued. Injected during the next evaluation turn.');
            setUserQuestion('');
            if (onQuestionQueued) {
                onQuestionQueued();
            }
        } catch (err) {
            setErrorMessage(err instanceof Error ? err.message : 'Failed to submit question.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="voxel-trough p-3 flex flex-col gap-2.5 border border-accent/20">
            <div className="flex flex-wrap items-center justify-between gap-1">
                <span className="text-sm font-bold uppercase tracking-wider text-accent">
                    Audience Interactive Queue & Desk Explainer
                </span>
                <span className="text-xs font-normal font-mono text-boxel-muted">
                    {pendingCount > 0 ? `${pendingCount} in queue` : 'Queue open'}
                </span>
            </div>

            <p className="text-xs font-normal text-boxel-muted leading-normal">
                Ask the trader about past choices, current SPY positioning, or macroeconomic
                hypotheses (e.g. &ldquo;What do you think will happen after midterms?&rdquo;).
            </p>

            {!user ? (
                <div className="p-2.5 bg-boxel-elevated border border-boxel-bevel-hi flex flex-col gap-2">
                    <span className="text-xs font-normal font-mono text-boxel-muted">
                        🔒 Sign in to submit hypotheses and questions for the live model.
                    </span>
                    <div>
                        <a
                            href="/signup"
                            className="voxel-btn inline-block bg-accent text-accent-ink px-3 py-1.5 text-sm font-bold uppercase tracking-wider hover:opacity-90"
                        >
                            Sign In to Queue
                        </a>
                    </div>
                </div>
            ) : submittedMessage ? (
                <div className="flex flex-col gap-1 py-1">
                    <div className="text-sm font-bold font-mono text-success">
                        {submittedMessage}
                    </div>
                    <button
                        type="button"
                        onClick={() => setSubmittedMessage(null)}
                        className="text-xs font-normal font-mono text-boxel-muted hover:text-boxel-ink text-left underline"
                    >
                        Submit another hypothesis
                    </button>
                </div>
            ) : (
                <form onSubmit={handleSubmit} className="flex flex-col gap-1.5">
                    <div className="flex flex-wrap gap-2">
                        <textarea
                            value={userQuestion}
                            onChange={(e) => setUserQuestion(e.target.value)}
                            maxLength={MAX_QUEUE_MESSAGE_LENGTH}
                            rows={2}
                            placeholder="Ask a question or thesis hypothesis (max 500 chars)..."
                            className="voxel-input flex-1 min-w-48 px-3 py-1.5 text-xs font-normal bg-boxel-canvas text-boxel-ink border border-boxel-bevel-hi focus:outline-none focus:border-accent resize-none"
                        />
                        <button
                            type="submit"
                            disabled={isSubmitting || !userQuestion.trim()}
                            className="voxel-btn bg-accent text-accent-ink px-3 py-1.5 text-sm font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 self-end"
                        >
                            {isSubmitting ? 'Queuing...' : 'Queue'}
                        </button>
                    </div>

                    <div className="flex items-center justify-between text-xs font-normal font-mono text-boxel-muted px-0.5">
                        <span>Logged in as analyst</span>
                        <span
                            className={
                                userQuestion.length >= 480
                                    ? 'text-danger font-normal'
                                    : 'text-boxel-muted'
                            }
                        >
                            {userQuestion.length}/{MAX_QUEUE_MESSAGE_LENGTH}
                        </span>
                    </div>

                    {errorMessage && (
                        <div className="text-xs font-normal font-mono text-danger">
                            {errorMessage}
                        </div>
                    )}
                </form>
            )}

            {latestAnswered && (
                <AnsweredTurnView latestAnswered={latestAnswered} isOutage={isOutage} />
            )}
        </div>
    );
}
