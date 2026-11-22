import {
    assertKnownRuleMetrics,
    assertNoPrevOutputPlaceholder,
    assertSingleLlmStage,
} from '../api/recipes-validators';
import { STARTER_RECIPES } from '../starter-templates';
import type { PushStrategy, StrategyBlock } from '../types';
import { CURATED_TOOLS } from '../types';

export type CompilerReply =
    | { status: 'ok'; strategy: PushStrategy; summary: string; fallback?: boolean }
    | { status: 'question'; question: string; options: string[] }
    | { status: 'declined'; reason: string; closest?: string };

export interface BuilderMessage {
    role: 'user' | 'assistant';
    content: string;
}

const BLOCK_TYPES = new Set(['prompt', 'news', 'memories', 'technicals', 'output_format']);
const MAX_OPTIONS = 4;

/**
 * The menu the compiler is allowed to choose from. It is generated from the same
 * types the studio edits, so the model can never invent a block, tool or field
 * the engine would reject at run time.
 */
export function capabilityManifest(): string {
    const tools = CURATED_TOOLS.filter((tool) => tool.name !== 'web_search')
        .map((tool) => `- ${tool.name}: ${tool.description}`)
        .join('\n');
    return [
        'BLOCKS (pick any subset, order does not matter):',
        '- prompt: {"type":"prompt","text":"<instructions>"}',
        '- news: {"type":"news","contains":["keyword"],"recency_hours":24}',
        '- memories: {"type":"memories","contains":["keyword"],"recency_hours":168,"category":"MACRO|POST_MORTEM|TECHNICAL|SENTIMENT","min_importance":1}',
        '- technicals: {"type":"technicals","rules":[{"metric":"RSI","operator":"<","value":30}]}',
        '  suggested metrics: RSI, MACD, VWAP_pct, P/E, FCF_yield, price_52w_pct, market_cap',
        '- output_format: {"type":"output_format"}  (REQUIRED, and always rendered last)',
        '',
        'TOOLS the recipe may call (selected_tools):',
        tools,
        '',
        'HARD CONSTRAINTS:',
        '- Long only. BUY or EXIT a held ticker, or [] to hold. No shorts, no options, no intraday triggers.',
        '- Exactly one stage. One LLM call per run.',
        '- cadence is "3h" (the scheduler runs 09:30, 12:30, 15:30 ET); 5m and 1d are accepted but not honoured.',
        '- Never use web_search. Every run is point-in-time and offline.',
        '- Every block needs a unique short string id (b1, b2, ...), the stage needs an id (s1).',
    ].join('\n');
}

export function compilerSystemPrompt(): string {
    return [
        "You turn a trader's plain-English idea into a Benchify Strategy Recipe (Push v2).",
        'Reply with STRICT JSON only, no prose, no code fences.',
        '',
        'Reply shapes:',
        '{"status":"ok","summary":"<one sentence describing the bot>","strategy":{"version":"2.0-push","name":"<max 40 chars>","description":"<one line>","cadence":"3h","stages":[{"id":"s1","blocks":[...],"selected_tools":["get_stock_quote"]}]}}',
        '{"status":"question","question":"<one short question>","options":["<choice>","<choice>"]}',
        '{"status":"declined","reason":"<why this cannot run here, one line>","closest":"<the nearest buildable version>"}',
        '',
        'Ask at most ONE question per reply and at most two across the conversation. If the idea is',
        'already specific enough, return status "ok" immediately. If the idea needs something the',
        'engine cannot do (shorts, options, leverage, intraday triggers, live web search), return',
        '"declined" and describe the closest buildable version in "closest".',
        '',
        capabilityManifest(),
    ].join('\n');
}

function stripFences(raw: string): string {
    const trimmed = raw.trim();
    const fence = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
    return (fence ? fence[1] : trimmed).trim();
}

function asBlock(value: unknown): StrategyBlock | null {
    if (!value || typeof value !== 'object') return null;
    const block = value as Record<string, unknown>;
    if (!BLOCK_TYPES.has(String(block.type))) return null;
    if (typeof block.id !== 'string' || !block.id) return null;
    if (block.type === 'prompt' && typeof block.text !== 'string') return null;
    if (block.type === 'news') {
        if (!Array.isArray(block.contains) || !Number.isFinite(Number(block.recency_hours))) {
            return null;
        }
    }
    if (block.type === 'technicals' && !Array.isArray(block.rules)) return null;
    return block as unknown as StrategyBlock;
}

function assertEnvelope(raw: Record<string, unknown>): void {
    if (raw.version !== '2.0-push') throw new Error('strategy version must be 2.0-push');
    if (typeof raw.name !== 'string' || !raw.name.trim()) throw new Error('strategy needs a name');
    // Only 3h is honoured by the scheduler; 5m/1d would advertise a cadence the
    // runner ignores, so a compiled graph is pinned to it explicitly.
    if (String(raw.cadence) !== '3h') throw new Error('cadence must be 3h');
    if (!Array.isArray(raw.stages) || raw.stages.length !== 1) {
        throw new Error('strategy must have exactly one stage');
    }
}

