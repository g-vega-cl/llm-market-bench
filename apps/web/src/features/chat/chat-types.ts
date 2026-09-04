export interface ToolCall {
    id: string;
    type: 'function';
    function: {
        name: string;
        arguments: string;
    };
}

export interface ToolTrace {
    tool_name: string;
    summary: string;
}

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string | null;
    name?: string;
    tool_call_id?: string;
    tool_calls?: ToolCall[];
    tool_traces?: ToolTrace[];
    suggested_questions?: string[];
    saved_memory_id?: string;
}

export interface ChatMemory {
    id: string;
    user_id: string;
    ticker?: string | null;
    thesis: string;
    tags?: string[];
    importance_score: number;
    source_query?: string | null;
    created_at: string;
}

export interface DistillMemoryRequest {
    userQuery: string;
    assistantResponse: string;
    customInstruction?: string;
}

export interface DistillMemoryResult {
    ticker?: string;
    thesis: string;
    tags: string[];
    importance_score: number;
}

export interface SaveChatMemoryRequest {
    ticker?: string;
    thesis: string;
    tags?: string[];
    importance_score?: number;
    sourceQuery?: string;
}

export const ALLOWED_CHAT_EMAILS = ['g.vega.cl@gmail.com'];

export const SUGGESTED_RESEARCH_PROMPTS = [
    'Should I invest in NVO based on current memories and trades?',
    'What is the current market feeling and today’s morning briefing?',
    'Show me the recent trades and theses for NVDA.',
    'Which portfolios and models currently have the highest win rate?',
];
