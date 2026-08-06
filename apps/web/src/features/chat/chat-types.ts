export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export const ALLOWED_CHAT_EMAILS = ['g.vega.cl@gmail.com'];
