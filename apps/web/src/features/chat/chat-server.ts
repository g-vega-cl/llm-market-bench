import { createServerFn } from '@tanstack/react-start';
import { EXPOSED_CHAT_READ_TOOLS, executeChatTool, getDatabaseSchemaSummary } from './chat-tools';
import {
    ALLOWED_CHAT_EMAILS,
    type ChatMemory,
    type ChatMessage,
    type DistillMemoryRequest,
    type DistillMemoryResult,
    type SaveChatMemoryRequest,
    type ToolTrace,
} from './chat-types';

export {
    ALLOWED_CHAT_EMAILS,
    type ChatMemory,
    type ChatMessage,
    type DistillMemoryRequest,
    type DistillMemoryResult,
    type SaveChatMemoryRequest,
    type ToolTrace,
};

const MAX_TOOL_STEPS = 4;

function buildSystemPrompt(schemaSummary: string): string {
    return `You are Benchify AI, an intelligent financial & market analysis assistant embedded in the LLM Market Bench platform.
You assist authorized users by answering questions, evaluating "Should I invest in this stock?" inquiries (e.g. NVO, NVDA, AAPL), reviewing market sentiment, comparing model trading performance, and retrieving live database records and past memories.

${schemaSummary}

You have access to specialized read-only tools:
- search_memories_and_theses: Search past agent market memories, lessons learned, and causal chains for tickers (e.g. NVO, NVDA) or market themes.
- get_stock_context_and_trades: Retrieve recent agent trades, execution prices, buy/sell theses, and model decisions for a specific stock ticker.
- get_market_sentiment_and_newsletter: Retrieve the latest daily market feeling/sentiment and morning AI briefing.
- get_my_saved_theses: Retrieve the user’s personal saved research theses and private market notes from their chat_memories.
- query_database_table: Execute safe read queries against any Supabase PostgreSQL table.

Always use these tools to pull facts, memory theses, and trade logs from the database before delivering answers.
Format your responses with clean Markdown, bullet points, and tables where applicable. Be concise, analytical, professional, and clear.

At the very end of your final response to the user, suggest 2-3 concise follow-up research questions or next steps directly relevant to the topic. Output them in this exact format:
<suggested_questions>
["Question 1", "Question 2", "Question 3"]
</suggested_questions>`;
}

function extractQuotedStrings(rawText: string): string[] {
    return [...rawText.matchAll(/"([^"\n\r]+)"/g)]
        .map((m) => m[1].trim())
        .filter((s) => s.length > 0);
}

function parseQuestionsBlock(rawBlock: string): string[] | undefined {
    try {
        const parsed = JSON.parse(rawBlock);
        if (Array.isArray(parsed)) {
            const strings = parsed
                .filter(
                    (item): item is string => typeof item === 'string' && item.trim().length > 0,
                )
                .map((item) => item.trim());
            if (strings.length > 0) return strings;
        }
    } catch {
        // Fall back to regex parsing of quotes
    }

    const extracted = extractQuotedStrings(rawBlock);
    return extracted.length > 0 ? extracted : undefined;
}

export function extractSuggestedQuestions(rawContent: string | null): {
    content: string | null;
    suggested_questions?: string[];
} {
    if (!rawContent) {
        return { content: rawContent, suggested_questions: undefined };
    }

    const tagMatch = /<suggested_questions>([\s\S]*?)<\/suggested_questions>/i.exec(rawContent);
    const partialMatch = !tagMatch ? /<suggested_questions>([\s\S]*)$/i.exec(rawContent) : null;
    const targetBlock = tagMatch?.[1] ?? partialMatch?.[1];

    const suggested_questions = targetBlock ? parseQuestionsBlock(targetBlock.trim()) : undefined;

    const cleanContent = rawContent
        .replace(/<suggested_questions>[\s\S]*?(<\/suggested_questions>|$)/gi, '')
        .trim();

    return {
        content: cleanContent.length > 0 ? cleanContent : rawContent.trim(),
        suggested_questions,
    };
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
    userId?: string,
): Promise<void> {
    if (!assistantMsg.tool_calls) return;

    for (const tc of assistantMsg.tool_calls) {
        let parsedArgs: Record<string, unknown> = {};
        try {
            parsedArgs = JSON.parse(tc.function.arguments || '{}');
        } catch {
            parsedArgs = {};
        }

        const { result, trace } = await executeChatTool(
            tc.function.name,
            parsedArgs,
            supabase,
            userId,
        );
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
            const { content: cleanContent, suggested_questions } = extractSuggestedQuestions(
                assistantMsg.content,
            );
            return {
                ...assistantMsg,
                content: cleanContent,
                suggested_questions,
                tool_traces: accumulatedTraces.length > 0 ? accumulatedTraces : undefined,
            };
        }

        await processToolCalls(
            assistantMsg,
            messagesToSend,
            supabase,
            accumulatedTraces,
            data.user.id,
        );
    }

    const lastMsg = messagesToSend[messagesToSend.length - 1];
    const rawContent =
        lastMsg.role === 'assistant' && lastMsg.content
            ? lastMsg.content
            : 'Completed database analysis and memory lookup.';
    const { content: cleanContent, suggested_questions } = extractSuggestedQuestions(rawContent);

    return {
        role: 'assistant',
        content: cleanContent,
        suggested_questions,
        tool_traces: accumulatedTraces.length > 0 ? accumulatedTraces : undefined,
    };
}

