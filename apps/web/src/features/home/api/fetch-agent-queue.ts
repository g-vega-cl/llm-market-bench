import { createServerFn } from '@tanstack/react-start';

export interface AgentQueueItem {
    id: string;
    user_id: string | null;
    display_name: string;
    message: string;
    status: 'pending' | 'injected' | 'answered' | 'archived' | 'rejected';
    created_at: string;
    injected_turn_at?: string | null;
    agent_response?: string | null;
}

export interface AgentQueueStatus {
    pendingCount: number;
    latestAnswered: AgentQueueItem | null;
}

export const MAX_QUEUE_MESSAGE_LENGTH = 500;

export function validateQueueMessage(rawMessage: string | null | undefined): string {
    if (!rawMessage?.trim()) {
        throw new Error('Message cannot be empty.');
    }
    const trimmed = rawMessage.trim();
    if (trimmed.length > MAX_QUEUE_MESSAGE_LENGTH) {
        throw new Error(`Message cannot exceed ${MAX_QUEUE_MESSAGE_LENGTH} characters.`);
    }
    return trimmed;
}

export async function handleSubmitAgentQueueQuestion(data: {
    message: string;
}): Promise<{ success: boolean; item: AgentQueueItem }> {
    const trimmedMessage = validateQueueMessage(data.message);

    const { getAuthServerClient } = await import('~/lib/auth');
    const { getDbAdminClient } = await import('~/lib/db');
    const authClient = getAuthServerClient();

    const { data: authData, error: authError } = await authClient.auth.getUser();
    const user = authData?.user;

    if (authError || !user?.id) {
        throw new Error('UNAUTHORIZED: You must be signed in to submit to the queue.');
    }

    const displayName = user.email ? user.email.split('@')[0] : 'Analyst';

    const db = getDbAdminClient();
    const { data: insertedItem, error: insertError } = await db
        .from('agent_chat_queue')
        .insert({
            user_id: user.id,
            display_name: displayName,
            message: trimmedMessage,
            status: 'pending',
        })
        .select()
        .single();

    if (insertError) {
        throw new Error(`Failed to submit question: ${insertError.message}`);
    }

    return {
        success: true,
        item: insertedItem as AgentQueueItem,
    };
}

export async function handleFetchAgentQueueStatus(): Promise<AgentQueueStatus> {
    try {
        const { getDbServerClient } = await import('~/lib/db');
        const db = getDbServerClient();

        // 1. Fetch pending count
        const { count: pendingCount, error: countErr } = await db
            .from('agent_chat_queue')
            .select('*', { count: 'exact', head: true })
            .eq('status', 'pending');

        // 2. Fetch latest answered item
        const { data: answeredRows, error: ansErr } = await db
            .from('agent_chat_queue')
            .select('*')
            .not('agent_response', 'is', null)
            .order('injected_turn_at', { ascending: false })
            .limit(1);

        return {
            pendingCount: !countErr && typeof pendingCount === 'number' ? pendingCount : 0,
            latestAnswered:
                !ansErr && answeredRows && answeredRows.length > 0
                    ? (answeredRows[0] as AgentQueueItem)
                    : null,
        };
    } catch {
        return {
            pendingCount: 0,
            latestAnswered: null,
        };
    }
}

export const submitAgentQueueQuestion = createServerFn({ method: 'POST' })
    .inputValidator((d: { message: string }) => d)
    .handler(async ({ data }) => {
        return handleSubmitAgentQueueQuestion(data);
    });

export const fetchAgentQueueStatus = createServerFn({ method: 'GET' }).handler(
    async (): Promise<AgentQueueStatus> => {
        return handleFetchAgentQueueStatus();
    },
);
