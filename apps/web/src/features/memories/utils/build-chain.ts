import type { Memory } from '@llm-market-bench/database';
import { formatEasternDateTimeWithYear } from '~/utils/date';

export interface ChainMemory extends Memory {
    formattedDate?: string;
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

    // 3. Sort chronologically and pre-format dates
    const chain: ChainMemory[] = Array.from(treeMemoryIds)
        .map((id) => memoryMap.get(id))
        .filter((m): m is Memory => m !== undefined)
        .sort((a, b) => {
            const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
            const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
            return dateA - dateB;
        })
        .map((m) => ({
            ...m,
            formattedDate: formatEasternDateTimeWithYear(m.created_at),
        }));

    const targetMemoryWithDate: ChainMemory | null = targetMemory
        ? {
              ...targetMemory,
              formattedDate: formatEasternDateTimeWithYear(targetMemory.created_at),
          }
        : null;

    return { chain, targetMemory: targetMemoryWithDate };
}