function parseJsonFromText<T>(text: string): T | null {
    try {
        return JSON.parse(text) as T;
    } catch {
        const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
        if (jsonMatch) {
            try {
                return JSON.parse(jsonMatch[1]) as T;
            } catch {
                // Continue
            }
        }
        const objMatch = text.match(/\{[\s\S]*\}/);
        if (objMatch) {
            try {
                return JSON.parse(objMatch[0]) as T;
            } catch {
                // Continue
            }
        }
    }
    return null;
}

export async function handleDistillChatMemory(
    payload: DistillMemoryRequest,
): Promise<DistillMemoryResult> {
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

    const systemPrompt = `You are a quantitative research editor for LLM Market Bench.
Your job is to distill a financial research exchange into a high-density, actionable market thesis for private memory storage.
Extract:
- ticker: Uppercase stock ticker symbol (e.g. NVO, NVDA) if discussed, or omit/null if macro/generic.
- thesis: Exactly 1 to 3 factual, standalone, self-contained sentences stating the catalyst, mechanism, and trading implication. No conversational filler or lead-ins.
- tags: Array of 2 to 5 relevant topic tags.
- importance_score: Integer from 1 to 10 evaluating signal strength (default 7 or 8).

Return ONLY a valid JSON object with keys: "ticker", "thesis", "tags", "importance_score".`;

    const userPrompt = `User Query: "${payload.userQuery || 'General market inquiry'}"
Assistant Response:
"""
${payload.assistantResponse}
"""${payload.customInstruction ? `\n\nAdditional refinement instruction from user: ${payload.customInstruction}` : ''}

Distill into JSON:`;

    const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
            model: 'deepseek-chat',
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: userPrompt },
            ],
            temperature: 0.2,
        }),
    });

    if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Memory distillation failed (${response.status}): ${errText}`);
    }

    const responseData = (await response.json()) as {
        choices: { message: { content: string } }[];
    };

    const rawContent = responseData.choices?.[0]?.message?.content?.trim() || '{}';
    const parsed = parseJsonFromText<{
        ticker?: string;
        thesis?: string;
        tags?: string[];
        importance_score?: number;
    }>(rawContent);

    return {
        ticker: parsed?.ticker ? parsed.ticker.trim().toUpperCase() : undefined,
        thesis: parsed?.thesis?.trim() || rawContent,
        tags: Array.isArray(parsed?.tags) ? parsed.tags : [],
        importance_score:
            typeof parsed?.importance_score === 'number'
                ? Math.max(1, Math.min(10, Math.round(parsed.importance_score)))
                : 7,
    };
}

export async function handleSaveChatMemory(payload: SaveChatMemoryRequest): Promise<ChatMemory> {
    const { getSupabaseServerClient } = await import('~/lib/supabase');
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();

    if (error || !data.user) {
        throw new Error('Authentication required');
    }

    if (!data.user.email || !ALLOWED_CHAT_EMAILS.includes(data.user.email)) {
        throw new Error('Chat feature is restricted to authorized accounts');
    }

    const thesis = payload.thesis?.trim();
    if (!thesis) {
        throw new Error('Thesis content is required');
    }

    const { data: inserted, error: insertError } = await supabase
        .from('chat_memories')
        .insert({
            user_id: data.user.id,
            ticker: payload.ticker ? payload.ticker.trim().toUpperCase() : null,
            thesis,
            tags: payload.tags || [],
            importance_score: payload.importance_score ?? 7,
            source_query: payload.sourceQuery || null,
        })
        .select()
        .single();

    if (insertError) {
        throw new Error(
            `Failed to save chat memory: ${insertError.message || String(insertError)}`,
        );
    }

    return inserted as ChatMemory;
}

export async function handleFetchMyChatMemories(payload: {
    ticker?: string;
}): Promise<ChatMemory[]> {
    const { getSupabaseServerClient } = await import('~/lib/supabase');
    const supabase = getSupabaseServerClient();
    const { data, error } = await supabase.auth.getUser();

    if (error || !data.user) {
        throw new Error('Authentication required');
    }

    if (!data.user.email || !ALLOWED_CHAT_EMAILS.includes(data.user.email)) {
        throw new Error('Chat feature is restricted to authorized accounts');
    }

    let query = supabase.from('chat_memories').select('*').eq('user_id', data.user.id);

    if (payload.ticker) {
        query = query.eq('ticker', payload.ticker.trim().toUpperCase());
    }

    const { data: records, error: fetchError } = await query.order('created_at', {
        ascending: false,
    });

    if (fetchError) {
        throw new Error(
            `Failed to fetch chat memories: ${fetchError.message || String(fetchError)}`,
        );
    }

    return (records || []) as ChatMemory[];
}

export const sendChatMessageFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { messages: ChatMessage[] }) => d)
    .handler(async ({ data }) => {
        return handleChatMessage(data);
    });

export const distillChatMemoryFn = createServerFn({ method: 'POST' })
    .inputValidator((d: DistillMemoryRequest) => d)
    .handler(async ({ data }) => {
        return handleDistillChatMemory(data);
    });

export const saveChatMemoryFn = createServerFn({ method: 'POST' })
    .inputValidator((d: SaveChatMemoryRequest) => d)
    .handler(async ({ data }) => {
        return handleSaveChatMemory(data);
    });

export const fetchMyChatMemoriesFn = createServerFn({ method: 'GET' })
    .inputValidator((d: { ticker?: string }) => d)
    .handler(async ({ data }) => {
        return handleFetchMyChatMemories(data);
    });
