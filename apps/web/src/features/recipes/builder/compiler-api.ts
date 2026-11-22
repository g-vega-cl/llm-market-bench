import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import {
    type BuilderMessage,
    buildConversation,
    type CompilerReply,
    fallbackReply,
    parseCompilerReply,
} from './compiler';

const DEFAULT_PROXY_URL = 'https://llm.clvg.uk/v1';
const MAX_MESSAGES = 8;
/** Each compile spends real proxy tokens, so it is capped like a backtest. */
export const BUILDER_DAILY_LIMIT = 25;

/**
 * The origin severs a synchronous server-function call somewhere between a 27.8s
 * success and a 30.1s Cloudflare 502 (measured on production), and the 502 body is
 * JSON with no reply envelope — which the Start client silently unwraps to
 * `undefined`. So the whole compile has to finish inside that ceiling with margin
 * for the handler, seroval and the network.
 *
 * One attempt gets the budget. A provider that could not answer in 24s will not
 * answer in the 3s a retry would have left, so a timeout goes straight to the
 * template instead of spending a second provider call and more of the user's time.
 * Cheap failures (invalid JSON, 429, 5xx) still get a second attempt.
 */
export const BUILDER_BUDGET_MS = 24_000;
/** Below this there is no useful retry window, so don't start one. */
export const BUILDER_MIN_RETRY_MS = 3_000;
const SLOW_PROVIDER_NOTE =
    'The free model was too slow to answer in time, so here is the closest working recipe. Edit it and run it.';

/** Milliseconds the next attempt may use, or 0 when the budget is spent. */
export function attemptBudget(remainingMs: number): number {
    return remainingMs >= BUILDER_MIN_RETRY_MS ? remainingMs : 0;
}

/** `AbortSignal.timeout` rejects with a DOMException: not an Error on every runtime. */
export function failureText(error: unknown): string {
    if (error instanceof Error) return error.message;
    if (typeof error === 'object' && error !== null && 'message' in error) {
        return String((error as { message: unknown }).message);
    }
    return String(error ?? '');
}

export function isTimeoutFailure(text: string): boolean {
    return /timeout|timed out|abort/i.test(text);
}

function proxyUrl(): string {
    return (process.env.FREE_LLM_PROXY_URL || DEFAULT_PROXY_URL).replace(/\/$/, '');
}

function proxyKey(): string {
    return process.env.FREE_PROXY_MASTER_KEY || process.env.STRATA_API_KEY || 'local';
}

async function callProxy(messages: BuilderMessage[], signal: AbortSignal): Promise<string> {
    const response = await fetch(`${proxyUrl()}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${proxyKey()}`,
        },
        body: JSON.stringify({
            model: 'auto-go',
            temperature: 0.2,
            messages: buildConversation(messages.slice(-MAX_MESSAGES)),
        }),
        // Bounded by the caller's budget so a hung provider cannot hold the
        // request handler open past the origin's own timeout.
        signal,
    });
    if (!response.ok) {
        throw new Error(`Builder model call failed (${response.status})`);
    }
    const payload = (await response.json()) as {
        choices?: Array<{ message?: { content?: string | null } }>;
    };
    const content = payload.choices?.[0]?.message?.content;
    if (!content) throw new Error('Builder model returned an empty reply');
    return content;
}

/**
 * Turn a conversation into a validated recipe. The model never edits the graph
 * freehand: whatever it returns is re-validated here, and invalid replies degrade
 * to a starter template rather than a dead end.
 */
export async function compileStrategy(messages: BuilderMessage[]): Promise<CompilerReply> {
    const deadline = Date.now() + BUILDER_BUDGET_MS;
    let lastError: unknown = null;

    for (let attempt = 0; attempt < 2; attempt += 1) {
        const budget = attemptBudget(deadline - Date.now());
        if (budget === 0) break;
        try {
            const raw = await callProxy(
                attempt === 0
                    ? messages
                    : [
                          ...messages,
                          {
                              role: 'assistant' as const,
                              content: failureText(lastError),
                          },
                          {
                              role: 'user' as const,
                              content: 'That reply was invalid. Return the strict JSON shape only.',
                          },
                      ],
                AbortSignal.timeout(budget),
            );
            return parseCompilerReply(raw);
        } catch (error) {
            lastError = error;
            // A provider that missed the whole budget will not make a 3s window.
            if (isTimeoutFailure(failureText(error))) break;
        }
    }

    return fallbackReply(
        isTimeoutFailure(failureText(lastError))
            ? SLOW_PROVIDER_NOTE
            : 'We could not build that idea exactly, so here is the closest working recipe. Edit it and run it.',
    );
}

export const compileStrategyFn = createServerFn({ method: 'POST' })
    .validator((d: { messages: BuilderMessage[] }) => d)
    .handler(async ({ data: { messages } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: sign in to build a recipe');
        }
        if (!Array.isArray(messages) || messages.length === 0) {
            throw new Error('Describe your strategy first');
        }

        const db = getDbAdminClient();
        const { data: used, error: usageError } = await db.rpc('consume_builder_compile', {
            p_user: user.id,
        });
        if (usageError) throw new Error(usageError.message);
        if (typeof used === 'number' && used > BUILDER_DAILY_LIMIT) {
            throw new Error(
                `Daily builder limit reached (${BUILDER_DAILY_LIMIT} compiles). Edit an existing recipe or come back tomorrow.`,
            );
        }

        return compileStrategy(messages);
    });
