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

function formatBlockPreview(
    block: StrategyBlock,
    hydratedByBlockId: Record<string, string>,
    stageIndex: number,
): { text: string; usedPrev: boolean } {
    if (block.type === 'prompt') {
        const trimmed = block.text.trim();
        const usedPrev = trimmed.includes('{{prev_output}}');
        const text = usedPrev
            ? trimmed.replaceAll(
                  '{{prev_output}}',
                  `<Output from Stage ${stageIndex} will be injected here>`,
              )
            : trimmed;
        return { text, usedPrev };
    }
    if (block.type === 'news') {
        return { text: formatNewsPreview(block, hydratedByBlockId[block.id]), usedPrev: false };
    }
    if (block.type === 'memories') {
        return { text: formatMemoriesPreview(block, hydratedByBlockId[block.id]), usedPrev: false };
    }
    return { text: formatTechnicalsPreview(block), usedPrev: false };
}

export function buildStagePromptPreview(
    stage: StrategyStage,
    hydratedByBlockId: Record<string, string> = {},
    stageIndex = 0,
): string {
    const sections: string[] = [];
    let usedPrev = false;

    for (const block of stage.blocks) {
        const res = formatBlockPreview(block, hydratedByBlockId, stageIndex);
        if (res.usedPrev) usedPrev = true;
        if (res.text) sections.push(res.text);
    }

    if (stageIndex > 0 && !usedPrev) {
        sections.push(
            `[Previous Stage Output]:\n<Output from Stage ${stageIndex} will be appended here>`,
        );
    }

    return sections.join('\n\n') || '(Empty stage — add a block above)';
}
