export interface ToolCall {
    id: string;
    type: 'function';
    function: {
        name: string;
        arguments: string;
    };
}

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string | null;
    name?: string;
    tool_call_id?: string;
    tool_calls?: ToolCall[];
}

export const ALLOWED_CHAT_EMAILS = ['g.vega.cl@gmail.com'];