function assertBlockContract(blocks: StrategyBlock[]): void {
    const ids = blocks.map((block) => block.id);
    if (new Set(ids).size !== ids.length) throw new Error('block ids must be unique');
    if (!blocks.some((block) => block.type === 'output_format')) {
        throw new Error('output_format block is required');
    }
    if (blocks[blocks.length - 1]?.type !== 'output_format') {
        throw new Error('output_format must be the last block');
    }
    for (const block of blocks) {
        if (block.type === 'prompt' && block.text.length > 4000) {
            throw new Error('prompt block is too long');
        }
    }
}

function assertTools(value: unknown): string[] {
    const tools = Array.isArray(value) ? value : [];
    const allowed = new Set(CURATED_TOOLS.map((tool) => tool.name));
    for (const tool of tools) {
        if (typeof tool !== 'string' || !allowed.has(tool) || tool === 'web_search') {
            throw new Error(`tool not available in recipes: ${String(tool)}`);
        }
    }
    return tools as string[];
}

/** Structural + contract validation shared by the server fn and its tests. */
export function validateStrategy(candidate: unknown): PushStrategy {
    if (!candidate || typeof candidate !== 'object') throw new Error('strategy is not an object');
    const raw = candidate as Record<string, unknown>;
    assertEnvelope(raw);

    const stage = (raw.stages as Array<Record<string, unknown>>)[0];
    if (typeof stage?.id !== 'string' || !stage.id) throw new Error('stage needs an id');
    if (!Array.isArray(stage.blocks)) throw new Error('stage needs blocks');

    const maybeBlocks = stage.blocks.map(asBlock);
    if (maybeBlocks.some((block) => block === null)) throw new Error('unknown or malformed block');
    const blocks = maybeBlocks as StrategyBlock[];
    assertBlockContract(blocks);

    const strategy = {
        version: '2.0-push',
        name: String(raw.name).trim().slice(0, 40),
        description: typeof raw.description === 'string' ? raw.description.slice(0, 200) : '',
        cadence: '3h',
        stages: [
            { id: String(stage.id), blocks, selected_tools: assertTools(stage.selected_tools) },
        ],
    } as PushStrategy;

    assertSingleLlmStage(strategy);
    assertNoPrevOutputPlaceholder(strategy);
    assertKnownRuleMetrics(strategy);
    return strategy;
}

/**
 * True only for a value that is really one of the three reply shapes. The server
 * function transport hands back `undefined` for an envelope-less response, and a
 * hand-edited reply can be `{status:'ok'}` with a half-built strategy, so a reply
 * is trusted only when `validateStrategy` accepts it.
 */
export function isCompilerReply(value: unknown): value is CompilerReply {
    if (!value || typeof value !== 'object') return false;
    const candidate = value as Record<string, unknown>;
    const status = String(candidate.status ?? '');
    if (status === 'ok') {
        try {
            validateStrategy(candidate.strategy);
            return true;
        } catch {
            return false;
        }
    }
    if (status === 'question') {
        return (
            typeof candidate.question === 'string' &&
            candidate.question.trim().length > 0 &&
            Array.isArray(candidate.options)
        );
    }
    return status === 'declined';
}

/** Parse one model reply into a decision we can act on or show. */
export function parseCompilerReply(raw: string): CompilerReply {
    const parsed = JSON.parse(stripFences(raw)) as Record<string, unknown>;
    const status = String(parsed.status || '');

    if (status === 'ok') {
        const strategy = validateStrategy(parsed.strategy);
        return {
            status: 'ok',
            strategy,
            summary: String(parsed.summary || strategy.description || '').slice(0, 240),
        };
    }
    if (status === 'question') {
        const question = String(parsed.question || '').trim();
        if (!question) throw new Error('question reply without text');
        const options = Array.isArray(parsed.options)
            ? parsed.options.map((option) => String(option)).slice(0, MAX_OPTIONS)
            : [];
        return { status: 'question', question, options };
    }
    if (status === 'declined') {
        return {
            status: 'declined',
            reason: String(parsed.reason || 'This idea cannot run in the recipe engine yet.'),
            closest: typeof parsed.closest === 'string' ? parsed.closest : undefined,
        };
    }
    throw new Error(`unknown compiler status: ${status || '<empty>'}`);
}

/**
 * Degrade instead of failing: an unbuildable or twice-invalid idea still lands the
 * visitor in a working recipe rather than a dead end.
 */
export function fallbackReply(reason: string): CompilerReply {
    const template = STARTER_RECIPES[0];
    return {
        status: 'ok',
        strategy: validateStrategy(structuredClone(template)),
        summary: reason,
        fallback: true,
    };
}

const MAX_TURN_CHARS = 2000;

/**
 * Client-supplied roles are sanitised: only user/assistant turns reach the model,
 * so a crafted request cannot append its own system prompt after ours.
 */
export function buildConversation(messages: BuilderMessage[]): Array<{
    role: 'system' | 'user' | 'assistant';
    content: string;
}> {
    const turns = messages
        .filter((message) => message.role === 'user' || message.role === 'assistant')
        .map((message) => ({
            role: message.role,
            content: String(message.content ?? '').slice(0, MAX_TURN_CHARS),
        }));
    return [{ role: 'system', content: compilerSystemPrompt() }, ...turns];
}
