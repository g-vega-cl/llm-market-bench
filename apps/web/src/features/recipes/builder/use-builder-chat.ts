import { usePostHog } from '@posthog/react';
import { useState } from 'react';
import { track } from '~/lib/analytics';
import { clearPendingIdea, loadPendingIdea, savePendingIdea } from '../utils/local-draft';
import type { BuilderMessage, CompilerReply } from './compiler';
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
    send: (text: string) => Promise<void>;
    reset: () => void;
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

    const pendingIdea = messages.length > 0 ? null : loadPendingIdea();

    const send = async (text: string) => {
        const trimmed = text.trim();
        if (!trimmed || isCompiling) return;

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
        setIsCompiling(true);
        setError(null);
        try {
            const result = await compileStrategyFn({ data: { messages: next } });
            setReply(result);
            if (result.status === 'question') {
                track(posthog, 'builder_question_answered');
                setMessages([...next, { role: 'assistant', content: result.question }]);
                setMessageIds((ids) => [...ids, `q${ids.length}-${Date.now()}`]);
            } else if (result.status === 'declined') {
                track(posthog, 'builder_declined');
            } else {
                track(posthog, 'builder_compiled', { cadence: result.strategy.cadence });
                clearPendingIdea();
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'The builder failed to answer');
        } finally {
            setIsCompiling(false);
        }
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
        send,
        reset,
    };
}
