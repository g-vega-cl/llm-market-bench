import type {
    MemoriesBlock,
    NewsBlock,
    StrategyBlock,
    StrategyStage,
    TechnicalsBlock,
} from './types';

function formatNewsPreview(block: NewsBlock, hydrated?: string): string {
    if (hydrated) return hydrated;
    const kw = block.contains.length > 0 ? block.contains.join(', ') : 'ALL';
    return `[News (contains: ${kw} | recency: ${block.recency_hours}h)]:\n- <Matching news headlines injected at run time>`;
}

function formatMemoriesPreview(block: MemoriesBlock, hydrated?: string): string {
    if (hydrated) return hydrated;
    const kw = block.contains.length > 0 ? block.contains.join(', ') : 'ALL';
    return `[Memories (contains: ${kw} | recency: ${block.recency_hours}h | category: ${block.category} | min_importance: ${block.min_importance})]:\n- <Matching memories injected at run time>`;
}

function formatTechnicalsPreview(block: TechnicalsBlock): string {
    if (block.rules.length === 0) {
        return '[Technicals Filter]: No technical filters configured.';
    }
    return [
        '[Technicals & Fundamentals Criteria (apply when selecting or filtering tickers)]:',
        ...block.rules.map((r) => `- ${r.metric} ${r.operator} ${r.target}`),
    ].join('\n');
}

function formatOutputFormatPreview(): string {
    return [
        '=== REQUIRED OUTPUT FORMAT ===',
        'Output BUY or SELL decisions strictly as a JSON array of objects:',
        '[{"action": "BUY", "ticker": "NVDA"}]',
        'Each object must have exactly "action" ("BUY" or "SELL") and "ticker" (uppercase ticker symbol).',
        'Do not include any keys beyond "action" and "ticker", and do not add prose outside the JSON array.',
        'This output-format block is immutable; do not edit its contents.',
    ].join('\n');
}

function formatBlockPreview(
    block: StrategyBlock,
    hydratedByBlockId: Record<string, string>,
): string {
    if (block.type === 'prompt') return block.text.trim();
    if (block.type === 'news') return formatNewsPreview(block, hydratedByBlockId[block.id]);
    if (block.type === 'memories') return formatMemoriesPreview(block, hydratedByBlockId[block.id]);
    if (block.type === 'output_format') return formatOutputFormatPreview();
    return formatTechnicalsPreview(block);
}

export function buildStagePromptPreview(
    stage: StrategyStage,
    hydratedByBlockId: Record<string, string> = {},
): string {
    const sections = stage.blocks
        .map((block) => formatBlockPreview(block, hydratedByBlockId))
        .filter((text) => text.length > 0);

    return sections.join('\n\n') || '(Empty stage — add a block above)';
}
