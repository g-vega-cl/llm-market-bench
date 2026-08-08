import { createServerFn } from '@tanstack/react-start';
import {
    EXPOSED_CHAT_READ_TOOLS,
    executeDatabaseQueryTool,
    getDatabaseSchemaSummary,
} from './chat-tools';
import { ALLOWED_CHAT_EMAILS, type ChatMessage } from './chat-types';

export { ALLOWED_CHAT_EMAILS, type ChatMessage };

const MAX_TOOL_STEPS = 3;

function buildSystemPrompt(schemaSummary: string): string {
    return `You are Benchify AI, an intelligent financial & market analysis assistant embedded in the LLM Market Bench platform.
You assist authorized users by answering questions, reviewing market predictions, discussing investment strategies, and retrieving live database records.

${schemaSummary}

You have access to the 'query_database_table' tool to execute safe, read-only queries against Supabase tables.
When asked about trades, portfolios, sector predictions, prompt experiments, newsletters, or leaderboard metrics, call 'query_database_table' to fetch real data before answering.
Be concise, analytical, professional, and clear.`;
}

async function executeSingleStep(apiKey: string, messages: ChatMessage[]): Promise<ChatMessage> {
    const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
            model: 'deepseek-chat',
            messages,
            tools: EXPOSED_CHAT_READ_TOOLS,
            temperature: 0.7,
        }),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`DeepSeek API request failed (${response.status}): ${errorText}`);
    }

    const responseData = (await response.json()) as {
        choices: { message: ChatMessage }[];
    };

    if (!responseData.choices || responseData.choices.length === 0) {
        throw new Error('Invalid response from DeepSeek API');
    }

    return responseData.choices[0].message;
}

async function processToolCalls(
    assistantMsg: ChatMessage,
    messagesToSend: ChatMessage[],
    supabase: unknown,
): Promise<void> {
    if (!assistantMsg.tool_calls) return;

    for (const tc of assistantMsg.tool_calls) {
        let parsedArgs: Record<string, unknown> = {};
        try {
            parsedArgs = JSON.parse(tc.function.arguments || '{}');
        } catch {
            parsedArgs = {};
        }

        const toolResult = await executeDatabaseQueryTool(parsedArgs, supabase);

        messagesToSend.push({
            role: 'tool',
            tool_call_id: tc.id,
            name: tc.function.name,
            content: toolResult,
        });
    }
}

export async function handleChatMessage(payload: {
    messages: ChatMessage[];
}): Promise<ChatMessage> {
    const { getSupabaseServerClient } = await import('~/lib/supabase');
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();

    if (error || !data.user) {
        throw new Error('Authentication required');
    }

    if (!data.user.email || !ALLOWED_CHAT_EMAILS.includes(data.user.email)) {
        throw new Error('Chat feature is restricted to authorized accounts');
    }

    const apiKey = process.env.DEEPSEEK_API_KEY;
    if (!apiKey) {
        throw new Error('DeepSeek API key is not configured');
    }

    const schemaSummary = await getDatabaseSchemaSummary(supabase);
    const systemPrompt = buildSystemPrompt(schemaSummary);

    const messagesToSend: ChatMessage[] = [
        { role: 'system', content: systemPrompt },
        ...payload.messages,
    ];

    for (let step = 0; step < MAX_TOOL_STEPS; step++) {
        const assistantMsg = await executeSingleStep(apiKey, messagesToSend);
        messagesToSend.push(assistantMsg);

        if (!assistantMsg.tool_calls || assistantMsg.tool_calls.length === 0) {
            return assistantMsg;
        }

        await processToolCalls(assistantMsg, messagesToSend, supabase);
    }

    const lastMsg = messagesToSend[messagesToSend.length - 1];
    return lastMsg.role === 'assistant'
        ? lastMsg
        : { role: 'assistant', content: 'Completed database query and analysis.' };
}

export const sendChatMessageFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { messages: ChatMessage[] }) => d)
    .handler(async ({ data }) => {
        return handleChatMessage(data);
    });
