import { createServerFn } from '@tanstack/react-start';
import { EXPOSED_CHAT_READ_TOOLS, executeChatTool, getDatabaseSchemaSummary } from './chat-tools';
import { ALLOWED_CHAT_EMAILS, type ChatMessage, type ToolTrace } from './chat-types';

export { ALLOWED_CHAT_EMAILS, type ChatMessage, type ToolTrace };

const MAX_TOOL_STEPS = 4;

function buildSystemPrompt(schemaSummary: string): string {
    return `You are Benchify AI, an intelligent financial & market analysis assistant embedded in the LLM Market Bench platform.
You assist authorized users by answering questions, evaluating "Should I invest in this stock?" inquiries (e.g. NVO, NVDA, AAPL), reviewing market sentiment, comparing model trading performance, and retrieving live database records and past memories.

${schemaSummary}

You have access to specialized read-only tools:
- search_memories_and_theses: Search past agent market memories, lessons learned, and causal chains for tickers (e.g. NVO, NVDA) or market themes.
- get_stock_context_and_trades: Retrieve recent agent trades, execution prices, buy/sell theses, and model decisions for a specific stock ticker.
- get_market_sentiment_and_newsletter: Retrieve the latest daily market feeling/sentiment and morning AI briefing.
- query_database_table: Execute safe read queries against any Supabase PostgreSQL table.

Always use these tools to pull facts, memory theses, and trade logs from the database before delivering answers.
Format your responses with clean Markdown, bullet points, and tables where applicable. Be concise, analytical, professional, and clear.`;
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
            messages: messages.map((m) => ({
                role: m.role,
                content: m.content,
                name: m.name,
                tool_call_id: m.tool_call_id,
                tool_calls: m.tool_calls,
            })),
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
    accumulatedTraces: ToolTrace[],
): Promise<void> {
    if (!assistantMsg.tool_calls) return;

    for (const tc of assistantMsg.tool_calls) {
        let parsedArgs: Record<string, unknown> = {};
        try {
            parsedArgs = JSON.parse(tc.function.arguments || '{}');
        } catch {
            parsedArgs = {};
        }

        const { result, trace } = await executeChatTool(tc.function.name, parsedArgs, supabase);
        accumulatedTraces.push(trace);

        messagesToSend.push({
            role: 'tool',
            tool_call_id: tc.id,
            name: tc.function.name,
            content: result,
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

    const accumulatedTraces: ToolTrace[] = [];

    for (let step = 0; step < MAX_TOOL_STEPS; step++) {
        const assistantMsg = await executeSingleStep(apiKey, messagesToSend);
        messagesToSend.push(assistantMsg);

        if (!assistantMsg.tool_calls || assistantMsg.tool_calls.length === 0) {
            return {
                ...assistantMsg,
                tool_traces: accumulatedTraces.length > 0 ? accumulatedTraces : undefined,
            };
        }

        await processToolCalls(assistantMsg, messagesToSend, supabase, accumulatedTraces);
    }

    const lastMsg = messagesToSend[messagesToSend.length - 1];
    return {
        role: 'assistant',
        content:
            lastMsg.role === 'assistant' && lastMsg.content
                ? lastMsg.content
                : 'Completed database analysis and memory lookup.',
        tool_traces: accumulatedTraces.length > 0 ? accumulatedTraces : undefined,
    };
}

export const sendChatMessageFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { messages: ChatMessage[] }) => d)
    .handler(async ({ data }) => {
        return handleChatMessage(data);
    });
