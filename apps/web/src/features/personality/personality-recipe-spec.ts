import type { PushStrategy } from '../recipes/types';

function formatRuleLabel(metric: string, operator: string, target: string): string {
    if (metric === 'price_52w_pct') return `52w ${operator} ${target}%`;
    if (metric === 'Price vs VWAP') return `VWAP ${operator} ${target}`;
    return `${metric} ${operator} ${target}`;
}

/**
 * Derives a compact, drift-free single-line execution summary directly from
 * all canonical blocks in `packages/config/starter-recipes.json`.
 */
export function formatRecipeExecutionSpec(recipe: PushStrategy): string {
    const blocks = recipe.stages[0]?.blocks ?? [];
    const newsBlocks = blocks.filter((block) => block.type === 'news');
    const memoryBlocks = blocks.filter((block) => block.type === 'memories');
    const technicalBlocks = blocks.filter((block) => block.type === 'technicals');

    const segments: string[] = [];
    if (newsBlocks.length > 0) {
        for (const n of newsBlocks) segments.push(`News ${n.recency_hours}h`);
    } else {
        segments.push('News Off');
    }
    for (const mem of memoryBlocks) {
        segments.push(`Memory ${mem.recency_hours}h`);
    }
    const allRules = technicalBlocks.flatMap((t) => t.rules);
    if (allRules.length > 0) {
        const formattedRules = allRules
            .map((r) => formatRuleLabel(r.metric, r.operator, r.target))
            .join(' · ');
        segments.push(`Rules: ${formattedRules}`);
    }
    return segments.join(' · ');
}

function compactRuleToken(metric: string, operator: string, target: string): string {
    if (metric === 'price_52w_pct') return `${operator}${target}% 52w`;
    if (metric === 'Price vs VWAP') return `VWAP${operator}${target}`;
    return `${metric}${operator}${target}`;
}

const CORE_GATE_MAX_CHARS = 14;

function fitNewsCoreGate(prefix: string, compactRules: string[]): string {
    const preferred = compactRules.find((r) => r.startsWith('RVOL')) ?? compactRules[0];
    if (preferred) {
        const candidate = `${prefix} · ${preferred}`;
        if (candidate.length <= CORE_GATE_MAX_CHARS) return candidate;
        const tight = `${prefix}·${preferred.replace(/\s+/g, '')}`;
        if (tight.length <= CORE_GATE_MAX_CHARS) return tight;
    }
    return `${prefix} News`.slice(0, CORE_GATE_MAX_CHARS);
}

/**
 * Derives a compact badge token (structurally bounded to <= 14 chars) directly
 * from starter recipe blocks so badges stay single-line at 360px mobile widths.
 */
export function summarizeRecipeCoreGate(recipe: PushStrategy): string {
    const blocks = recipe.stages[0]?.blocks ?? [];
    const news = blocks.find((block) => block.type === 'news');
    const compactRules = blocks
        .filter((block) => block.type === 'technicals')
        .flatMap((block) =>
            block.rules.map((r) => compactRuleToken(r.metric, r.operator, r.target)),
        );

    if (news) {
        return fitNewsCoreGate(`${news.recency_hours}h`, compactRules);
    }

    if (compactRules.length > 0) {
        let acc = compactRules[0];
        for (let i = 1; i < compactRules.length; i++) {
            const next = `${acc} · ${compactRules[i]}`;
            if (next.length > CORE_GATE_MAX_CHARS) break;
            acc = next;
        }
        return acc.slice(0, CORE_GATE_MAX_CHARS);
    }

    return `${recipe.stages[0]?.selected_tools.length ?? 0} tool checks`.slice(
        0,
        CORE_GATE_MAX_CHARS,
    );
}
