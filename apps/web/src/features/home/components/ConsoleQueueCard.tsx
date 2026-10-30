import * as React from 'react';
import {
    type AgentQueueItem,
    MAX_QUEUE_MESSAGE_LENGTH,
    submitAgentQueueQuestion,
} from '../api/fetch-agent-queue';

export interface ConsoleQueueCardProps {
    user?: { id: string; email?: string } | null;
    pendingCount?: number;
    latestAnswered?: AgentQueueItem | null;
    onQuestionQueued?: () => void;
}

export function ConsoleQueueCard({
    user,
    pendingCount = 0,
    latestAnswered,
    onQuestionQueued,
}: ConsoleQueueCardProps) {
    const [userQuestion, setUserQuestion] = React.useState('');
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [submittedMessage, setSubmittedMessage] = React.useState<string | null>(null);
    const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

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
                <span className="text-xs font-black uppercase tracking-wider text-accent">
                    Audience Interactive Queue
                </span>
                <span className="text-xs font-mono text-boxel-muted">
                    {pendingCount > 0 ? `${pendingCount} in queue` : 'Queue open'}
                </span>
            </div>

            <p className="text-xs text-boxel-muted leading-normal">
                Submit questions or hypotheses to inject into the model&apos;s next 5-minute
                thinking turn.
            </p>

            {!user ? (
                <div className="p-2.5 bg-boxel-elevated border border-boxel-bevel-hi flex flex-col gap-2">
                    <span className="text-xs font-mono text-boxel-muted">
                        🔒 Sign in to submit hypotheses and questions for the live model.
                    </span>
                    <div>
                        <a
                            href="/signup"
                            className="voxel-btn inline-block bg-accent text-accent-ink px-3 py-1.5 text-xs font-black uppercase tracking-wider hover:opacity-90"
                        >
                            Sign In to Queue
                        </a>
                    </div>
                </div>
            ) : submittedMessage ? (
                <div className="flex flex-col gap-1 py-1">
                    <div className="text-xs font-mono text-success font-bold">
                        {submittedMessage}
                    </div>
                    <button
                        type="button"
                        onClick={() => setSubmittedMessage(null)}
                        className="text-[10px] font-mono text-boxel-muted hover:text-boxel-ink text-left underline"
                    >
                        Submit another hypothesis
                    </button>
                </div>
            ) : (
                <form onSubmit={handleSubmit} className="flex flex-col gap-1.5 mt-0.5">
                    <div className="flex flex-wrap gap-2">
                        <textarea
                            value={userQuestion}
                            onChange={(e) => setUserQuestion(e.target.value)}
                            maxLength={MAX_QUEUE_MESSAGE_LENGTH}
                            rows={2}
                            placeholder="Ask a question or thesis hypothesis (max 500 chars)..."
                            className="voxel-input flex-1 min-w-48 px-3 py-1.5 text-xs bg-boxel-canvas text-boxel-ink border border-boxel-bevel-hi focus:outline-none focus:border-accent resize-none"
                        />
                        <button
                            type="submit"
                            disabled={isSubmitting || !userQuestion.trim()}
                            className="voxel-btn bg-accent text-accent-ink px-3 py-1.5 text-xs font-black uppercase tracking-widest hover:opacity-90 disabled:opacity-50 self-end"
                        >
                            {isSubmitting ? 'Queuing...' : 'Queue'}
                        </button>
                    </div>

                    <div className="flex items-center justify-between text-[10px] font-mono text-boxel-muted px-0.5">
                        <span>Logged in as analyst</span>
                        <span
                            className={
                                userQuestion.length >= 480
                                    ? 'text-danger font-bold'
                                    : 'text-boxel-muted'
                            }
                        >
                            {userQuestion.length}/{MAX_QUEUE_MESSAGE_LENGTH}
                        </span>
                    </div>

                    {errorMessage && (
                        <div className="text-[11px] font-mono text-danger">{errorMessage}</div>
                    )}
                </form>
            )}

            {latestAnswered && (
                <div className="border-t border-boxel-bevel-hi/60 pt-2 flex flex-col gap-1 text-xs">
                    <div className="flex items-center justify-between text-boxel-muted font-mono text-[10px]">
                        <span>Latest Answered Turn:</span>
                        <span>@{latestAnswered.display_name}</span>
                    </div>
                    <div className="font-mono text-boxel-ink text-xs line-clamp-2">
                        &ldquo;{latestAnswered.message}&rdquo;
                    </div>
                    {latestAnswered.agent_response && (
                        <div className="text-accent text-[11px] leading-relaxed italic bg-accent/5 p-2 border border-accent/20">
                            &ldquo;{latestAnswered.agent_response}&rdquo;
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
