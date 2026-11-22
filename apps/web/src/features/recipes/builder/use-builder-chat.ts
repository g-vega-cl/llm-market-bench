import { usePostHog } from '@posthog/react';
import { useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { track } from '~/lib/analytics';
import { assertServerFnResult } from '~/lib/server-fn';
import { clearPendingIdea, loadPendingIdea, savePendingIdea } from '../utils/local-draft';
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
    parseCompilerReply,
} from './compiler';

export interface UseBuilderChatArgs {
    idea?: string;
    userId?: string | null;
    onNeedSignIn: (idea: string) => Promise<void>;
}

export interface BuilderChat {
    messages: BuilderMessage[];
    messageIds: string[];
    draft: string;
    setDraft: (value: string) => void;
    reply: CompilerReply | null;
    isCompiling: boolean;
    error: string | null;
    pendingIdea: string | null;
    phase: BuilderPhase;
    elapsedMs: number;
    /** Extra strip copy for a job that is sitting unclaimed; null until it matters. */
    statusDetail: string | null;
    send: (text: string) => Promise<void>;
    retry: () => void;
    /** Explicit escape hatch from a failed compile: drop in the closest template. */
    useTemplate: () => void;
    reset: () => void;
}

/**
 * The transport resolves to `undefined` (instead of throwing) when a server
 * function response is not a reply envelope — an edge 502, a cut-off request.
 * Reading `.status` off that used to surface a raw TypeError with no way
 * forward, so an unknown payload is now a legible, retryable message.
 */
const NO_REPLY_MESSAGE =
    'The builder did not get an answer back — the request was cut off before it finished. Nothing was queued; try again.';
const FAILED_MESSAGE = 'The builder failed to answer. Try again, or use the closest template.';
const UNUSABLE_REPLY =
    'The model replied with something the engine cannot run, so here is the closest working recipe. Edit it and run it.';
const ABANDONED_MESSAGE =
    'The builder never picked this request up, so it was cancelled. Try again — nothing was spent on it.';

function isInFlight(status: string | undefined): boolean {
    return status === 'pending' || status === 'processing';
}

/** One discrete phase: the lifecycle is derived, never a set of booleans. */
function derivePhase(args: {
    error: string | null;
    jobStatus: string | undefined;
    reply: CompilerReply | null;
    userId?: string | null;
}): BuilderPhase {
    if (args.error) return 'error';
    if (args.jobStatus === 'pending') return 'queued';
    if (args.jobStatus === 'processing') return 'compiling';
    if (args.reply) return args.reply.status === 'ok' ? 'ready' : args.reply.status;
    return args.userId ? 'idle' : 'signed-out';
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
    const [error, setError] = useState<string | null>(null);
    const [jobId, setJobId] = useState<string | null>(null);
    const [elapsedMs, setElapsedMs] = useState(0);
    // A latch, not state: two clicks in one tick must not enqueue two compiles.
    const inFlight = useRef(false);
    // Mirrors `elapsedMs` for the poll interval, which cannot read render state.
    const elapsedRef = useRef(0);
    elapsedRef.current = elapsedMs;

    const pendingIdea = messages.length > 0 ? null : loadPendingIdea();

    const job = useQuery({
        queryKey: ['builder-compile', jobId],
        queryFn: async () => {
            const result = await fetchCompileJobFn({ data: { jobId: jobId as string } });
            // An envelope-less reply resolves to `undefined`; throwing keeps the
            // last known job state and lets the poll retry instead of crashing.
            return assertServerFnResult(result, 'The builder');
        },
        enabled: Boolean(jobId),
        refetchInterval: (q) => {
            if (!isInFlight(q.state.data?.status)) return false;
            // Stop hammering the server once the client has given up; the abandon
            // effect below then cancels the row and frees the per-user cap.
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
            setReply(next);
            if (next.status === 'ok') {
                track(posthog, 'builder_compiled', {
                    cadence: next.strategy.cadence,
                    fallback: Boolean(next.fallback),
                });
                clearPendingIdea();
            } else if (next.status === 'question') {
                track(posthog, 'builder_question_answered');
                setMessages((prev) => [...prev, { role: 'assistant', content: next.question }]);
                setMessageIds((ids) => [...ids, `q${ids.length}-${Date.now()}`]);
            } else {
                track(posthog, 'builder_declined');
            }
        },
        [posthog],
    );

    const fail = useCallback(
        (message: string) => {
            track(posthog, 'builder_failed', { reason: message.slice(0, 120) });
            setError(message);
            // A failed compile has no reply to act on; a stale one would leave question
            // buttons alive beside a failure message.
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
                fail(data.error_message || FAILED_MESSAGE);
                return;
            }
            const content = data.result_json?.content;
            if (!content) {
                fail(NO_REPLY_MESSAGE);
                return;
            }
            try {
                const parsed = parseCompilerReply(content);
                if (!isCompilerReply(parsed)) throw new Error('malformed reply');
                finish(parsed);
            } catch {
                // Degrade instead of dead-ending: the visitor still leaves with a bot.
                finish(fallbackReply(UNUSABLE_REPLY));
            }
        },
        [fail, finish],
    );

    // Settle exactly once, when the polled job reaches a terminal state, and on a
    // failed poll itself.
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
        fail(job.error instanceof Error ? job.error.message : NO_REPLY_MESSAGE);
        inFlight.current = false;
        setJobId(null);
    }, [job.error, fail]);

    // Give up on a job no worker ever claimed: cancel the row so it stops holding
    // the 2-pending cap, then tell the user instead of counting up forever. The
    // daemon's stale sweep is the backstop for a tab that was closed instead.
    useEffect(() => {
        if (!jobId || !isQueueAbandoned(elapsedMs)) return;
        const abandoned = jobId;
        inFlight.current = false;
        setJobId(null);
        fail(ABANDONED_MESSAGE);
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
            fail(err instanceof Error ? err.message : 'The builder failed to answer');
        }
    };

    const send = async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed || inFlight.current) return;

        // Anonymous visitors may type freely, but compiles spend tokens, so the
        // conversation is parked locally and resumed after sign-in.
        if (!userId) {
            savePendingIdea(trimmed);
            await onNeedSignIn(trimmed);
            return;
        }

        const next: BuilderMessage[] = [...messages, { role: 'user', content: trimmed }];
        setMessages(next);
        setMessageIds((ids) => [...ids, `m${ids.length}-${Date.now()}`]);
        setDraft('');
        await requestCompile(next);
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
        setError(null);
        setJobId(null);
        inFlight.current = false;
    };

    return {
        messages,
        messageIds,
        draft,
        setDraft,
        reply,
        isCompiling: Boolean(jobId),
        error,
        pendingIdea,
        phase: derivePhase({ error, jobStatus: job.data?.status, reply, userId }),
        elapsedMs,
        statusDetail: jobId && isInFlight(job.data?.status) ? queuedHint(elapsedMs) : null,
        send,
        retry,
        useTemplate,
        reset,
    };
}
