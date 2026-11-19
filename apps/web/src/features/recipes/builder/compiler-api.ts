import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import {
    type BuilderMessage,
    buildConversation,
    fallbackReply,
    parseCompilerReply,
} from './compiler';

const DEFAULT_PROXY_URL = 'https://llm.clvg.uk/v1';
const MAX_MESSAGES = 8;
/** Each compile spends real proxy tokens, so it is capped like a backtest. */
export const BUILDER_DAILY_LIMIT = 25;

function proxyUrl(): string {
    return (process.env.FREE_LLM_PROXY_URL || DEFAULT_PROXY_URL).replace(/\/$/, '');
}

function proxyKey(): string {
    return process.env.FREE_PROXY_MASTER_KEY || process.env.STRATA_API_KEY || 'local';
}

async function callProxy(messages: BuilderMessage[]): Promise<string> {
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
        // A hung free-tier provider must not hold the request handler open.
        signal: AbortSignal.timeout(45_000),
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
 * freehand: whatever it returns is re-validated here, and two invalid replies
 * degrade to a starter template rather than a dead end.
 */
export async function compileStrategy(messages: BuilderMessage[]) {
    let lastError: unknown = null;
    for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
            const raw = await callProxy(
                attempt === 0
                    ? messages
                    : [
                          ...messages,
                          {
                              role: 'assistant' as const,
                              content: String(lastError instanceof Error ? lastError.message : ''),
                          },
                          {
                              role: 'user' as const,
                              content: 'That reply was invalid. Return the strict JSON shape only.',
                          },
                      ],
            );
            return parseCompilerReply(raw);
        } catch (error) {
            lastError = error;
        }
    }
    return fallbackReply(
        'We could not build that idea exactly, so here is the closest working recipe. Edit it and run it.',
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
