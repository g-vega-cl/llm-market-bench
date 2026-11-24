import { usePostHog } from '@posthog/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { track } from '~/lib/analytics';
import { assertServerFnResult } from '~/lib/server-fn';
import { clearPendingIdea, loadPendingIdea, savePendingIdea } from '../utils/local-draft';
import type { AlignmentAnswerEntry } from './BuilderAlignmentCard';
import type { BuilderPhase } from './builder-phases';
import {
    cancelCompileFn,
    enqueueCompileFn,
    fetchCompileJobFn,
    isQueueAbandoned,
    queuedHint,
} from './compile-queue';
import {
    type BuilderMessage,
    type CompilerReply,
    fallbackReply,
    isCompilerReply,
    isNonTradingRefusal,
    MAX_ASSISTANT_TURN_CHARS,
    MAX_TURN_CHARS,
    parseCompilerReply,
    promoteDeclinedToBot,
} from './compiler';

/**
 * Short, bounded failure taxonomy. `reason` keeps the human message for debugging,
 * but the insight breaks down on this code — a 120-char message string as a
 * breakdown value produces one row per distinct sentence.
 */
export type BuilderFailureCode = 'no_reply' | 'job_failed' | 'enqueue_rejected' | 'abandoned';

export interface UseBuilderChatArgs {
    idea?: string;
    userId?: string | null;
    onNeedSignIn: (idea: string) => Promise<void>;
}

export type AlignmentPromptReply = Extract<CompilerReply, { status: 'align' }>;

export interface BuilderChat {
    messages: BuilderMessage[];
    messageIds: string[];
    draft: string;
    setDraft: (value: string) => void;
    reply: CompilerReply | null;
    /** Preserved across alignment compile retries/errors so selections are never lost. */
    activeAlignment: AlignmentPromptReply | null;
    /** Incremented on every compiled bot result to guarantee fresh workspace mounts. */
    compileNonce: number;
    isCompiling: boolean;
    error: string | null;
    pendingIdea: string | null;
    restoredFromBrowser: boolean;
    phase: BuilderPhase;
    elapsedMs: number;
    /** Extra strip copy for a job that is sitting unclaimed; null until it matters. */
    statusDetail: string | null;
    send: (text: string) => Promise<void>;
    submitAlignment: (answers: AlignmentAnswerEntry[]) => Promise<void>;
    skipAlignment: () => Promise<void>;
    retry: () => void;
    /** Explicit escape hatch from a failed compile: drop in the closest template. */
    useTemplate: () => void;
    reset: () => void;
}

const NO_REPLY_MESSAGE =
    'The builder did not get an answer back — the request was cut off before it finished. Nothing was queued; try again.';
const FAILED_MESSAGE = 'The builder failed to answer. Try again, or use the closest template.';
const UNUSABLE_REPLY =
    'The model replied with something the engine cannot run, so here is the closest working recipe. Edit it and run it.';
const ABANDONED_MESSAGE =
    'The builder never picked this request up, so it was cancelled. Try again — nothing was spent on it.';

function formatAlignmentTranscript(reply: AlignmentPromptReply): string {
    const lines = [
        reply.intro ? reply.intro : 'Alignment questions:',
        ...reply.questions.map((q, idx) => `${idx + 1}. ${q.question}`),
    ];
    return lines.join('\n').slice(0, MAX_ASSISTANT_TURN_CHARS);
}

function formatAlignmentAnswersTurn(entries: AlignmentAnswerEntry[]): string {
    const lines = entries.map(
        ({ question, answer }) => `- ${question.slice(0, 120)}: ${answer.slice(0, 120)}`,
    );
    return [
        'Alignment choices:',
        ...lines,
        'Compile the final bot now with a clear prompt block first.',
    ]
        .join('\n')
        .slice(0, MAX_TURN_CHARS);
}

function resolveConversationBase(args: {
    messages: BuilderMessage[];
    messageIds: string[];
    reply: CompilerReply | null;
    activeAlignment: AlignmentPromptReply | null;
}): { baseMessages: BuilderMessage[]; baseIds: string[] } {
    if (args.reply?.status === 'declined') {
        return { baseMessages: [], baseIds: [] };
    }
    const retryingAlignment =
        Boolean(args.activeAlignment) && args.messages[args.messages.length - 1]?.role === 'user';
    if (retryingAlignment) {
        return {
            baseMessages: args.messages.slice(0, -1),
            baseIds: args.messageIds.slice(0, -1),
        };
    }
    return { baseMessages: args.messages, baseIds: args.messageIds };
}

function isInFlight(status: string | undefined): boolean {
    return status === 'pending' || status === 'processing';
}

/** One discrete phase: the lifecycle is derived, never a set of booleans. */
function derivePhase(args: {
    error: string | null;
    jobStatus: string | undefined;
    reply: CompilerReply | null;
    activeAlignment: AlignmentPromptReply | null;
    userId?: string | null;
    hasPendingIdea: boolean;
}): BuilderPhase {
    if (args.error) return 'error';
    if (args.jobStatus === 'pending') return 'queued';
    if (args.jobStatus === 'processing') return 'compiling';
    if (args.reply) return args.reply.status === 'ok' ? 'ready' : args.reply.status;
    if (args.activeAlignment) return 'align';
    if (!args.userId && args.hasPendingIdea) return 'signed-out';
    return 'idle';
}

