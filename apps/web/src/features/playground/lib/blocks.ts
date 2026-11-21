import type { PushStrategy, StrategyBlock, StrategyStage } from '~/features/recipes/types';

/** Visitor-facing labels. The domain names stay as the subtitle (N2). */
export const BLOCK_COPY = {
    prompt: { title: 'Think', subtitle: 'Plain-English instructions for the model' },
    news: { title: 'Read news', subtitle: 'Only headlines containing these words' },
    technicals: { title: 'Filter', subtitle: 'Numbers the bot checks before it acts' },
    memories: { title: 'Remember', subtitle: 'Earlier lessons worth recalling' },
    output_format: { title: 'Answer', subtitle: 'Locked trade format' },
} as const satisfies Record<StrategyBlock['type'], { title: string; subtitle: string }>;

export const CONTENT_TYPES = ['prompt', 'news', 'technicals', 'memories'] as const;
export type ContentBlockType = (typeof CONTENT_TYPES)[number];

let sequence = 0;

/** Deterministic ids: two renders of the same edits must produce the same graph. */
function nextId(prefix: string): string {
    sequence += 1;
    return `${prefix}-${sequence}`;
}

export function createBlock(type: StrategyBlock['type']): StrategyBlock {
    const id = nextId(type);
    if (type === 'prompt') return { id, type: 'prompt', text: '' };
    if (type === 'news') return { id, type: 'news', contains: [], recency_hours: 48 };
    if (type === 'memories') {
        return {
            id,
            type: 'memories',
            contains: [],
            recency_hours: 168,
            category: 'ALL',
            min_importance: 3,
        };
    }
    if (type === 'output_format') return { id, type: 'output_format' };
    return {
        id,
        type: 'technicals',
        rules: [{ id: nextId('rule'), metric: 'RSI', operator: '<', target: '70' }],
    };
}

/**
 * Tools the hero supplies itself. `selected_tools` used to be written only by
 * ToolPicker, so a builder without one launched an empty tool list and a
 * technicals filter could never be evaluated.
 */
export function deriveTools(blocks: StrategyBlock[]): string[] {
    const tools = new Set<string>(['get_stock_quote']);
    if (blocks.some((block) => block.type === 'technicals')) {
        tools.add('get_technical_indicators');
        tools.add('get_key_metrics');
    }
    if (blocks.some((block) => block.type === 'news')) tools.add('get_todays_news_menu');
    if (blocks.some((block) => block.type === 'prompt')) tools.add('get_price_history');
    // run_stock_screener is liveOnly; never derive it for a backtest-shaped draft.
    return [...tools];
}

export function createStage(): StrategyStage {
    const blocks = [createBlock('prompt'), createBlock('news'), createBlock('technicals')];
    return {
        id: nextId('stage'),
        blocks: normalizeBlocks([...blocks, createBlock('output_format')]),
        selected_tools: deriveTools(blocks),
    };
}

export function normalizeBlocks(blocks: StrategyBlock[]): StrategyBlock[] {
    const terminal = blocks.filter((block) => block.type === 'output_format');
    const content = blocks.filter((block) => block.type !== 'output_format');
    return [...content, ...terminal];
}

/**
 * Returns the same array when the move is a no-op, so React can skip a render.
 * The terminal block is presentation-only (the hydrator sorts it last anyway),
 * so moving across it would make the editor lie about the graph.
 */
export function moveBlock(blocks: StrategyBlock[], index: number, delta: -1 | 1): StrategyBlock[] {
    const target = index + delta;
    if (target < 0 || target >= blocks.length) return blocks;
    if (blocks[index]?.type === 'output_format' || blocks[target]?.type === 'output_format') {
        return blocks;
    }
    const next = [...blocks];
    const [moved] = next.splice(index, 1);
    next.splice(target, 0, moved);
    return next;
}

/** Turns the draft into the exact shape the engine validates. */
export function toStrategy(stage: StrategyStage, name: string, description: string): PushStrategy {
    return {
        version: '2.0-push',
        name: name.trim().slice(0, 40) || 'My first bot',
        description: description.trim().slice(0, 200),
        cadence: '3h',
        stages: [
            {
                id: stage.id,
                blocks: normalizeBlocks(stage.blocks),
                selected_tools: stage.selected_tools.length
                    ? stage.selected_tools
                    : deriveTools(stage.blocks),
            },
        ],
    };
}
