import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { GoogleGenAI } from '@google/genai';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

// Support ES module directory resolution
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Auto-load environment variables from apps/engine/.env or process directory
const envPaths = [
    path.resolve(__dirname, '../../../apps/engine/.env'),
    path.resolve(process.cwd(), 'apps/engine/.env'),
    path.resolve(process.cwd(), '.env'),
];

for (const envPath of envPaths) {
    if (fs.existsSync(envPath)) {
        dotenv.config({ path: envPath });
        break;
    }
}

/**
 * Structure of an email record retrieved from the knowledge database.
 */
export interface EmailRecord {
    id: string;
    gmail_id: string;
    sender?: string;
    subject?: string;
    body?: string;
    received_at?: string;
    similarity: number;
}

interface Executable<T> {
    execute(): Promise<T>;
}

/**
 * Generates vector embeddings for a given text query using Gemini API.
 */
export async function getEmbedding(text: string): Promise<number[]> {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
        throw new Error('GEMINI_API_KEY is not defined in the environment or .env file');
    }

    if (!text) {
        return [];
    }

    try {
        const ai = new GoogleGenAI({ apiKey });
        const cleanedText = text.replace(/\n/g, ' ');

        const response = await ai.models.embedContent({
            model: 'gemini-embedding-001',
            contents: cleanedText,
            config: {
                outputDimensionality: 768,
            },
        });

        if (!response.embeddings || response.embeddings.length === 0) {
            throw new Error('No embeddings returned from Gemini API');
        }

        const values = response.embeddings[0].values;
        if (!values) {
            throw new Error('No embedding values returned from Gemini API');
        }

        return values;
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);
        throw new Error(`Failed to generate embedding: ${message}`);
    }
}

/**
 * Performs semantic search queries against the misc Supabase database.
 */
export async function queryKnowledgeBase(
    queryText: string,
    limit: number = 5,
    threshold: number = 0.5,
): Promise<EmailRecord[]> {
    const supabaseUrl = process.env.MISC_SUPABASE_URL;
    const supabaseKey = process.env.MISC_SUPABASE_KEY;

    if (!supabaseUrl || !supabaseKey) {
        throw new Error(
            'MISC_SUPABASE_URL and MISC_SUPABASE_KEY must be defined in the environment or .env file',
        );
    }

    // 1. Generate query embedding
    const embedding = await getEmbedding(queryText);

    // 2. Connect to Supabase
    const supabase = createClient(supabaseUrl, supabaseKey);

    // 3. Invoke pgvector RPC search function
    const query = supabase.rpc('match_emails', {
        query_embedding: embedding,
        match_threshold: threshold,
        match_count: limit,
    });

    let response: { data: EmailRecord[] | null; error: { message: string } | null };
    if (
        query &&
        typeof query === 'object' &&
        'execute' in query &&
        typeof (query as { execute: unknown }).execute === 'function'
    ) {
        response = await (
            query as unknown as Executable<{
                data: EmailRecord[] | null;
                error: { message: string } | null;
            }>
        ).execute();
    } else {
        response = await (query as unknown as Promise<{
            data: EmailRecord[] | null;
            error: { message: string } | null;
        }>);
    }

    const { data, error } = response;

    if (error) {
        throw new Error(`Supabase search query failed: ${error.message}`);
    }

    return data || [];
}

// ==========================================
// MCP Server Setup
// ==========================================

const server = new Server(
    {
        name: 'mcp-knowledge-rag',
        version: '0.1.0',
    },
    {
        capabilities: {
            tools: {},
        },
    },
);

// Register available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'query_knowledge_base',
                description:
                    'Queries the external database of emails and ingested information using semantic search (RAG). Use this to find relevant context, emails, and reputable source information for answering user questions.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        query: {
                            type: 'string',
                            description:
                                'The natural language query or question to search the database for.',
                        },
                        limit: {
                            type: 'number',
                            description:
                                'Optional maximum number of matching results to retrieve (default: 5).',
                        },
                        threshold: {
                            type: 'number',
                            description:
                                'Optional minimum similarity threshold between 0.0 and 1.0 (default: 0.5).',
                        },
                    },
                    required: ['query'],
                },
            },
        ],
    };
});

// Handle tool execution requests
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (request.params.name === 'query_knowledge_base') {
        const args = request.params.arguments as {
            query: string;
            limit?: number;
            threshold?: number;
        };

        if (!args || typeof args.query !== 'string') {
            throw new Error('Invalid arguments for query_knowledge_base. Query must be a string.');
        }

        try {
            const results = await queryKnowledgeBase(
                args.query,
                args.limit ?? 5,
                args.threshold ?? 0.5,
            );

            if (results.length === 0) {
                return {
                    content: [
                        {
                            type: 'text',
                            text: 'No matching records found in the knowledge base.',
                        },
                    ],
                };
            }

            const formattedResults = results
                .map((email, index: number) => {
                    return `[Result ${index + 1}] (Similarity: ${(email.similarity * 100).toFixed(1)}%)\nSender: ${email.sender || 'Unknown'}\nSubject: ${email.subject || 'No Subject'}\nDate: ${email.received_at || 'Unknown'}\nContent:\n${email.body || 'No content'}\n---`;
                })
                .join('\n\n');

            return {
                content: [
                    {
                        type: 'text',
                        text: formattedResults,
                    },
                ],
            };
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : String(err);
            return {
                content: [
                    {
                        type: 'text',
                        text: `Error querying knowledge base: ${message}`,
                    },
                ],
                isError: true,
            };
        }
    }

    throw new Error(`Tool not found: ${request.params.name}`);
});

// Start the server (only if not running inside test environment)
async function run() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('MCP Knowledge RAG Server running on stdio');
}

if (process.env.NODE_ENV !== 'test') {
    run().catch((err) => {
        console.error('Fatal error running MCP server:', err);
        process.exit(1);
    });
}
