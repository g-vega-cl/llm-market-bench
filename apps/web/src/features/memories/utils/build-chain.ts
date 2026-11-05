import type { Memory } from '@llm-market-bench/database';
import { formatEasternDateTimeWithYear } from '~/utils/date';

export interface ChainMemory {
    id: string;
    content: string;
    created_at: string | null;
    formattedDate?: string;
    elapsedFromRoot?: string;
    elapsedFromPreceding?: string;
    isRoot?: boolean;
    modelsInvolved?: string[];
    directPredecessorId?: string | null;
    directSuccessorIds?: string[];
    status?: string | null;
    parent_id?: string | null;
    relationship_type?: string | null;
    relevance_score?: number | null;
    memory_type?: string | null;
    importance_score?: number | null;
    target_date?: string | null;
    // biome-ignore lint/suspicious/noExplicitAny: metadata is JSONB with arbitrary shapes
    metadata?: Record<string, any> | null;
}

export function formatElapsedDuration(diffMs: number): string {
    if (diffMs <= 0) return '0m later';
    if (diffMs < 60 * 1000) return '<1m later';

    const oneHourMs = 60 * 60 * 1000;
    const oneDayMs = 24 * oneHourMs;

    if (diffMs < oneHourMs) {
        const mins = Math.round(diffMs / 60000);
        return `+${mins}m later`;
    }

    if (diffMs < oneDayMs) {
        const hours = Math.floor(diffMs / oneHourMs);
        const mins = Math.round((diffMs % oneHourMs) / 60000);
        return mins > 0 ? `+${hours}h ${mins}m later` : `+${hours}h later`;
    }

    const days = Math.floor(diffMs / oneDayMs);
    const hours = Math.round((diffMs % oneDayMs) / oneHourMs);
    return hours > 0 ? `+${days}d ${hours}h later` : `+${days}d later`;
}

function addStringIfPresent(target: Set<string>, val: unknown): void {
    if (typeof val === 'string' && val.trim()) {
        target.add(val.trim());
    }
}

function addArrayStrings(target: Set<string>, list: unknown): void {
    if (Array.isArray(list)) {
        for (const item of list) {
            addStringIfPresent(target, item);
        }
    }
}

// biome-ignore lint/suspicious/noExplicitAny: metadata is JSONB with arbitrary shapes
export function extractModelsInvolved(metadata?: Record<string, any> | null): string[] {
    if (!metadata) return [];
    const models = new Set<string>();

    addArrayStrings(models, metadata.models_involved);
    addArrayStrings(models, metadata.participating_agents);
    addStringIfPresent(models, metadata.model_name);

    if (typeof metadata.debate === 'object' && metadata.debate !== null) {
        addStringIfPresent(models, metadata.debate.adversary_model);
        addStringIfPresent(models, metadata.debate.arbiter_model);
    }

    return Array.from(models);
}

export function buildChain(
    memoryId: string,
    allMemories: Memory[],
): { chain: ChainMemory[]; targetMemory: ChainMemory | null } {
    const memoryMap = new Map(allMemories.map((m) => [m.id, m]));
    const targetMemory = memoryMap.get(memoryId) || null;

    if (!targetMemory) {
        return { chain: [], targetMemory: null };
    }

    // 1. Traverse backwards to find the root of the tree
    let root = targetMemory;
    while (root.parent_id) {
        const parent = memoryMap.get(root.parent_id);
        if (!parent) break;
        root = parent;
    }

    // 2. From the root, collect all descendants recursively
    const treeMemoryIds = new Set<string>();
    const collectDescendants = (nodeId: string) => {
        if (treeMemoryIds.has(nodeId)) return;
        treeMemoryIds.add(nodeId);

        for (const m of allMemories) {
            if (m.parent_id === nodeId) {
                collectDescendants(m.id);
            }
        }
    };
    collectDescendants(root.id);

    // 3. Sort chronologically
    const sorted = Array.from(treeMemoryIds)
        .map((id) => memoryMap.get(id))
        .filter((m): m is Memory => m !== undefined)
        .sort((a, b) => {
            const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
            const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
            return dateA - dateB;
        });

    const rootTimeMs = sorted[0]?.created_at ? new Date(sorted[0].created_at).getTime() : 0;

    // 4. Build annotated chain with elapsed times and model process attributions
    const chain: ChainMemory[] = sorted.map((m, idx) => {
        const currentTimeMs = m.created_at ? new Date(m.created_at).getTime() : 0;
        const prevDateStr = idx > 0 ? sorted[idx - 1]?.created_at : null;
        const prevTimeMs = prevDateStr ? new Date(prevDateStr).getTime() : 0;
        const isRootNode = idx === 0 || !m.parent_id;

        const successors = sorted
            .filter((other) => other.parent_id === m.id)
            .map((other) => other.id);

        return {
            ...m,
            formattedDate: formatEasternDateTimeWithYear(m.created_at),
            isRoot: isRootNode,
            elapsedFromRoot: isRootNode
                ? 'Origin Catalyst'
                : formatElapsedDuration(currentTimeMs - rootTimeMs),
            elapsedFromPreceding:
                idx === 0 ? 'Origin' : formatElapsedDuration(currentTimeMs - prevTimeMs),
            modelsInvolved: extractModelsInvolved(m.metadata),
            directPredecessorId: m.parent_id ?? null,
            directSuccessorIds: successors,
        };
    });

    const targetInChain = chain.find((m) => m.id === memoryId) || null;
    const targetMemoryWithDate: ChainMemory | null = targetInChain
        ? targetInChain
        : {
              ...targetMemory,
              formattedDate: formatEasternDateTimeWithYear(targetMemory.created_at),
              isRoot: !targetMemory.parent_id,
              elapsedFromRoot: 'Origin Catalyst',
              elapsedFromPreceding: 'Origin',
              modelsInvolved: extractModelsInvolved(targetMemory.metadata),
              directPredecessorId: targetMemory.parent_id ?? null,
              directSuccessorIds: [],
          };

    return { chain, targetMemory: targetMemoryWithDate };
}
