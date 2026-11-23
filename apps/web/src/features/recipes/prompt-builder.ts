import { buildNewsExcerpt } from './news-excerpt';
import type {
    MemoriesBlock,
    NewsBlock,
    StrategyBlock,
    StrategyStage,
    TechnicalsBlock,
} from './types';
import { pinStageBlocks } from './utils/stage-blocks';

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
        'This strategy is Long-Only. Output BUY (enter long) or EXIT (close open position) as a JSON array of objects, or [] to HOLD:',
        '[{"action": "BUY", "ticker": "NVDA"}]',
        'Each object must have exactly "action" ("BUY" or "EXIT") and "ticker" (uppercase ticker symbol).',
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
    const sections = pinStageBlocks(stage.blocks)
        .map((block) => formatBlockPreview(block, hydratedByBlockId))
        .filter((text) => text.length > 0);

    return sections.join('\n\n') || '(Empty stage — add a block above)';
}

function matchesKeywords(haystack: string, keywords: string[]): boolean {
    const cleaned = keywords.map((k) => k.trim().toLowerCase()).filter(Boolean);
    if (cleaned.length === 0) return true;
    const lower = haystack.toLowerCase();
    return cleaned.some((kw) => lower.includes(kw));
}

export function hydrateNewsBlockText(
    block: { contains: string[]; recency_hours: number },
    newsRows: Array<{ title?: string; full_text?: string; date_published?: string }>,
    now: number,
): string {
    const floorMs = now - Math.max(1, block.recency_hours) * 3600 * 1000;
    const matched = newsRows
        .filter((r) => {
            const ts = Date.parse(String(r.date_published || ''));
            return (
                !Number.isNaN(ts) &&
                ts >= floorMs &&
                ts <= now &&
                matchesKeywords(`${r.title || ''} ${r.full_text || ''}`, block.contains)
            );
        })
        .slice(0, 15);
    const kw = block.contains.length > 0 ? block.contains.join(', ') : 'ALL';
    const header = `[News (contains: ${kw} | recency: ${block.recency_hours}h)]:`;
    if (matched.length === 0) return `${header}\n- (No matching news in window)`;
    return [
        header,
        ...matched.map((n) => {
            const line = `- [${String(n.date_published).slice(0, 16)}] ${n.title}`;
            const excerpt = buildNewsExcerpt(n.full_text, block.contains);
            return excerpt ? `${line}\n  ${excerpt}` : line;
        }),
    ].join('\n');
}

export function hydrateMemoriesBlockText(
    block: { contains: string[]; recency_hours: number; category: string; min_importance: number },
    memoryRows: Array<{
        content?: string;
        created_at?: string;
        memory_type?: string;
        importance_score?: number;
    }>,
    now: number,
): string {
    const floorMs = now - Math.max(1, block.recency_hours) * 3600 * 1000;
    const catNorm = (block.category || 'ALL').toUpperCase();
    const matched = memoryRows
        .filter((m) => {
            const ts = Date.parse(String(m.created_at || ''));
            if (Number.isNaN(ts) || ts < floorMs || ts > now) return false;
            if (Number(m.importance_score ?? 5) < block.min_importance) return false;
            const mt = String(m.memory_type || 'MARKET_EVENT').toUpperCase();
            return (
                (catNorm === 'ALL' || mt === catNorm) &&
                matchesKeywords(String(m.content || ''), block.contains)
            );
        })
        .slice(0, 15);
    const kw = block.contains.length > 0 ? block.contains.join(', ') : 'ALL';
    const header = `[Memories (contains: ${kw} | recency: ${block.recency_hours}h | category: ${block.category} | min_importance: ${block.min_importance})]:`;
    if (matched.length === 0) return `${header}\n- (No matching memories in window)`;
    return [
        header,
        ...matched.map(
            (m) => `- [${m.memory_type || 'EVENT'} | imp=${m.importance_score ?? 5}] ${m.content}`,
        ),
    ].join('\n');
}