/**
 * Builder conversation state. Compiles are queued (see compile-queue.ts): `send`
 * enqueues a job, this hook polls it, and the reply is parsed and validated here
 * when it lands — so the model contract lives in exactly one place.
 */
export function useBuilderChat({ idea, userId, onNeedSignIn }: UseBuilderChatArgs): BuilderChat {
    const posthog = usePostHog();
    const [messages, setMessages] = useState<BuilderMessage[]>(() =>
        idea ? [{ role: 'user', content: idea }] : [],
    );
    const [messageIds, setMessageIds] = useState<string[]>(() => (idea ? ['seed'] : []));
    const [draft, setDraft] = useState('');
    const [reply, setReply] = useState<CompilerReply | null>(null);
    const [activeAlignment, setActiveAlignment] = useState<AlignmentPromptReply | null>(null);
    const [compileNonce, setCompileNonce] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [elapsedMs, setElapsedMs] = useState(0);
    const [parkedIdea, setParkedIdea] = useState<string | null>(null);
    const [restoredFromBrowser, setRestoredFromBrowser] = useState(false);
    // A latch, not state: two clicks in one tick must not enqueue two compiles.
    const inFlight = useRef(false);
    // Mirrors `elapsedMs` for the poll interval, which cannot read render state.
    const elapsedRef = useRef(0);
    elapsedRef.current = elapsedMs;
    const hasAlignedRef = useRef(false);

    // Hydrate after mount so SSR and initial client paint stay identical.
    // Signed-in users get their saved idea pre-filled into the main textarea
    // (one input + one CTA); signed-out visitors keep the parked sign-in card.
    useEffect(() => {
        const saved = loadPendingIdea();
        if (!saved) {
            setParkedIdea(null);
            setRestoredFromBrowser(false);
            return;
        }
        if (userId) {
            setParkedIdea(null);
            if (!idea) {
                setDraft((prev) => (prev ? prev : saved));
                setRestoredFromBrowser(true);
            }
            return;
        }
        setParkedIdea(saved);
        setRestoredFromBrowser(false);
    }, [userId, idea]);

    const pendingIdea = messages.length > 0 || userId ? null : parkedIdea;

    const updateDraft = useCallback((value: string) => {
        setDraft(value);
        if (!value) {
            setRestoredFromBrowser(false);
            clearPendingIdea();
            setParkedIdea(null);
        }
    }, []);

    const job = useQuery({
        queryKey: ['builder-compile', jobId],
        queryFn: async () => {
            const result = await fetchCompileJobFn({ data: { jobId: jobId as string } });
            return assertServerFnResult(result, 'The builder');
        },
        enabled: Boolean(jobId),
        refetchInterval: (q) => {
            if (!isInFlight(q.state.data?.status)) return false;
            if (isQueueAbandoned(elapsedRef.current)) return false;
            return 2000;
        },
    });

    // The strip counts up from the moment the job is queued.
    useEffect(() => {
        if (!jobId) {
            setElapsedMs(0);
            return;
        }
        const startedAt = Date.now();
        const timer = setInterval(() => setElapsedMs(Date.now() - startedAt), 1000);
        return () => clearInterval(timer);
    }, [jobId]);

    const finish = useCallback(
        (next: CompilerReply) => {
            // Guard against a second alignment round: at most one alignment round per session.
            // Trading ideas that came back as `declined` (e.g. offline toolset gaps) are
            // promoted to a runnable bot with a warning advising Live execution instead of blocking.
            let resolved: CompilerReply = next;
            if (next.status === 'align' && hasAlignedRef.current) {
                resolved = fallbackReply(UNUSABLE_REPLY);
            } else if (next.status === 'declined' && !isNonTradingRefusal(next)) {
                resolved = promoteDeclinedToBot(next);
            }

            setReply(resolved);
            if (resolved.status === 'ok') {
                setActiveAlignment(null);
                setCompileNonce((n) => n + 1);
                track(posthog, 'builder_compiled', {
                    cadence: resolved.strategy.cadence,
                    fallback: Boolean(resolved.fallback),
                });
                clearPendingIdea();
                setParkedIdea(null);
            } else if (resolved.status === 'align') {
                hasAlignedRef.current = true;
                setActiveAlignment(resolved);
                track(posthog, 'builder_alignment_shown', {
                    question_count: resolved.questions.length,
                });
                const transcript = formatAlignmentTranscript(resolved);
                setMessages((prev) => [...prev, { role: 'assistant', content: transcript }]);
                setMessageIds((ids) => [...ids, `a${ids.length}-${Date.now()}`]);
            } else if (resolved.status === 'question') {
                track(posthog, 'builder_question_answered');
                setMessages((prev) => [...prev, { role: 'assistant', content: resolved.question }]);
                setMessageIds((ids) => [...ids, `q${ids.length}-${Date.now()}`]);
            } else {
                setActiveAlignment(null);
                track(posthog, 'builder_declined');
            }
        },
        [posthog],
    );

    const fail = useCallback(
        (message: string, code: BuilderFailureCode) => {
            track(posthog, 'builder_failed', {
                reason_code: code,
                reason: message.slice(0, 120),
            });
            setError(message);
            setReply(null);
        },
        [posthog],
    );

    const settle = useCallback(
        (data: {
            status: string;
            result_json: { content?: string } | null;
            error_message: string | null;
        }) => {
            if (data.status === 'failed' || data.status === 'cancelled') {
                fail(data.error_message || FAILED_MESSAGE, 'job_failed');
                return;
            }
            const content = data.result_json?.content;
            if (!content) {
                fail(NO_REPLY_MESSAGE, 'no_reply');
                return;
            }
            try {
                const parsed = parseCompilerReply(content);
                if (!isCompilerReply(parsed)) throw new Error('malformed reply');
                finish(parsed);
            } catch {
                finish(fallbackReply(UNUSABLE_REPLY));
            }
        },
        [fail, finish],
    );

    const settledJobId = useRef<string | null>(null);
    useEffect(() => {
        if (!jobId || !job.data || isInFlight(job.data.status)) return;
        if (settledJobId.current === jobId) return;
        settledJobId.current = jobId;
        settle(job.data);
        inFlight.current = false;
        setJobId(null);
    }, [jobId, job.data, settle]);

    useEffect(() => {
        if (!job.error) return;
        fail(job.error instanceof Error ? job.error.message : NO_REPLY_MESSAGE, 'no_reply');
        inFlight.current = false;
        setJobId(null);
    }, [job.error, fail]);

    useEffect(() => {
        if (!jobId || !isQueueAbandoned(elapsedMs)) return;
        const abandoned = jobId;
        inFlight.current = false;
        setJobId(null);
        fail(ABANDONED_MESSAGE, 'abandoned');
        void cancelCompileFn({ data: { jobId: abandoned } }).catch(() => {
            // Best effort: the sweep fails the row within ten minutes regardless.
        });
    }, [jobId, elapsedMs, fail]);

    const requestCompile = async (conversation: BuilderMessage[]) => {
        if (inFlight.current) return;
        inFlight.current = true;
        setError(null);
        try {
            const { jobId: queued } = await enqueueCompileFn({ data: { messages: conversation } });
            setJobId(queued);
        } catch (err) {
            inFlight.current = false;
            fail(
                err instanceof Error ? err.message : 'The builder failed to answer',
                'enqueue_rejected',
            );
        }
    };

    const send = async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed || inFlight.current) return;

        if (!userId) {
            savePendingIdea(trimmed);
            setParkedIdea(trimmed);
            await onNeedSignIn(trimmed);
            return;
        }

        // After a decline, start fresh; if re-submitting alignment after a failure,
        // replace the failed trailing user turn so strict user/assistant alternation holds.
        const { baseMessages, baseIds } = resolveConversationBase({
            messages,
            messageIds,
            reply,
            activeAlignment,
        });

        const next: BuilderMessage[] = [...baseMessages, { role: 'user', content: trimmed }];
        setMessages(next);
        setMessageIds([...baseIds, `m${baseIds.length}-${Date.now()}`]);
        setReply(null);
        setDraft('');
        setRestoredFromBrowser(false);
        await requestCompile(next);
    };

    const submitAlignment = async (answers: AlignmentAnswerEntry[]) => {
        await send(formatAlignmentAnswersTurn(answers));
    };

    const skipAlignment = async () => {
        await send(
            'Skip alignment and compile the final bot now with sensible defaults based on my instructions.',
        );
    };

    /** Re-run the last turn without appending a duplicate message. */
    const retry = () => {
        if (inFlight.current || messages.length === 0) return;
        void requestCompile(messages);
    };

    /** Explicit fallback: a working starter recipe, never a dead end. */
    const useTemplate = () => {
        setError(null);
        finish(fallbackReply(UNUSABLE_REPLY));
    };

    const reset = () => {
        setMessages([]);
        setMessageIds([]);
        setDraft('');
        setReply(null);
        setActiveAlignment(null);
        hasAlignedRef.current = false;
        setError(null);
        setJobId(null);
        inFlight.current = false;
        clearPendingIdea();
        setParkedIdea(null);
        setRestoredFromBrowser(false);
    };

    return {
        messages,
        messageIds,
        draft,
        setDraft: updateDraft,
        reply,
        activeAlignment,
        compileNonce,
        isCompiling: Boolean(jobId),
        error,
        pendingIdea,
        restoredFromBrowser,
        phase: derivePhase({
            error,
            jobStatus: job.data?.status,
            reply,
            activeAlignment,
            userId,
            hasPendingIdea: Boolean(pendingIdea),
        }),
        elapsedMs,
        statusDetail: jobId && isInFlight(job.data?.status) ? queuedHint(elapsedMs) : null,
        send,
        submitAlignment,
        skipAlignment,
        retry,
        useTemplate,
        reset,
    };
}
