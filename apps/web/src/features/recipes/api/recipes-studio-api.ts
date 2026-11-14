import { createServerFn } from '@tanstack/react-start';
import { getAuthServerClient } from '~/lib/auth';
import { getDbAdminClient, getDbServerClient } from '~/lib/db';
import { hydrateMemoriesBlockText, hydrateNewsBlockText } from '../prompt-builder';
import type { PushStrategy, RecipeAlert } from '../types';

const ANONYMOUS_USER_ID = '00000000-0000-0000-0000-000000000000';

export async function fetchRecipeAlerts(userId: string): Promise<RecipeAlert[]> {
    const db = getDbAdminClient();

    const { data, error } = await db
        .from('recipe_alerts_inbox')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(50);

    if (error) {
        throw new Error(error.message);
    }
    return (data || []) as RecipeAlert[];
}

export const fetchRecipeAlertsFn = createServerFn({ method: 'GET' }).handler(async () => {
    const auth = getAuthServerClient();
    const {
        data: { user },
    } = await auth.auth.getUser();
    return fetchRecipeAlerts(user?.id || ANONYMOUS_USER_ID);
});

export async function markAlertRead(
    alertId: string,
    userId: string,
): Promise<{ success: boolean }> {
    const db = getDbAdminClient();
    const { error } = await db
        .from('recipe_alerts_inbox')
        .update({ is_read: true })
        .eq('id', alertId)
        .eq('user_id', userId);

    if (error) throw new Error(error.message);
    return { success: true };
}

export const markAlertReadFn = createServerFn({ method: 'POST' })
    .validator((d: { alertId: string }) => d)
    .handler(async ({ data: { alertId } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        return markAlertRead(alertId, user?.id || ANONYMOUS_USER_ID);
    });

export async function submitWaitlistPledge(
    userId: string,
    email: string,
    intendedTier: string,
    feedback = '',
): Promise<{ success: boolean }> {
    const db = getDbAdminClient();
    const { error } = await db.from('recipe_waitlist_pledges').insert({
        user_id: userId,
        email,
        intended_tier: intendedTier,
        feedback,
    });

    if (error) throw new Error(error.message);
    return { success: true };
}

export const submitWaitlistPledgeFn = createServerFn({ method: 'POST' })
    .validator((d: { email: string; intendedTier: string; feedback?: string }) => d)
    .handler(async ({ data: { email, intendedTier, feedback = '' } }) => {
        const auth = getAuthServerClient();
        const {
            data: { user },
        } = await auth.auth.getUser();
        return submitWaitlistPledge(user?.id || ANONYMOUS_USER_ID, email, intendedTier, feedback);
    });

export async function previewStrategyPrompt(
    strategy: PushStrategy,
): Promise<Record<string, string>> {
    const db = getDbServerClient();
    const now = Date.now();
    const hydrated: Record<string, string> = {};

    const needsNews = strategy.stages.some((stage) =>
        stage.blocks.some((block) => block.type === 'news'),
    );
    const needsMemories = strategy.stages.some((stage) =>
        stage.blocks.some((block) => block.type === 'memories'),
    );

    let newsRows: Array<{ title?: string; full_text?: string; date_published?: string }> = [];
    if (needsNews) {
        const { data } = await db
            .from('recipe_news_corpus')
            .select('article_id, title, full_text, date_published, tickers')
            .order('date_published', { ascending: false })
            .limit(500);
        newsRows = data ?? [];
    }

    let memoryRows: Array<{
        content?: string;
        created_at?: string;
        memory_type?: string;
        importance_score?: number;
    }> = [];
    if (needsMemories) {
        const { data } = await db
            .from('memories')
            .select('id, content, created_at, memory_type, importance_score')
            .order('created_at', { ascending: false })
            .limit(500);
        memoryRows = data ?? [];
    }

    for (const stage of strategy.stages) {
        for (const block of stage.blocks) {
            if (block.type === 'news') {
                hydrated[block.id] = hydrateNewsBlockText(block, newsRows, now);
            } else if (block.type === 'memories') {
                hydrated[block.id] = hydrateMemoriesBlockText(block, memoryRows, now);
            }
        }
    }

    return hydrated;
}

export const previewStrategyPromptFn = createServerFn({ method: 'POST' })
    .validator((d: { strategy: PushStrategy }) => d)
    .handler(({ data: { strategy } }) => previewStrategyPrompt(strategy));
