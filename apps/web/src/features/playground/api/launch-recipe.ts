import { createHash } from 'node:crypto';
import { createServerFn } from '@tanstack/react-start';
import type { PushStrategy } from '~/features/recipes/types';
import { getEtDateString } from '~/features/recipes/utils/market-hours';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient } from '~/lib/db';
import { normalizeBlocks } from '../lib/blocks';
import { type LaunchResult, normalizeLaunchRow } from '../lib/launch-result';

export interface LaunchInput {
    graph: PushStrategy;
    live: boolean;
    name: string;
    description: string;
}

/**
 * Order is presentation (the hydrator sorts the terminal block last), so the key
 * must not depend on it: otherwise renaming two blocks would buy a second run.
 */
function canonicalGraph(graph: PushStrategy): string {
    const stage = graph.stages[0];
    const blocks = [...stage.blocks].sort((a, b) => a.id.localeCompare(b.id));
    return JSON.stringify({
        name: graph.name,
        cadence: graph.cadence,
        tools: [...stage.selected_tools].sort(),
        blocks,
    });
}

function idempotencyKey(userId: string, graph: PushStrategy, live: boolean): string {
    return createHash('sha256')
        .update(
            [userId, getEtDateString(), live ? 'live' : 'backtest', canonicalGraph(graph)].join(
                '|',
            ),
        )
        .digest('hex');
}

function mapRpcError(error: { message?: string; code?: string }): LaunchResult {
    const message = error.message ?? 'The run request failed.';
    const retryable = /timeout|timed out|429|503|fetch failed|ECONN/i.test(message);
    if (/does not exist|schema cache|PGRST202/i.test(message)) {
        return {
            kind: 'error',
            retryable: false,
            message: 'The launch endpoint is not deployed yet. Try again after the next deploy.',
        };
    }
    return { kind: 'error', retryable, message };
}

/**
 * One atomic call: the recipe row, its queue job and the cap checks happen under
 * a single row lock inside `launch_recipe`, so a double click or two tabs cannot
 * produce two bots.
 */
export const launchRecipeFn = createServerFn({ method: 'POST' })
    .validator((data: LaunchInput) => data)
    .handler(async ({ data }): Promise<LaunchResult> => {
        const auth = getAuthServerClient();
        const { data: authData } = await auth.auth.getUser();
        const userId = authData?.user?.id;
        if (!userId) {
            return {
                kind: 'error',
                retryable: false,
                needsAuth: true,
                message: 'Sign in to run this bot.',
            };
        }

        const stage = data.graph?.stages?.[0];
        if (!stage || !Array.isArray(stage.blocks)) {
            return { kind: 'invalid', message: 'That bot has no blocks to run.' };
        }
        const ids = stage.blocks.map((block) => block.id);
        if (new Set(ids).size !== ids.length) {
            return { kind: 'invalid', message: 'Two blocks share an id — remove one.' };
        }
        const terminals = stage.blocks.filter((block) => block.type === 'output_format');
        if (terminals.length !== 1) {
            return { kind: 'invalid', message: 'A bot needs exactly one answer block.' };
        }
        if (JSON.stringify(stage.blocks).includes('{{prev_output}}')) {
            return {
                kind: 'invalid',
                message: 'A single-stage bot cannot reference a previous stage.',
            };
        }
        const graph: PushStrategy = {
            ...data.graph,
            stages: [{ ...stage, blocks: normalizeBlocks(stage.blocks) }],
        };

        const db = getDbAdminClient();
        const { data: rows, error } = await db.rpc('launch_recipe', {
            p_user_id: userId,
            p_graph: graph,
            p_name: data.name,
            p_description: data.description,
            p_live_wanted: data.live,
            p_idempotency_key: idempotencyKey(userId, graph, data.live),
        });

        if (error) return mapRpcError(error);
        return normalizeLaunchRow(Array.isArray(rows) ? rows[0] : rows);
    });
