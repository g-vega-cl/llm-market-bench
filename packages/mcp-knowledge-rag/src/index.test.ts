import { describe, expect, it, vi } from 'vitest';

// Mock the GenAI SDK
vi.mock('@google/genai', () => {
    return {
        GoogleGenAI: class {
            models = {
                embedContent: vi.fn().mockResolvedValue({
                    embeddings: [{ values: new Array(768).fill(0.1) }],
                }),
            };
        },
    };
});

// Mock the Supabase SDK
vi.mock('@supabase/supabase-js', () => {
    return {
        createClient: vi.fn().mockImplementation(() => {
            return {
                rpc: vi.fn().mockImplementation(() => {
                    const mockPromise = Promise.resolve({
                        data: [
                            {
                                id: 'test-uuid-1',
                                gmail_id: 'msg-1',
                                sender: 'test@example.com',
                                subject: 'Test Subject',
                                body: 'This is a test email body for RAG.',
                                received_at: '2026-06-04T12:00:00Z',
                                similarity: 0.95,
                            },
                        ],
                        error: null,
                    });
                    interface MockPromiseWithExecute
                        extends Promise<{
                            data: Array<{
                                id: string;
                                gmail_id: string;
                                sender: string;
                                subject: string;
                                body: string;
                                received_at: string;
                                similarity: number;
                            }>;
                            error: null;
                        }> {
                        execute?: () => Promise<{
                            data: Array<{
                                id: string;
                                gmail_id: string;
                                sender: string;
                                subject: string;
                                body: string;
                                received_at: string;
                                similarity: number;
                            }>;
                            error: null;
                        }>;
                    }
                    // Also attach .execute for mock compatibility
                    (mockPromise as MockPromiseWithExecute).execute = () => mockPromise;
                    return mockPromise;
                }),
            };
        }),
    };
});

import { queryKnowledgeBase } from './index';

describe('MCP Knowledge RAG', () => {
    it('should query the knowledge base and return matching emails', async () => {
        const results = await queryKnowledgeBase('test query', 1, 0.5);
        expect(results).toBeDefined();
        expect(results.length).toBe(1);
        expect(results[0].subject).toBe('Test Subject');
        expect(results[0].sender).toBe('test@example.com');
    });
});
