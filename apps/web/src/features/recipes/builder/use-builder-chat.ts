import { usePostHog } from '@posthog/react';
import { useEffect, useRef, useState } from 'react';
import { track } from '~/lib/analytics';
import { assertServerFnResult } from '~/lib/server-fn';
import { clearPendingIdea, loadPendingIdea, savePendingIdea } from '../utils/local-draft';
import type { BuilderPhase } from './builder-phases';
import { type BuilderMessage, type CompilerReply, isCompilerReply } from './compiler';
import { compileStrategyFn } from './compiler-api';

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
    send: (text: string) => Promise<void>;
    retry: () => void;
    reset: () => void;
}

/**
 * The transport resolves to `undefined` (instead of throwing) when a server
 * function response is not a reply envelope — an edge 502, a cut-off request.
 * Reading `.status` off that used to surface a raw TypeError with no way
 * forward, so an unknown reply is now a legible, retryable message.
 */
const NO_REPLY_MESSAGE =
    'The builder did not get an answer back — the request was cut off before it finished. Nothing was queued; try again.';

/** One discrete phase: the lifecycle is derived, never a set of booleans. */
function derivePhase(args: {
    error: string | null;
    isCompiling: boolean;
    reply: CompilerReply | null;
    userId?: string | null;
}): BuilderPhase {
    if (args.error) return 'error';
    if (args.isCompiling) return 'compiling';
    if (args.reply) return args.reply.status === 'ok' ? 'ready' : args.reply.status;
    return args.userId ? 'idle' : 'signed-out';
}

/**
 * Builder conversation state: anonymous messages are parked locally and resumed
 * after sign-in, compiles are metered server-side, and every outcome is tracked.
 */
export function useBuilderChat({ idea, userId, onNeedSignIn }: UseBuilderChatArgs): BuilderChat {
    const posthog = usePostHog();
    const [messages, setMessages] = useState<BuilderMessage[]>(() =>
        idea ? [{ role: 'user', content: idea }] : [],
    );
    const [messageIds, setMessageIds] = useState<string[]>(() => (idea ? ['seed'] : []));
    const [draft, setDraft] = useState('');
    const [reply, setReply] = useState<CompilerReply | null>(null);
    const [isCompiling, setIsCompiling] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [elapsedMs, setElapsedMs] = useState(0);
    // A latch, not state: two clicks in one tick would both see isCompiling as
    // false and spend two metered compiles.
    const inFlight = useRef(false);

    const pendingIdea = messages.length > 0 ? null : loadPendingIdea();

    // Compiles run for seconds and can be cut short, so the strip counts up
    // while the request is in flight instead of leaving a dead button.
    useEffect(() => {
        if (!isCompiling) {
            setElapsedMs(0);
            return;
        }
        const startedAt = Date.now();
        const timer = setInterval(() => setElapsedMs(Date.now() - startedAt), 1000);
        return () => clearInterval(timer);
    }, [isCompiling]);

    const compile = async (conversation: BuilderMessage[]) => {
        if (inFlight.current) return;
        inFlight.current = true;
        setIsCompiling(true);
        setError(null);
        try {
            // The transport can hand back `undefined` for an envelope-less reply;
            // that has to fail here, not at the first property read.
            const result = assertServerFnResult(
                await compileStrategyFn({ data: { messages: conversation } }),
                'The builder',
            );
            if (!isCompilerReply(result)) {
                console.error('[builder] compile returned a malformed reply', result);
                setError(NO_REPLY_MESSAGE);
                return;
            }
            setReply(result);
            if (result.status === 'question') {
                track(posthog, 'builder_question_answered');
                setMessages([...conversation, { role: 'assistant', content: result.question }]);
                setMessageIds((ids) => [...ids, `q${ids.length}-${Date.now()}`]);
            } else if (result.status === 'declined') {
                track(posthog, 'builder_declined');
            } else {
                track(posthog, 'builder_compiled', {
                    cadence: result.strategy.cadence,
                    fallback: Boolean(result.fallback),
                });
                clearPendingIdea();
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'The builder failed to answer';
            track(posthog, 'builder_failed', { reason: message.slice(0, 120) });
            setError(message);
            // A failed compile has no reply to act on; the stale one would leave
            // question buttons alive beside a failure message.
            setReply(null);
        } finally {
            inFlight.current = false;
            setIsCompiling(false);
        }
    };

    const send = async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed || isCompiling || inFlight.current) return;

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
        await compile(next);
    };

    /** Re-run the last turn without appending a duplicate message. */
    const retry = () => {
        if (isCompiling || inFlight.current || messages.length === 0) return;
        void compile(messages);
    };

    const reset = () => {
        setMessages([]);
        setMessageIds([]);
        setDraft('');
        setReply(null);
        setError(null);
    };

    return {
        messages,
        messageIds,
        draft,
        setDraft,
        reply,
        isCompiling,
        error,
        pendingIdea,
        phase: derivePhase({ error, isCompiling, reply, userId }),
        elapsedMs,
        send,
        retry,
        reset,
    };
}
