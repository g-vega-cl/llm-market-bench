import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import recipeCompileJson from '../../../../../../packages/config/recipe-compile.json';
import {
    type BuilderMessage,
    buildConversation,
    MAX_CONVERSATION_MESSAGES,
    sanitizeCompileResult,
    validateBuilderMessages,
} from './compiler';

/**
 * /build compiles are queued, not executed in the request: the edge severs a
 * synchronous server function around 28-30s, and the free provider regularly needs
 * longer. The row is picked up by the recipes daemon (`apps/engine/recipes/runner.py`,
 * 5s poll, MiniPC) which executes the stored request and writes the raw reply.
 *
 * The prompt, capability manifest and all validation stay here in TS — the daemon
 * never knows what a recipe is, so there is nothing to drift.
 */
export const BUILDER_DAILY_LIMIT = 25;
export const BUILDER_BURST_LIMIT = 5;
export const BUILDER_BURST_WINDOW_MINUTES = 5;
/** Single-flight per-user concurrency lock: 1 active compile at a time. */
export const MAX_PENDING_COMPILES = 1;
// Shared with apps/engine/recipes/worker.py via packages/config/recipe-compile.json.
export const COMPILE_MAX_TOKENS: number = (recipeCompileJson as { compileMaxTokens: number })
    .compileMaxTokens;
/** A queued job this old gets an honest "worker is busy" line in the strip. */
export const QUEUE_SLOW_MS = 60_000;
/** Past this the client gives up, cancels the row and offers Try again. */
export const QUEUE_ABANDON_MS = 300_000;
const MAX_MESSAGES = MAX_CONVERSATION_MESSAGES;
const MAX_JOB_ID_CHARS = 128;
const JOB_COLUMNS = 'id, status, progress_pct, result_json, error_message';

export interface CompileJob {
    id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
    progress_pct: number | null;
    result_json: { content?: string } | null;
    error_message: string | null;
}

export function builderLimitMessage(): string {
    return `Daily builder limit reached (${BUILDER_DAILY_LIMIT} compiles). Edit an existing recipe or come back tomorrow.`;
}

export function pendingCompilesMessage(): string {
    return MAX_PENDING_COMPILES === 1
        ? 'You already have a compile in flight. Wait for it to finish, then try again.'
        : `You already have ${MAX_PENDING_COMPILES} compiles in flight. Wait for one to finish, then try again.`;
}

export function builderBurstLimitMessage(): string {
    return `Too many build requests (${BUILDER_BURST_LIMIT} in ${BUILDER_BURST_WINDOW_MINUTES} minutes). Wait a few minutes and try again.`;
}

/** Strip copy while a job sits unclaimed; null until it is worth saying. */
export function queuedHint(elapsedMs: number): string | null {
    if (elapsedMs < QUEUE_SLOW_MS) return null;
    return 'still queued — the worker is busy. This is cancelled automatically after 5 minutes, and a stuck job is cleared from your quota after 10.';
}

export function isQueueAbandoned(elapsedMs: number): boolean {
    return elapsedMs >= QUEUE_ABANDON_MS;
}

function todayUtc(): string {
    return new Date().toISOString().slice(0, 10);
}

function validateJobId(value: unknown): string {
    if (typeof value !== 'string') {
        throw new Error('Invalid compile job ID');
    }
    const trimmed = value.trim();
    if (!trimmed || trimmed.length > MAX_JOB_ID_CHARS) {
        throw new Error('Invalid compile job ID');
    }
    return trimmed;
}

/** Build the server-locked LLM request body; the daemon enforces & posts it. */
export function buildCompilePayload(messages: BuilderMessage[]) {
    return {
        model: 'auto-go',
        temperature: 0.2,
        max_tokens: COMPILE_MAX_TOKENS,
        response_format: { type: 'json_object' as const },
        messages: buildConversation(messages.slice(-MAX_MESSAGES)),
    };
}

