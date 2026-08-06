import { createServerFn } from '@tanstack/react-start';
import { ALLOWED_CHAT_EMAILS, type ChatMessage } from './chat-types';

export { ALLOWED_CHAT_EMAILS, type ChatMessage };

const SYSTEM_PROMPT = `You are Benchify AI, an intelligent financial & market analysis assistant embedded in the LLM Market Bench platform.
You assist authorized users by answering questions, reviewing market predictions, and discussing investment strategies.
Be concise, analytical, professional, and clear.`;

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

    const messagesToSend: ChatMessage[] = [
        { role: 'system', content: SYSTEM_PROMPT },
        ...payload.messages,
    ];

    const response = await fetch('https://api.deepseek.com/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
            model: 'deepseek-chat',
            messages: messagesToSend,
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

export const sendChatMessageFn = createServerFn({ method: 'POST' })
    .inputValidator((d: { messages: ChatMessage[] }) => d)
    .handler(async ({ data }) => {
        return handleChatMessage(data);
    });