export async function enqueueCompile(userId: string, messages: BuilderMessage[]): Promise<string> {
    const validatedMessages = validateBuilderMessages(messages);

    const db = getDbAdminClient();

    const { data: usage } = await db
        .from('recipe_builder_usage')
        .select('compiles')
        .eq('user_id', userId)
        .eq('usage_day', todayUtc())
        .maybeSingle();
    const compiles = Number((usage as { compiles?: number } | null)?.compiles ?? 0);
    if (compiles >= BUILDER_DAILY_LIMIT) {
        throw new Error(builderLimitMessage());
    }

    const { data: pending, error: pendingError } = await db
        .from('recipe_execution_queue')
        .select('id')
        .eq('user_id', userId)
        .eq('mode', 'compile')
        .in('status', ['pending', 'processing']);
    if (pendingError) throw new Error(pendingError.message);
    if (Array.isArray(pending) && pending.length >= MAX_PENDING_COMPILES) {
        throw new Error(pendingCompilesMessage());
    }

    const burstSinceIso = new Date(
        Date.now() - BUILDER_BURST_WINDOW_MINUTES * 60 * 1000,
    ).toISOString();
    const { data: recentCompiles, error: recentError } = await db
        .from('recipe_execution_queue')
        .select('id')
        .eq('user_id', userId)
        .eq('mode', 'compile')
        .gte('created_at', burstSinceIso);
    if (recentError) throw new Error(recentError.message);
    if (Array.isArray(recentCompiles) && recentCompiles.length >= BUILDER_BURST_LIMIT) {
        throw new Error(builderBurstLimitMessage());
    }

    const { data, error } = await db
        .from('recipe_execution_queue')
        .insert({
            recipe_id: null,
            user_id: userId,
            mode: 'compile',
            priority: 10,
            provider: 'auto-go',
            model: 'auto-go',
            payload_json: buildCompilePayload(validatedMessages),
        })
        .select('id')
        .single();

    if (error) {
        if (error.code === '23505') {
            throw new Error(pendingCompilesMessage());
        }
        throw new Error(`${error.code ?? 'error'}: ${error.message}`);
    }
    return String((data as { id: string }).id);
}

export async function readCompileJob(jobId: string, userId: string): Promise<CompileJob | null> {
    const validJobId = validateJobId(jobId);
    const db = getDbAdminClient();
    const { data, error } = await db
        .from('recipe_execution_queue')
        .select(JOB_COLUMNS)
        .eq('id', validJobId)
        .eq('user_id', userId)
        .eq('mode', 'compile')
        .maybeSingle();

    if (error) throw new Error(`${error.code ?? 'error'}: ${error.message}`);
    const row = (data as CompileJob | null) ?? null;
    if (!row) return null;

    if (row.status === 'completed' && typeof row.result_json?.content === 'string') {
        const sanitized = sanitizeCompileResult(row.result_json.content);
        return {
            ...row,
            result_json: { content: JSON.stringify(sanitized) },
        };
    }
    return row;
}

export const enqueueCompileFn = createServerFn({ method: 'POST' })
    .validator((d: unknown): { messages: BuilderMessage[] } => {
        if (!d || typeof d !== 'object') {
            throw new Error('Invalid builder request');
        }
        return {
            messages: validateBuilderMessages((d as { messages?: unknown }).messages),
        };
    })
    .handler(async ({ data: { messages } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: sign in to build a recipe');
        }
        return { jobId: await enqueueCompile(user.id, messages) };
    });

export const fetchCompileJobFn = createServerFn({ method: 'GET' })
    .validator((d: unknown): { jobId: string } => {
        if (!d || typeof d !== 'object') {
            throw new Error('Invalid compile job ID');
        }
        return {
            jobId: validateJobId((d as { jobId?: unknown }).jobId),
        };
    })
    .handler(async ({ data: { jobId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: sign in to build a recipe');
        }
        return readCompileJob(jobId, user.id);
    });

/**
 * Cancel a job the user gave up waiting for. Only a row still `pending` is touched,
 * so a worker that already claimed it keeps its result; this just frees the cap.
 */
export async function cancelCompile(jobId: string, userId: string): Promise<void> {
    const validJobId = validateJobId(jobId);
    const db = getDbAdminClient();
    const { error } = await db
        .from('recipe_execution_queue')
        .update({ status: 'cancelled', cancelled_at: new Date().toISOString() })
        .eq('id', validJobId)
        .eq('user_id', userId)
        .eq('mode', 'compile')
        .eq('status', 'pending');
    if (error) {
        throw new Error(`${error.code ?? 'error'}: ${error.message}`);
    }
}

export const cancelCompileFn = createServerFn({ method: 'POST' })
    .validator((d: unknown): { jobId: string } => {
        if (!d || typeof d !== 'object') {
            throw new Error('Invalid compile job ID');
        }
        return {
            jobId: validateJobId((d as { jobId?: unknown }).jobId),
        };
    })
    .handler(async ({ data: { jobId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        if (!user?.id) {
            throw new Error('Unauthorized: sign in to build a recipe');
        }
        await cancelCompile(jobId, user.id);
        return { cancelled: true };
    });
